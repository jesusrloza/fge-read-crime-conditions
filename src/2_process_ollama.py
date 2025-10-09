#!/usr/bin/env python3
"""
Script to process existing prompts with Ollama.

This script expects prompt files to already exist in the output/prompts directory
and processes them with Ollama, saving responses to output/responses.
"""

import sys
import json
import re
from pathlib import Path
from typing import Dict, Any, Tuple, Optional

# Handle imports based on how the script is run
try:
    # Try relative import (when run as module)
    from .utils.ollama_client import process_prompts_with_ollama, save_summary_report
except ImportError:
    # Fall back to absolute import (when run directly)
    from utils.ollama_client import process_prompts_with_ollama, save_summary_report


def extract_original_values_from_prompt(prompt_content: str) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """
    Extract the original NUC, condition, and Hechos values from a prompt file.

    Args:
        prompt_content: The content of the prompt file

    Returns:
        Tuple of (nuc, condition, hechos) extracted from the JSON data in the prompt
    """
    try:
        # Find the JSON block in the prompt (between ```json and ```)
        json_match = re.search(r'```json\s*\n(.*?)\n```',
                               prompt_content, re.DOTALL)
        if not json_match:
            return None, None, None

        # Parse the JSON data
        record_data = json.loads(json_match.group(1))

        # Extract NUC (case identifier) - try common field names
        nuc = None
        for field in ['nuc', 'NUC', 'case_id', 'id', 'folio', 'numero_unico_caso']:
            if field in record_data and record_data[field] is not None:
                nuc = str(record_data[field])
                break

        # Extract condition from the prompt text
        condition_match = re.search(
            r'Condición:\s*(.+?)(?=\n\n|\nDatos|\nResponde)', prompt_content, re.DOTALL)
        condition = condition_match.group(
            1).strip() if condition_match else None

        # Extract Hechos from the JSON data
        hechos = None
        for field in ['hechos', 'Hechos', 'HECHOS', 'narrativa', 'narracion', 'crime_narration']:
            if field in record_data and record_data[field] is not None:
                hechos = str(record_data[field])
                break

        return nuc, condition, hechos

    except (json.JSONDecodeError, AttributeError):
        return None, None, None


def preserve_original_values(results: list, prompts_dir: Path, responses_dir: Path) -> list:
    """
    Preserve original NUC and condition values in the results by extracting them
    from the original prompt files and merging them into the LLM responses.
    Also re-saves the individual response files with the updated data.

    Args:
        results: List of result dictionaries from Ollama processing
        prompts_dir: Directory containing the original prompt files
        responses_dir: Directory containing the response files

    Returns:
        Updated results with preserved original values
    """
    updated_results = []

    for result in results:
        if not result.get('success', False):
            # For failed results, just pass through
            updated_results.append(result)
            continue

        prompt_file = result.get('prompt_file')
        if not prompt_file:
            updated_results.append(result)
            continue

        # Read the original prompt file
        prompt_path = prompts_dir / prompt_file
        try:
            prompt_content = prompt_path.read_text(encoding='utf-8')
            original_nuc, original_condition, original_hechos = extract_original_values_from_prompt(
                prompt_content)

            # Debug output
            if original_nuc:
                print(f"  📋 Extracted NUC: {original_nuc}")
            if original_condition:
                print(f"  📋 Extracted condition: {original_condition[:50]}...")
            if original_hechos:
                print(f"  📋 Extracted hechos: {original_hechos[:50]}...")

            # Get the LLM response
            llm_response = result.get('response', {})

            # Always add original values to ensure they're present
            if original_nuc:
                llm_response['nuc'] = original_nuc
                print(f"  ✓ Added NUC: {original_nuc}")

            if original_condition:
                llm_response['condition'] = original_condition
                print(f"  ✓ Added condition")

            if original_hechos:
                llm_response['hechos'] = original_hechos
                print(f"  ✓ Added hechos")

            # Re-save the updated result to the response file
            response_filename = prompt_file.replace('.md', '_response.json')
            response_path = responses_dir / response_filename
            with response_path.open('w', encoding='utf-8') as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
            print(f"  ✓ Updated response file: {response_filename}")

        except Exception as e:
            print(
                f"  ⚠️  Warning: Could not preserve original values for {prompt_file}: {e}")

        updated_results.append(result)

    return updated_results


def main():
    """Process existing prompts with Ollama."""
    # Fixed paths
    prompts_dir = Path("./output/prompts")
    responses_dir = Path("./output/responses")
    summary_path = Path("./output/ollama_summary.json")
    config_path = Path("./prompt/prompt_config.json")

    # Load config
    try:
        with config_path.open("r", encoding="utf-8") as f:
            config = json.load(f)
        model = config.get("model", "gpt-oss:latest")
        use_json_format = config.get("use_json_format", False)
    except Exception as e:
        print(
            f"Warning: Could not load config from {config_path}: {e}", file=sys.stderr)
        model = "gpt-oss:latest"
        use_json_format = False

    # Check if prompts directory exists and has files
    if not prompts_dir.exists():
        print(
            f"Error: Prompts directory not found: {prompts_dir}", file=sys.stderr)
        print(
            "Please run generate_prompts.py first to create prompt files.", file=sys.stderr)
        sys.exit(1)

    prompt_files = list(prompts_dir.glob("*.md"))
    if not prompt_files:
        print(
            f"Error: No prompt files found in {prompts_dir}", file=sys.stderr)
        print(
            "Please run generate_prompts.py first to create prompt files.", file=sys.stderr)
        sys.exit(1)

    # Filter out prompts that already have responses
    prompts_to_process = []
    skipped_count = 0

    for prompt_file in prompt_files:
        # Construct expected response filename
        response_filename = prompt_file.name.replace('.md', '_response.json')
        response_path = responses_dir / response_filename

        if response_path.exists():
            print(
                f"Skipping {prompt_file.name} (response already exists)", file=sys.stderr)
            skipped_count += 1
        else:
            prompts_to_process.append(prompt_file)

    if not prompts_to_process:
        print(
            f"All {len(prompt_files)} prompt files already have responses. Nothing to process.", file=sys.stderr)
        sys.exit(0)

    print(f"Found {len(prompt_files)} total prompt files", file=sys.stderr)
    print(
        f"Skipped {skipped_count} prompts with existing responses", file=sys.stderr)
    print(
        f"Processing {len(prompts_to_process)} remaining prompts", file=sys.stderr)

    try:
        print(
            f"Starting Ollama processing with model: {model}", file=sys.stderr)
        if use_json_format:
            print(
                "Using JSON format enforcement (may cause issues with some models)", file=sys.stderr)
        print("Note: Processing may take several minutes depending on the number of prompts", file=sys.stderr)

        results = process_prompts_with_ollama(
            prompts_dir=prompts_dir,
            responses_dir=responses_dir,
            model=model,
            delay_between_requests=1.0,  # 1 second delay between requests
            use_json_format=use_json_format,
            prompt_files=prompts_to_process
        )

        # Preserve original NUC and condition values (now handled automatically in processing)
        print("Original values preserved during processing...", file=sys.stderr)

        # Save summary report
        save_summary_report(results, summary_path)

        print("Ollama processing completed successfully!", file=sys.stderr)
        print(f"Results saved to {responses_dir}", file=sys.stderr)
        print(f"Summary report saved to {summary_path}", file=sys.stderr)

    except Exception as e:
        print(f"Error processing prompts with Ollama: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
