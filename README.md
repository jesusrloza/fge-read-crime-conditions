# fge-read-crime-conditions

Internal analytics tooling for the State Attorney General of Michoacán to batch-evaluate crime records against specific, request-driven conditions using Ollama-hosted LLMs and produce structured statistics plus summary reports.

## Why this project exists

Prosecutorial teams often need quick answers to bespoke investigative questions (e.g., "Which kidnapping cases mention highway blockades?"). This repository accelerates that workflow by combining:

- **Prompt generation** for large batches of crime narrations pulled from Excel.
- **LLM-backed evaluation** using self-hosted Ollama models (such as `gpt-oss`).
- **Result aggregation** that preserves ground-truth inputs and produces auditable summaries.

The stack favors transparency (plain markdown prompts + JSON responses) and can be adapted to new legal conditions with minimal effort.

## Features

- Deterministic prompt builder with templating, JSON fencing, and deduplication by NUC.
- Ollama client with configurable retries, JSON parsing safeguards, and summary export.
- Automatic preservation of original narrative context in downstream responses.
- Summary exporter that converts LLM decisions into Excel-ready analytics tables.
- "src" layout with typed helper modules that are easy to extend and test.

## Project structure

```
├── src/
│   ├── 0_update_prompt_config.py  # Sync prompt config from reference files
│   ├── 1_generate_prompts.py      # Prompt creation entry point
│   ├── 2_process_ollama.py        # Batch prompts through Ollama
│   ├── 3_create_summary.py        # Excel summary extraction
│   └── utils/
│       ├── prompt_builder.py      # Shared prompt templating helpers
│       └── ollama_client.py       # Ollama chat orchestration
├── prompt/
│   ├── data/                    # Excel inputs kept out of version control by default
│   ├── reference/               # Human-editable condition/template source files
│   └── prompt_config.json       # Serialized configuration consumed by the tooling
├── output/                      # Generated prompts, responses, and summary exports
├── requirements.txt             # Locked dependency pins (mirrors pyproject)
├── pyproject.toml               # Packaging + metadata for publishing/install
└── README.md
```

## Getting started

### Prerequisites

- Python 3.10 or newer (pandas ≥ 2.3 requires Python 3.10+).
- [Ollama](https://ollama.com/) installed locally with your model of choice (defaults to `gpt-oss:latest`).
- Git LFS if you plan to store large Excel files or Ollama outputs inside the repo.

### Installation

1. Clone the repository and move into the project folder.
2. Create and activate a virtual environment:

   ```bash
   python -m venv .venv
   source .venv/bin/activate            # macOS / Linux
   .venv\\Scripts\\activate           # Windows PowerShell
   ```

3. Install the package in editable mode (recommended for contributors):

   ```bash
   pip install -e .
   ```

4. Verify installation by running one of the numbered scripts (see below), for example:

   ```bash
   python src/1_generate_prompts.py
   ```

### Configuration inputs

Key configurable assets can be found under the `prompt/` directory:

| File                             | Purpose                                                                                                  |
| -------------------------------- | -------------------------------------------------------------------------------------------------------- |
| `prompt/prompt_config.json`      | Unified configuration containing the condition, prompt template, model name, and optional output schema. |
| `prompt/reference/condition.txt` | Plain-text reference for the current investigative condition.                                            |
| `prompt/reference/template.txt`  | Prompt body with placeholders `{{CONDITION}}`, `{{RECORD_JSON}}`, and `{{OUTPUT_SCHEMA}}`.               |
| `prompt/data/sample.xlsx`        | Example Excel input; replace with campaign-specific extracts (gitignored by default).                    |

Swap in a new `sample.xlsx` or replicate the folder for each campaign.

## CLI workflows

Once the package is installed, run the numbered scripts directly with Python:

| Command                                | Description                                                                                                   |
| -------------------------------------- | ------------------------------------------------------------------------------------------------------------- |
| `python src/0_update_prompt_config.py` | Refreshes `prompt/prompt_config.json` from files in `prompt/reference/`.                                      |
| `python src/1_generate_prompts.py`     | Reads `prompt/data/sample.xlsx`, deduplicates by NUC, and emits markdown prompts into `output/prompts/`.      |
| `python src/2_process_ollama.py`       | Sends generated prompts to Ollama, writes JSON responses in `output/responses/`, and generates a run summary. |
| `python src/3_create_summary.py`       | Walks responses and writes an analytics spreadsheet to `output/summary/results.xlsx`.                         |

Each script accepts the defaults shown in code. For campaign-specific paths, fork the scripts or add argument parsing (see "Future enhancements").

## Running the pipeline

1. **Prepare data**: Place your Excel source in `prompt/data/sample.xlsx` and confirm `prompt_config.json` describes the desired condition/template.
2. **Update prompt config** (optional, run when `prompt/reference` changes):

   ```bash
   python src/0_update_prompt_config.py
   ```

3. **Generate prompts**:

   ```bash
   python src/1_generate_prompts.py
   ```

4. **Process with Ollama** (ensure the Ollama daemon is running):

   ```bash
   ollama run gpt-oss:latest --help   # optional sanity check
   python src/2_process_ollama.py
   ```

5. **Export summary**:

   ```bash
   python src/3_create_summary.py
   ```

Outputs are stored under `output/` and reuse existing files when re-run. Failed requests are retried automatically; inspect `_response.json` files for full context.

## Data handling & privacy

- Never commit raw case files containing personal data. The root `.gitignore` already excludes `output/` and `prompt/data/` to keep sensitive artifacts out of version control.
- When sharing prompt templates publicly, redact sensitive condition wording and examples.
- The repository intentionally keeps prompts and responses as human-readable markdown/JSON to support auditing.

## Contributing

1. Fork and branch from `main` (the repository currently tracks only the `main` branch).
2. Run `pip install -e .[dev]` once a dev extras group is defined (see roadmap).
3. Apply formatting/tests before opening a PR.
4. Use conventional commit messages when possible (`feat:`, `fix:`, etc.).

Please open an issue for architectural changes or enhancements.

## License

The project currently ships without an open-source license. Until one is selected and added to `LICENSE`, the default assumption is "All rights reserved". Choose a license before making the repository public.
