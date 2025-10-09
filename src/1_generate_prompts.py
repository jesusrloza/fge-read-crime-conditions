#!/usr/bin/env python3
"""
Script to generate prompts from crime narrations data.

This script reads Excel data, deduplicates records, and generates prompt files
for later processing with Ollama.
"""

import sys
import json
from pathlib import Path
from typing import Tuple, List, Dict, Any

import pandas as pd

# Handle imports based on how the script is run
try:
    # Try relative import (when run as module)
    from .utils.prompt_builder import write_prompts
except ImportError:
    # Fall back to absolute import (when run directly)
    from utils.prompt_builder import write_prompts


def _normalize_key(s: str) -> str:
    return "".join(ch for ch in str(s).lower() if ch.isalnum())


def read_excel_all(excel_path: Path) -> Tuple[List[Dict[str, Any]], Dict[str, str]]:
    """
    Read the whole Excel file and return:
      - a list of records (each record is a dict mapping original column name -> cleaned value)
      - a mapping normalized_column_key -> original column name (for lookups)
    Values:
      - strings are stripped
      - pandas Timestamps are converted to ISO strings
      - NA values become None
    """
    if not excel_path.exists():
        raise FileNotFoundError(f"File not found: {excel_path}")

    df = pd.read_excel(excel_path)

    # mapping from normalized key -> original column name
    cols_map = {_normalize_key(c): c for c in df.columns}

    # Convert pandas NA -> None
    df = df.where(pd.notna(df), None)

    records: List[Dict[str, Any]] = []
    for _, row in df.iterrows():
        rec: Dict[str, Any] = {}
        for col in df.columns:
            val = row[col]
            if val is None:
                rec[col] = None
            elif isinstance(val, pd.Timestamp):
                rec[col] = val.isoformat()
            elif isinstance(val, str):
                rec[col] = val.strip()
            else:
                # keep numeric / bool / python-native types as-is
                rec[col] = val
        records.append(rec)

    return records, cols_map


def dedupe_records_by_nuc(
    records: List[Dict[str, Any]], cols_map: Dict[str, str], nuc_key: str = "nuc"
) -> List[Dict[str, Any]]:
    """
    Merge records having the same NUC into a single record.

    Rules:
      - The NUC column name is resolved from `cols_map` using a normalized key.
      - For each column, None values are ignored when aggregating.
      - If multiple distinct non-None values exist for a column, the
        aggregated value becomes a list (order preserved, duplicates removed).
      - If only a single non-None value exists, the scalar value is kept.
    """
    norm = _normalize_key(nuc_key)
    nuc_col_name = cols_map.get(norm)
    if not nuc_col_name:
        raise KeyError(f"NUC column not found (normalized key: {norm})")

    grouped: Dict[Any, Dict[str, Any]] = {}

    for rec in records:
        nuc_val = rec.get(nuc_col_name)
        # Use the raw nuc_val as a grouping key (could be None)
        key = nuc_val

        if key not in grouped:
            # start with a shallow copy so we don't mutate the original
            grouped[key] = {k: v for k, v in rec.items()}
            # ensure future aggregation can produce lists
            continue

        agg = grouped[key]
        for col, new_val in rec.items():
            old_val = agg.get(col)

            # treat pandas/NumPy NA as missing
            def _is_missing(v: Any) -> bool:
                # None is missing
                if v is None:
                    return True

                # lists/tuples: missing when all elements are missing
                if isinstance(v, (list, tuple)):
                    return all(_is_missing(x) for x in v)

                try:
                    res = pd.isna(v)
                except Exception:
                    return False

                # pd.isna can return array-like for sequences; consider missing
                # only if all elements are NA
                if hasattr(res, "all"):
                    try:
                        return bool(res.all())
                    except Exception:
                        return False

                return bool(res)

            if _is_missing(new_val):
                # nothing to add from a missing new value
                continue

            if _is_missing(old_val):
                # replace missing old value with the new non-missing value
                agg[col] = new_val
                continue

            # If values are equal, keep the scalar
            if old_val == new_val:
                continue

            # If old_val is already a list, append new_val if not present
            if isinstance(old_val, list):
                if new_val not in old_val:
                    old_val.append(new_val)
                    agg[col] = old_val
                continue

            # old_val is a scalar and different from new_val -> make a list
            agg[col] = [old_val, new_val] if new_val != old_val else old_val

    # Return list of aggregated records
    return list(grouped.values())


def sanitize_records_for_json(records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Recursively sanitize records to make them JSON-friendly.

    - Convert pandas/NumPy NA (pd.isna) to None
    - Convert numpy/pandas scalars to native Python using .item() when available
    - Recursively sanitize lists/dicts
    """
    def _sanitize_value(v: Any) -> Any:
        # treat pandas/np NA as None
        try:
            if pd.isna(v):
                return None
        except Exception:
            pass

        # dict -> sanitize each value
        if isinstance(v, dict):
            return {k: _sanitize_value(val) for k, val in v.items()}

        # list/tuple -> sanitize elements (preserve list type)
        if isinstance(v, (list, tuple)):
            return [_sanitize_value(x) for x in v]

        # numpy / pandas scalar -> native python
        if hasattr(v, "item") and not isinstance(v, (str, bytes)):
            try:
                return v.item()
            except Exception:
                pass

        return v

    return [{k: _sanitize_value(v) for k, v in rec.items()} for rec in records]


def main():
    """Generate prompts from crime narration data."""
    # Fixed paths
    config_path = Path("./prompt/prompt_config.json")
    excel_path = Path("./prompt/data/sample.xlsx")
    prompts_dir = Path("./output/prompts")
    # unique_path = Path("./output/unique.json")

    try:
        records, cols_map = read_excel_all(excel_path)
        print(f"Read {len(records)} records from {excel_path}",
              file=sys.stderr)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(2)

    nuc_col = cols_map.get(_normalize_key("nuc"))

    # Deduplicate records by NUC
    try:
        deduped = dedupe_records_by_nuc(records, cols_map)
        print(
            f"Deduplicated: {len(records)} -> {len(deduped)} records", file=sys.stderr)
        records = deduped
    except KeyError as e:
        print(f"Warning: {e}; skipping deduplication", file=sys.stderr)

    # # Write unique JSON
    # unique_path.parent.mkdir(parents=True, exist_ok=True)
    # try:
    #     safe = sanitize_records_for_json(records)
    #     with unique_path.open("w", encoding="utf-8") as f:
    #         json.dump(safe, f, ensure_ascii=False, indent=2)
    #     print(f"Wrote deduplicated records to {unique_path}", file=sys.stderr)
    # except Exception as e:
    #     print(f"Error writing {unique_path}: {e}", file=sys.stderr)
    #     sys.exit(1)

    # Generate prompts
    try:
        safe_records = sanitize_records_for_json(records)
        written = write_prompts(
            safe_records,
            config_path=config_path,
            output_dir=prompts_dir,
            nuc_column=nuc_col,
        )
        print(
            f"Generated {len(written)} prompt files in {prompts_dir}", file=sys.stderr)
        print("Prompt generation completed successfully!", file=sys.stderr)
    except Exception as e:
        print(f"Error generating prompts: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
