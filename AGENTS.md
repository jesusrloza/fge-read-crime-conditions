# Crime Narrations Analysis - Agent Setup Guide

## Project Overview

This project analyzes crime narrations using Ollama and legal analysis prompts. It processes Excel files containing crime data and generates structured prompts for AI analysis.

## Environment Setup

### Prerequisites

- Python 3.8+
- Virtual environment (`.venv` directory should exist)
- Required packages installed via `pip install -r requirements.txt`

### Installing Dependencies

After activating the virtual environment, install the required packages:

```bash
# Activate virtual environment first (see below)
source .venv/bin/activate  # Linux/macOS
# or
source .venv/Scripts/activate  # Windows Git Bash / MSYS terminals (e.g., with Starship)
# or
.venv\Scripts\activate     # Windows

# Install dependencies
pip install -r requirements.txt
```

### Activating Virtual Environment

Before running any Python modules, you MUST activate the virtual environment. Use the appropriate command for your operating system:

#### Windows (Command Prompt)

```cmd
.venv\Scripts\activate
```

#### Windows (PowerShell)

```powershell
.venv\Scripts\Activate.ps1
```

#### Linux / macOS (bash/zsh)

```bash
source .venv/bin/activate
```

#### Alternative activation paths

If the standard paths don't work, try these alternatives:

**Windows:**

- `.venv\Scripts\activate.bat` (older Windows versions)
- `.\.venv\Scripts\Activate.ps1` (if using relative path)
- `source .venv/Scripts/activate` (Git Bash / MSYS terminals)

**Linux/macOS:**

- `source .venv/bin/activate` (most common)
- `source ./venv/bin/activate` (if using relative path)
- `source ~/.venv/bin/activate` (if venv is in home directory)

### Running the Application

Once the virtual environment is activated, you can run the main application:

```bash
# Run the main analysis pipeline
python -m src.main

# Run with specific options
python -m src.main --skip-ollama  # Skip Ollama processing
```

### Running Tests

```bash
# Run prompt generation test
python -m test.test_prompt_generation

# Or run directly
python test/test_prompt_generation.py
```

### Project Structure

```
├── src/                    # Main application code
│   ├── __init__.py
│   ├── main.py            # Main entry point
│   ├── ollama_client.py   # Ollama integration
│   └── prompt_builder.py  # Prompt generation
├── test/                  # Test suite
│   ├── __init__.py
│   └── test_prompt_generation.py
├── data/                  # Input data files
├── output/                # Generated outputs
│   ├── prompts/          # Generated prompts
│   ├── responses/        # Ollama responses
│   └── test/             # Test outputs
├── prompt/                # Configuration files
│   └── prompt_config.json # Unified prompt configuration
└── .venv/                 # Virtual environment (created by user)
```

### Troubleshooting

#### Virtual Environment Issues

- **"activate: No such file or directory"**: Check if `.venv` directory exists and contains the activation scripts
- **Permission denied**: On Linux/macOS, make sure the activation script is executable: `chmod +x .venv/bin/activate`
- **Command not found**: Ensure you're using the correct path separator (`\` for Windows, `/` for Unix)

#### Python Module Issues

- **"ModuleNotFoundError"**: Ensure virtual environment is activated and packages are installed
- **"No module named 'src'"**: Run from project root directory using `python -m src.main`

#### Common Commands

```bash
# Check Python version
python --version

# Check if virtual environment is active (should show path to .venv)
which python

# Install/update requirements
pip install -r requirements.txt

# Deactivate virtual environment
deactivate
```

#### VS Code integrated terminal quirk

Some VS Code terminals occasionally drop the very first character typed or pasted (e.g., `mv` becomes `v`). If a command fails unexpectedly, press ↑ to recall it and re-run—on the second try it usually executes correctly.

### Development Notes

- Always activate the virtual environment before development
- Use `python -m` syntax for running modules to ensure proper package resolution
- Test outputs are saved to `output/test/` directory
- Configuration is managed through `prompt/prompt_config.json`
