#!/usr/bin/env python3
"""
Script to update the prompt_template and condition in prompt_config.json with content from template.txt and condition.txt
"""

import json
import os
from pathlib import Path


def update_prompt_config():
    # Define paths relative to the script location
    script_dir = Path(__file__).parent
    project_root = script_dir.parent

    template_path = project_root / "prompt" / "reference" / "template.txt"
    condition_path = project_root / "prompt" / "reference" / "condition.txt"
    config_path = project_root / "prompt" / "prompt_config.json"

    # Read template content
    try:
        with open(template_path, 'r', encoding='utf-8') as f:
            template_content = f.read().strip()
    except FileNotFoundError:
        print(f"Error: Template file not found at {template_path}")
        return False
    except Exception as e:
        print(f"Error reading template file: {e}")
        return False

    # Read condition content
    try:
        with open(condition_path, 'r', encoding='utf-8') as f:
            condition_content = f.read().strip()
    except FileNotFoundError:
        print(f"Error: Condition file not found at {condition_path}")
        return False
    except Exception as e:
        print(f"Error reading condition file: {e}")
        return False

    # Read current config
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
    except FileNotFoundError:
        print(f"Error: Config file not found at {config_path}")
        return False
    except json.JSONDecodeError as e:
        print(f"Error parsing config JSON: {e}")
        return False
    except Exception as e:
        print(f"Error reading config file: {e}")
        return False

    # Update prompt_template and condition
    config['prompt_template'] = template_content
    config['condition'] = condition_content

    # Write updated config back
    try:
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        print(f"Successfully updated prompt_template in {config_path}")
        return True
    except Exception as e:
        print(f"Error writing config file: {e}")
        return False


if __name__ == "__main__":
    success = update_prompt_config()
    exit(0 if success else 1)
