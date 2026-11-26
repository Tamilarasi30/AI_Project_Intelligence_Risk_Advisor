# AI Project Intelligence & Risk Advisor

An AI-driven project intelligence and risk management platform designed to help teams understand project documents, identify risks and blockers, track project health, and obtain actionable recommendations through a document-grounded AI assistant.

## Project Overview

The platform uses a Retrieval-Augmented Generation (RAG) workflow to make project information available to an AI assistant. Users can upload project documents, ask questions about the information contained in them, and generate structured project insights.

**Project:** Development of AI-Driven Enterprise Project Intelligence & Risk Management Platform

## Intended Capabilities

- **Document ingestion:** Import project information from supported document formats (PDF, DOCX, TXT, and CSV, subject to the implementation and installed dependencies).
- **Document-grounded Q&A:** Ask questions about ingested project information using a RAG-based workflow.
- **Project analysis:** Analyze project information for risks, blockers, issues, and relevant insights.
- **Project intelligence:** Provide project health indicators, milestones, scope information, recommendations, and suggested actions where supported by the available source documents.
- **Report generation:** Generate Markdown and Word (DOCX) outputs where supported by the application.
- **Knowledge updates:** Add new project documents to the knowledge base without unnecessarily replacing previously ingested information, if implemented in the current version.

## Technology

- Python
- Retrieval-Augmented Generation (RAG)
- Document processing (including `python-docx` for Word documents)
- AI integration (configure according to the provider used in your code)

Check `requirements.txt` for the project's actual Python dependencies.

## Repository Structure

```text
AI_Project_Intelligence_Risk_Advisor/
├── app.py                 # Application entry point
├── engine.py              # Core orchestration and analysis functions
├── ingestion.py           # Document ingestion and text extraction
├── modules/                # modules  functionality
├── requirements.txt        # Python dependencies
├── README.md               # Project documentation
├── LICENSE                 # MIT license
├── .env.example            # Example environment configuration (if needed)
├── .gitignore              # Files excluded from Git                  
└── tests/                  # Tests 
```

This is a reference layout. Update it to match the files and folders actually committed to the repository.

## Requirements

- Python 3.9 or newer (use the version supported by your dependencies)
- `pip`
- Git
- Any API key or local model configuration required by the AI provider used by this project

## Installation

### 1. Clone the repository

```bash
git clone <YOUR_GITHUB_REPOSITORY_URL>
cd AI_Project_Intelligence_Risk_Advisor
```

### 2. Create and activate a virtual environment

**Windows PowerShell:**

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

If PowerShell blocks activation, you may instead run commands through the environment directly:

```powershell
.\.venv\Scripts\python.exe -m pip install --upgrade pip
```

**macOS / Linux:**

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install dependencies

If the repository contains `requirements.txt`:

```bash
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

If `requirements.txt` is not yet available, install the packages listed/imported by the project. For example, Word document support uses:

```bash
python -m pip install python-docx
```

### 4. Configure environment variables

If the application requires an API key or other configuration, create a local `.env` file using `.env.example` as a template, and fill in your own values.

**Do not commit `.env` files, API keys, passwords, or tokens.**

### 5. Run the application

```bash
python app.py
```

Follow the terminal output and the application's interface or instructions to use it.

## Usage

1. Start the application.
2. Upload or ingest the project documents supported by your version.
3. Allow the documents to be processed and indexed.
4. Ask questions about the project, or run the available project-analysis functions.
5. Review generated risks, blockers, insights, recommendations, and reports.
6. Verify AI-generated results against the original project documents before making project decisions.

## Testing

Run the tests included in the repository, if available. For example:

```bash
python -m pytest
```

If `pytest` is not included in the dependencies, install it in your development environment:

```bash
python -m pip install pytest
```

Document the test results and known limitations here as the project evolves.

## License

This project is licensed under the **MIT License**. See the [`LICENSE`](LICENSE) file for the complete license text.

Copyright notice in the included license:

```text
Copyright (c) 2026 Tamilarasi
```

Retain the copyright and permission notice in copies or substantial portions of the software as required by the MIT License.

## Third-Party Dependencies and Attribution

Third-party libraries remain subject to their own licenses and terms. Review the licenses of the packages and any third-party code, models, datasets, or assets included or used by this project.

- Do not copy third-party source code without complying with its license.
- Preserve copyright, attribution, license, and notice files when required.
- Include third-party license notices for bundled components when their licenses require them.
- Check the terms of any model, dataset, API, or service used by the application; these may have terms separate from the Python package licenses.

The MIT license for this repository does not replace or override third-party licenses.

## Security and Privacy

- Never commit credentials, API keys, personal information, confidential project files, or proprietary datasets.
- Keep local environment files and generated/private data out of version control.
- Review uploaded documents and generated reports before sharing them publicly.
- AI-generated analysis can be incomplete or incorrect; independently validate important decisions.

## Project Status

This project is under active development. Features, installation steps, and dependencies may change as milestones are completed.

## Contributing

Contributions, bug reports, and suggestions are welcome. Before submitting changes:

1. Test your changes locally.
2. Do not include secrets or private data.
3. Preserve applicable third-party notices.
4. Describe changes and known limitations clearly.

---

**Note:** Replace `<YOUR_GITHUB_REPOSITORY_URL>` with your repository's clone URL and update this README to reflect the exact features, dependencies, and file structure in the version you publish.
