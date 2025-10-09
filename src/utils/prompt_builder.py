from pathlib import Path
from typing import Dict, Any
import json
import re


CONDITION_PLACEHOLDER = "{{CONDITION}}"
JSON_PLACEHOLDER = "{{RECORD_JSON}}"
OUTPUT_SCHEMA_PLACEHOLDER = "{{OUTPUT_SCHEMA}}"


def load_config(path: Path) -> dict:
    with path.open('r', encoding='utf-8') as f:
        return json.load(f)


def load_condition(path: Path) -> str:
    return path.read_text(encoding="utf-8").strip()


def load_template(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _ensure_json_fence(pre_template: str, json_snippet: str) -> str:
    """Insert json fenced code block, upgrading a generic fence if present.

    Strategy:
      - Build the replacement block: ```json + JSON + closing fence.
      - Replace the placeholder token (which is already inside fences in the
        template) OR if the template only had the placeholder, insert fences.
    """
    fenced_json = f"```json\n{json_snippet}\n```"

    # Case 1: Placeholder inside existing triple backticks block:
    # Replace any code fence block containing only the placeholder.
    pattern = re.compile(
        r"```[^`]*?" + re.escape(JSON_PLACEHOLDER) + r"[^`]*?```", re.DOTALL)
    if pattern.search(pre_template):
        return pattern.sub(fenced_json, pre_template, count=1)

    # Case 2: Placeholder bare; just replace token with fenced block.
    return pre_template.replace(JSON_PLACEHOLDER, fenced_json)


def render_prompt(template: str, condition: str, record: Dict[str, Any], output_schema: Dict[str, Any] = None) -> str:
    # Convert record to a pretty JSON string (ensure_ascii False preserves accents)
    record_json = json.dumps(record, ensure_ascii=False, indent=2)

    out = template.replace(CONDITION_PLACEHOLDER, condition)

    # Replace output schema placeholder if present
    if output_schema:
        schema_json = json.dumps(output_schema, ensure_ascii=False, indent=2)
        out = out.replace(OUTPUT_SCHEMA_PLACEHOLDER,
                          f"```json\n{schema_json}\n```")

    # Replace JSON placeholder, ensuring fenced block has language spec
    out = out.replace(JSON_PLACEHOLDER, record_json)
    # Upgrade fence to json if not already
    out = _ensure_json_fence(out, record_json)
    return out


def safe_filename(nuc_val: Any, index: int) -> str:
    base = str(nuc_val).strip() if nuc_val not in (
        None, "", "nan") else f"row_{index + 1}"
    # Keep only safe chars
    safe = "".join(ch for ch in base if ch.isalnum() or ch in ("-", "_"))
    if not safe:
        safe = f"row_{index + 1}"
    return f"prompt_{safe}.md"


def write_prompts(
    records: list[dict[str, Any]],
    config_path: Path,
    output_dir: Path,
    nuc_column: str | None = None,
) -> list[Path]:
    config = load_config(config_path)
    template = config['prompt_template']
    condition = config['condition']
    output_schema = config.get('output_schema')
    output_dir.mkdir(parents=True, exist_ok=True)

    written: list[Path] = []
    for idx, rec in enumerate(records):
        nuc_val = rec.get(nuc_column) if nuc_column else None
        content = render_prompt(template, condition, rec, output_schema)
        file_path = output_dir / safe_filename(nuc_val, idx)
        file_path.write_text(content, encoding="utf-8")
        written.append(file_path)
    return written
