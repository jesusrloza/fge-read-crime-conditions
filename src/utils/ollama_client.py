"""
Ollama client for sending prompts to language models.
"""
import json
import time
import re
from pathlib import Path
from typing import Dict, Any, Optional, List

# import ollama
from ollama import chat
from ollama import ChatResponse


def get_retry_reason(result: Dict[str, Any]) -> str:
    """
    Get the specific reason why a result should be retried.

    Possible reasons:
    - "success=False": Processing failed
    - "meets_condition=null": meets_condition field is null/None
    - "confidence=X.XX<0.7": confidence is below 0.7 threshold
    - "unknown": Unknown reason

    Args:
        result: Result dictionary from send_prompt_to_ollama

    Returns:
        String describing the retry reason
    """
    # Check success first
    if not result.get('success', False):
        return "success=False"

    # Get response data
    response = result.get('response', {})
    if response is None:
        return "unknown"

    # Check meets_condition
    if response.get('meets_condition') is None:
        return "meets_condition=null"

    # Check confidence
    confidence = response.get('confidence')
    if confidence is not None and isinstance(confidence, (int, float)) and confidence < 0.7:
        return f"confidence={confidence:.2f}<0.7"

    return "unknown"


def should_retry_result(result: Dict[str, Any]) -> bool:
    """
    Determine if a result should be retried based on the specified conditions.

    Retry conditions:
    1. success = false (processing error)
    2. meets_condition = null (null/None value)
    3. confidence < 0.7 (low confidence threshold)

    Args:
        result: Result dictionary from send_prompt_to_ollama

    Returns:
        True if the result should be retried, False otherwise
    """
    # Retry if success is False
    if not result.get('success', False):
        return True

    # Get response data
    response = result.get('response', {})
    if response is None:
        return False

    # Retry if meets_condition is null/None
    if response.get('meets_condition') is None:
        return True

    # Retry if confidence is below 0.7
    confidence = response.get('confidence')
    if confidence is not None and isinstance(confidence, (int, float)) and confidence < 0.7:
        return True

    return False


def clean_json_response(raw_content: str) -> str:
    """
    Clean raw LLM response by removing markdown code blocks and extracting JSON.

    Args:
        raw_content: Raw response content from LLM

    Returns:
        Cleaned JSON string
    """
    # Remove markdown code blocks (```json ... ``` or ``` ... ```)
    # Pattern matches ```json or ``` followed by content until closing ```
    json_block_pattern = re.compile(r'```\w*\n(.*?)\n```', re.DOTALL)
    match = json_block_pattern.search(raw_content.strip())

    if match:
        # Extract content from markdown block
        return match.group(1).strip()
    else:
        # No markdown block found, return as-is
        return raw_content.strip()


def parse_llm_response(raw_content: str) -> Dict[str, Any]:
    """
    Parse LLM response, handling both direct JSON and markdown-wrapped JSON.

    Args:
        raw_content: Raw response content from LLM

    Returns:
        Parsed JSON dictionary

    Raises:
        ValueError: If response cannot be parsed as valid JSON
    """
    # First try to parse as-is
    try:
        return json.loads(raw_content)
    except json.JSONDecodeError:
        pass

    # If that fails, try cleaning markdown and parsing
    cleaned_content = clean_json_response(raw_content)
    try:
        return json.loads(cleaned_content)
    except json.JSONDecodeError as e:
        # Include both original and cleaned content in error for debugging
        raise ValueError(
            f"Invalid JSON response: {e}. "
            f"Original content: '{raw_content}'. "
            f"Cleaned content: '{cleaned_content}'"
        )


def send_prompt_to_ollama(
    prompt: str,
    model: str = "gpt-oss:latest",
    timeout: int = 120,
    use_json_format: bool = False
) -> Dict[str, Any]:
    """
    Send a prompt to Ollama and return the response.

    Args:
        prompt: The prompt text to send
        model: The model name to use
        timeout: Timeout in seconds
        use_json_format: Whether to force JSON format in Ollama options.
                         Note: This may cause issues with some models like gpt-oss:latest.
                         Known working models: llama2:13b, codellama:13b
                         Known problematic models: gpt-oss:latest, some fine-tuned models

    Returns:
        Dictionary containing the response and metadata
    """
    try:
        start_time = time.time()

        # Prepare Ollama options
        options = {'timeout': timeout}

        # Add format option if requested (may cause issues with some models)
        if use_json_format:
            options['format'] = 'json'

        # Send the prompt to Ollama
        response: ChatResponse = chat(
            model=model,
            messages=[
                {
                    'role': 'user',
                    'content': prompt
                }
            ],
            options=options
        )

        end_time = time.time()
        duration = end_time - start_time

        # Parse and validate the response as JSON using enhanced parsing
        raw_content = response['message']['content']
        try:
            parsed_response = parse_llm_response(raw_content)
        except ValueError as e:
            # Re-raise with additional context
            raise ValueError(f"Failed to parse LLM response: {e}")

        return {
            'success': True,
            'model': model,
            'response': parsed_response,  # Return parsed JSON instead of raw string
            'duration_seconds': duration,
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
            'error': None,
            'raw_content': raw_content,  # Keep raw content for debugging
            'used_json_format': use_json_format
        }

    except Exception as e:
        return {
            'success': False,
            'model': model,
            'response': None,
            'duration_seconds': None,
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
            'error': str(e),
            'raw_content': None,
            'used_json_format': use_json_format
        }


def extract_original_values_from_prompt(prompt_content: str) -> tuple[Optional[str], Optional[str], Optional[str]]:
    """
    Extract the original NUC, condition, and Hechos values from a prompt file.

    Args:
        prompt_content: The content of the prompt file

    Returns:
        Tuple of (nuc, condition, hechos) extracted from the JSON data in the prompt
    """
    import re

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


def process_prompts_with_ollama(
    prompts_dir: Path,
    responses_dir: Path,
    model: str = "gpt-oss:latest",
    delay_between_requests: float = 1.0,
    use_json_format: bool = False,
    prompt_files: Optional[List[Path]] = None
) -> List[Dict[str, Any]]:
    """
    Process all prompt files in a directory with Ollama.

    Args:
        prompts_dir: Directory containing prompt .md files
        responses_dir: Directory to save responses
        model: Ollama model to use
        delay_between_requests: Delay in seconds between requests
        use_json_format: Whether to force JSON format in Ollama options
        prompt_files: Optional list of specific prompt files to process.
                     If None, processes all .md files in prompts_dir

    Returns:
        List of results for each processed prompt
    """
    if not prompts_dir.exists():
        raise FileNotFoundError(f"Prompts directory not found: {prompts_dir}")

    # Create responses directory
    responses_dir.mkdir(parents=True, exist_ok=True)

    # Get prompt files - use provided list or scan directory
    if prompt_files is not None:
        # Use the provided list of files
        files_to_process = prompt_files
    else:
        # Get all .md files in prompts directory
        files_to_process = list(prompts_dir.glob("*.md"))

    files_to_process.sort()  # Process in consistent order

    results = []

    print(
        f"Processing {len(files_to_process)} prompt files with model {model}")
    if use_json_format:
        print(f"Using JSON format enforcement (may cause issues with some models)")

    try:
        for i, prompt_file in enumerate(files_to_process, 1):
            print(
                f"Processing prompt {i}/{len(files_to_process)}: {prompt_file.name}")

            # Read the prompt once
            prompt_content = prompt_file.read_text(encoding='utf-8')

            # Initialize retry variables
            max_retries = 3
            attempt = 0
            final_result = None

            while attempt < max_retries:
                attempt += 1
                print(f"  Attempt {attempt}/{max_retries}")

                try:
                    # Send to Ollama
                    result = send_prompt_to_ollama(
                        prompt_content,
                        model,
                        use_json_format=use_json_format
                    )

                    # Check if we need to retry
                    if should_retry_result(result):
                        if attempt < max_retries:
                            retry_reason = get_retry_reason(result)
                            print(
                                f"  ⚠️  Retry needed (reason: {retry_reason}), waiting before retry...")
                            time.sleep(2)  # Brief pause before retry
                            continue
                        else:
                            print(
                                f"  ✗ Max retries ({max_retries}) reached, using final result")
                            final_result = result
                            break
                    else:
                        # Success - no retry needed
                        final_result = result
                        if attempt > 1:
                            print(f"  ✓ Success on attempt {attempt}")
                        break

                except Exception as e:
                    if attempt < max_retries:
                        print(
                            f"  ✗ Attempt {attempt} failed: {e}, retrying...")
                        time.sleep(2)  # Brief pause before retry
                        continue
                    else:
                        print(
                            f"  ✗ Max retries ({max_retries}) reached after exception: {e}")
                        final_result = {
                            'success': False,
                            'prompt_file': prompt_file.name,
                            'prompt_number': i,
                            'error': f"Failed after {max_retries} attempts: {str(e)}",
                            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
                            'retry_attempts': attempt
                        }
                        break

            # Use the final result (either successful or after max retries)
            result = final_result

            # Add file information to result
            result['prompt_file'] = prompt_file.name
            result['prompt_number'] = i
            result['retry_attempts'] = attempt

            # Extract and add original NUC, condition, and hechos values immediately
            if result.get('success', False):
                try:
                    original_nuc, original_condition, original_hechos = extract_original_values_from_prompt(
                        prompt_content)
                    if original_nuc:
                        result['response']['nuc'] = original_nuc
                        print(f"  ✓ Added NUC: {original_nuc}")
                    if original_condition:
                        result['response']['condition'] = original_condition
                        print(f"  ✓ Added condition")
                    if original_hechos:
                        result['response']['hechos'] = original_hechos
                        print(f"  ✓ Added hechos")
                except Exception as e:
                    print(
                        f"  ⚠️  Warning: Could not extract original values: {e}")

            # Create response filename (replace .md with _response.json)
            response_filename = prompt_file.stem + "_response.json"
            response_path = responses_dir / response_filename

            # Save the full result as JSON
            with response_path.open('w', encoding='utf-8') as f:
                json.dump(result, f, ensure_ascii=False, indent=2)

            print(f"  ✓ Response saved to: {response_filename}")

            if result['success']:
                print(f"  ✓ Duration: {result['duration_seconds']:.2f}s")
                if result.get('used_json_format'):
                    print(f"  ✓ Used JSON format enforcement")
                if attempt > 1:
                    print(f"  ✓ Completed after {attempt} attempts")
            else:
                print(f"  ✗ Error: {result['error']}")

            results.append(result)

            # Add delay between requests (except for the last one)
            if i < len(files_to_process):
                time.sleep(delay_between_requests)

    except KeyboardInterrupt:
        print(
            f"\n⚠️  Processing interrupted by user after {len(results)} prompts")
        print(f"   Partial results will be saved")


def save_summary_report(
    results: List[Dict[str, Any]],
    output_path: Path
) -> None:
    """
    Save a summary report of all Ollama processing results.

    Args:
        results: List of result dictionaries from process_prompts_with_ollama
        output_path: Path to save the summary report
    """
    successful = [r for r in results if r.get('success', False)]
    failed = [r for r in results if not r.get('success', False)]

    total_duration = sum(r.get('duration_seconds', 0) for r in successful)
    avg_duration = total_duration / len(successful) if successful else 0

    # Calculate retry statistics
    total_retry_attempts = sum(r.get('retry_attempts', 1) for r in results)
    avg_retry_attempts = total_retry_attempts / len(results) if results else 0
    max_retry_attempts = max((r.get('retry_attempts', 1)
                             for r in results), default=1)
    prompts_with_retries = len(
        [r for r in results if r.get('retry_attempts', 1) > 1])

    summary = {
        'processing_summary': {
            'total_prompts': len(results),
            'successful': len(successful),
            'failed': len(failed),
            'success_rate': len(successful) / len(results) if results else 0,
            'total_duration_seconds': total_duration,
            'average_duration_seconds': avg_duration,
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
            'retry_statistics': {
                'total_retry_attempts': total_retry_attempts,
                'average_retry_attempts': avg_retry_attempts,
                'max_retry_attempts': max_retry_attempts,
                'prompts_with_retries': prompts_with_retries,
                'retry_rate': prompts_with_retries / len(results) if results else 0
            }
        },
        'failed_prompts': [
            {
                'file': r.get('prompt_file'),
                'error': r.get('error'),
                'retry_attempts': r.get('retry_attempts', 1)
            }
            for r in failed
        ],
        'detailed_results': results
    }

    with output_path.open('w', encoding='utf-8') as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    print(f"\nProcessing Summary:")
    print(f"  Total prompts: {len(results)}")
    print(f"  Successful: {len(successful)}")
    print(f"  Failed: {len(failed)}")
    print(f"  Success rate: {len(successful) / len(results) * 100:.1f}%")
    if successful:
        print(f"  Total duration: {total_duration:.2f}s")
        print(f"  Average duration: {avg_duration:.2f}s")
    print(f"  Retry Statistics:")
    print(f"    Total retry attempts: {total_retry_attempts}")
    print(f"    Average retry attempts: {avg_retry_attempts:.2f}")
    print(f"    Max retry attempts: {max_retry_attempts}")
    print(f"    Prompts with retries: {prompts_with_retries}")
    print(
        f"    Retry rate: {prompts_with_retries / len(results) * 100:.1f}%" if results else "    Retry rate: 0%")
    print(f"  Summary saved to: {output_path}")
