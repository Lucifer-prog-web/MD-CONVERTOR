# Document-to-Markdown Converter

A Python + Streamlit app that converts supported document formats into Markdown (`.md`). It is based on the supplied notebook workflow and packages it as a GitHub-ready application.

## Features

- Upload one or multiple documents.
- Supports PDF, DOCX, PPTX, XLSX, XLS, CSV, HTML/HTM, TXT, JSON, XML, EPUB, and Markdown.
- Uses MarkItDown for document conversion.
- Attempts OCR for scanned PDFs using PyMuPDF, Pillow, and Tesseract.
- Imports publicly accessible Google Docs, Sheets, Slides, and Google Drive files by shareable link.
- Converts pasted notes into Markdown.
- Downloads each Markdown file individually or downloads all results as a ZIP.
- Optionally combines converted content into a configurable number of merged Markdown files inside a ZIP.
- Shows a preview and reports per-file conversion errors.

## Project structure

```text
document-to-markdown-converter/
├── app.py
├── requirements.txt
├── .gitignore
└── README.md
```

## Requirements

- Python 3.10 or newer is recommended.
- `pip`
- Tesseract OCR installed on the machine if scanned-PDF OCR is needed.
- Google Drive links must be accessible to the machine running the app. Google Docs/Sheets/Slides export usually requires sharing permission such as **Anyone with the link**.

## Setup and run locally

### 1. Clone the repository

```bash
git clone https://github.com/YOUR-USERNAME/YOUR-REPOSITORY.git
cd YOUR-REPOSITORY
```

Replace the URL with your repository URL.

### 2. Create and activate a virtual environment

Windows PowerShell:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

Windows Command Prompt:

```bat
python -m venv .venv
.venv\Scripts\activate.bat
```

macOS/Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install Python dependencies

```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Install Tesseract OCR (for scanned PDFs)

OCR is an optional fallback for PDFs that produce almost no extractable text.

- **Windows:** Install Tesseract OCR using a trusted distribution, then make sure `tesseract.exe` is on your `PATH`. If needed, configure the executable path in your local environment or in the code.
- **Ubuntu/Debian:** `sudo apt-get update && sudo apt-get install -y tesseract-ocr`
- **macOS with Homebrew:** `brew install tesseract`

The app can still convert ordinary, text-based documents without Tesseract, but OCR will fail if the executable is missing and a scanned PDF requires it.

### 5. Start the app

```bash
streamlit run app.py
```

Streamlit will show a local URL in the terminal, typically `http://localhost:8501`.

## How to use

1. Open the app in your browser.
2. Choose **Upload documents**, **Google Drive / Docs link**, or **Paste text**.
3. Add one or more inputs.
4. Choose whether to create merged Markdown bundles and how many bundle files to create.
5. Click **Convert documents**.
6. Preview the output and download individual `.md` files, a ZIP of all converted files, and optionally a ZIP of merged Markdown files.

## Supported input extensions

`pdf`, `docx`, `pptx`, `xlsx`, `xls`, `csv`, `html`, `htm`, `txt`, `json`, `xml`, `epub`, `md`

Only documents are intended to be accepted. Images, executables, archives, and other unsupported file types are not accepted as direct uploads.

## Notes and limitations

- Conversion quality depends on the source file, its layout, and the parsers used. Complex formatting, embedded objects, charts, and tables may not be represented perfectly in Markdown.
- OCR quality depends on scan resolution, language, orientation, and Tesseract configuration.
- The app does not guarantee lossless conversion. Review the generated Markdown, especially for important tables or scanned documents.
- The Google Drive downloader works only when the link and file permissions allow access; it cannot bypass authentication or access controls.
- The app processes uploaded documents in the environment where Streamlit is running. For public deployments, configure suitable file-size limits, access controls, and privacy practices.
- This project does not intentionally summarize, rewrite, or deduplicate converted document content. Some information may nevertheless be lost due to the conversion libraries or source format.

## Dependencies

See [`requirements.txt`](requirements.txt).

## License

No license has been selected for this repository. Add a `LICENSE` file if you want to specify how others may use, modify, and distribute this project.
