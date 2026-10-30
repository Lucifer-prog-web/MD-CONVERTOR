"""Document-to-Markdown Converter — Streamlit application.

Supports document uploads, Google Drive/Docs links, pasted text, OCR for scanned PDFs,
individual Markdown downloads, batch ZIP downloads, and merged Markdown bundles.
"""
from __future__ import annotations

import io
import os
import re
import zipfile
from pathlib import Path
from urllib.parse import unquote, urlparse

import gdown
import pymupdf
import pytesseract
import requests
import streamlit as st
from markitdown import MarkItDown
from PIL import Image

APP_TITLE = "Document to Markdown Converter"
ALLOWED_EXTENSIONS = {
    "pdf", "docx", "pptx", "xlsx", "xls", "csv", "html", "htm",
    "txt", "json", "xml", "epub", "md",
}
MAX_UPLOAD_MB = 200
REQUEST_TIMEOUT = 120


def extension_of(filename: str) -> str:
    return Path(filename).suffix.lower().lstrip(".")


def is_supported(filename: str) -> bool:
    return extension_of(filename) in ALLOWED_EXTENSIONS


def safe_filename(filename: str) -> str:
    """Return a simple filename suitable for a download/archive."""
    name = Path(filename).name
    name = re.sub(r"[^A-Za-z0-9._ -]", "_", name).strip(" .")
    return name or "document"


def normal_convert_bytes(data: bytes, filename: str) -> str:
    """Convert a document using MarkItDown from a temporary local file."""
    suffix = Path(filename).suffix.lower()
    if suffix not in {f".{ext}" for ext in ALLOWED_EXTENSIONS}:
        raise ValueError(f"Unsupported file type: {suffix or '(no extension)'}")
    import tempfile
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(data)
        temp_path = tmp.name
    try:
        return MarkItDown().convert(temp_path).text_content or ""
    finally:
        try:
            os.unlink(temp_path)
        except OSError:
            pass


def ocr_pdf_bytes(data: bytes) -> str:
    """Extract text from a scanned PDF using PyMuPDF and Tesseract."""
    pages: list[str] = []
    with pymupdf.open(stream=data, filetype="pdf") as document:
        for page in document:
            pix = page.get_pixmap(dpi=200, alpha=False)
            image = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
            pages.append(pytesseract.image_to_string(image))
    return "\n\n".join(pages).strip()


def convert_document(data: bytes, filename: str) -> tuple[str, bool]:
    if not is_supported(filename):
        raise ValueError("Only supported document formats are accepted.")
    try:
        text = normal_convert_bytes(data, filename)
    except Exception:
        # OCR fallback is intentionally limited to PDFs.
        if extension_of(filename) != "pdf":
            raise
        text = ""
    if extension_of(filename) == "pdf" and len(text.strip()) < 50:
        ocr_text = ocr_pdf_bytes(data)
        if ocr_text.strip():
            return ocr_text, True
    return text, False


def download_google_drive(link: str) -> tuple[str, bytes]:
    """Download a public/shared Google Drive file or export Docs/Sheets/Slides."""
    link = link.strip()
    match = re.search(
        r"docs\.google\.com/(document|spreadsheets|presentation)/d/([\w-]+)",
        link,
    )
    if match:
        kind, file_id = match.groups()
        fmt = {"document": "docx", "spreadsheets": "xlsx", "presentation": "pptx"}[kind]
        export_url = f"https://docs.google.com/{kind}/d/{file_id}/export?format={fmt}"
        response = requests.get(export_url, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        if "text/html" in response.headers.get("Content-Type", "").lower():
            raise ValueError("The Google file is not publicly accessible. Set access to 'Anyone with the link'.")
        disposition = response.headers.get("Content-Disposition", "")
        found = re.search(r"filename\*=UTF-8''([^;]+)", disposition) or re.search(
            r'filename="([^"]+)"', disposition
        )
        filename = unquote(found.group(1)) if found else f"{file_id}.{fmt}"
        return safe_filename(filename), response.content

    # gdown supports common Google Drive share URLs.
    downloaded = gdown.download(link, output=None, fuzzy=True, quiet=True)
    if not downloaded:
        raise ValueError("Could not download the link. Check the URL and sharing permissions.")
    path = Path(downloaded)
    try:
        return safe_filename(path.name), path.read_bytes()
    finally:
        try:
            path.unlink()
        except OSError:
            pass


def markdown_bytes(text: str) -> bytes:
    return text.encode("utf-8")


def zip_bytes(files: list[tuple[str, bytes]]) -> bytes:
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for filename, content in files:
            archive.writestr(filename, content)
    return output.getvalue()


def split_groups(items: list[dict], requested_groups: int) -> list[list[dict]]:
    if not items:
        return []
    count = max(1, min(int(requested_groups), len(items)))
    quotient, remainder = divmod(len(items), count)
    groups = []
    start = 0
    for i in range(count):
        size = quotient + (1 if i < remainder else 0)
        groups.append(items[start:start + size])
        start += size
    return groups


def merge_groups(results: list[dict], number_of_groups: int) -> bytes:
    grouped_files: list[tuple[str, bytes]] = []
    groups = split_groups(results, number_of_groups)
    for index, group in enumerate(groups, start=1):
        body = "\n\n---\n\n".join(
            f"## Source: {item['source_name']}\n\n{item['text']}" for item in group
        )
        grouped_files.append(
            (f"merged_{index}_of_{len(groups)}.md", body.encode("utf-8"))
        )
    return zip_bytes(grouped_files)


def add_result(results: list[dict], filename: str, data: bytes) -> None:
    if not is_supported(filename):
        raise ValueError(f"{filename}: unsupported file type.")
    text, used_ocr = convert_document(data, filename)
    output_name = f"{Path(safe_filename(filename)).stem or 'document'}.md"
    results.append({
        "source_name": safe_filename(filename),
        "output_name": output_name,
        "text": text,
        "used_ocr": used_ocr,
        "bytes": markdown_bytes(text),
    })


st.set_page_config(page_title=APP_TITLE, page_icon="📄", layout="wide")
st.title("📄 Document to Markdown Converter")
st.caption(
    "Convert supported documents to Markdown. Upload files, use a shareable Google link, "
    "or paste text. Batch conversion and merged Markdown bundles are supported."
)

with st.sidebar:
    st.header("Conversion options")
    st.write("**Supported formats**")
    st.caption(", ".join(sorted(ALLOWED_EXTENSIONS)).upper())
    st.info(
        "Scanned PDF OCR requires the Tesseract OCR executable to be installed on the "
        "computer running this app."
    )
    st.caption(f"Upload guidance: up to {MAX_UPLOAD_MB} MB per file.")

upload_tab, link_tab, paste_tab = st.tabs(
    ["Upload documents", "Google Drive / Docs link", "Paste text"]
)

uploaded_files = []
with upload_tab:
    uploaded_files = st.file_uploader(
        "Choose one or more documents",
        type=sorted(ALLOWED_EXTENSIONS),
        accept_multiple_files=True,
        help="Only supported document formats are accepted; other files are ignored.",
    )

with link_tab:
    drive_link = st.text_input(
        "Shareable Google Drive, Docs, Sheets, or Slides URL",
        placeholder="https://drive.google.com/file/d/…",
    )
    st.caption("The linked file must be accessible to the app, usually with 'Anyone with the link' permission.")

with paste_tab:
    pasted_name = st.text_input("Output filename", value="pasted_notes")
    pasted_text = st.text_area("Paste your text or notes", height=180)

st.divider()
left, right = st.columns(2)
with left:
    merge_enabled = st.checkbox("Also create merged Markdown bundle(s)", value=True)
with right:
    merge_count = st.number_input(
        "Number of merged output files",
        min_value=1,
        max_value=50,
        value=2,
        step=1,
        disabled=not merge_enabled,
        help="The files are distributed as evenly as possible across the requested groups.",
    )

if st.button("Convert documents", type="primary", use_container_width=True):
    inputs: list[tuple[str, bytes]] = []
    errors: list[str] = []

    for uploaded in uploaded_files or []:
        if is_supported(uploaded.name):
            if uploaded.size > MAX_UPLOAD_MB * 1024 * 1024:
                errors.append(f"{uploaded.name}: exceeds the {MAX_UPLOAD_MB} MB app limit.")
            else:
                inputs.append((uploaded.name, uploaded.getvalue()))
        else:
            errors.append(f"{uploaded.name}: skipped because its format is not supported.")

    if drive_link.strip():
        try:
            linked_name, linked_bytes = download_google_drive(drive_link)
            if not is_supported(linked_name):
                errors.append(f"Link download ({linked_name}): unsupported file format.")
            elif len(linked_bytes) > MAX_UPLOAD_MB * 1024 * 1024:
                errors.append(f"{linked_name}: exceeds the {MAX_UPLOAD_MB} MB app limit.")
            else:
                inputs.append((linked_name, linked_bytes))
        except Exception as exc:
            errors.append(f"Link download failed: {exc}")

    if pasted_text.strip():
        clean_stem = safe_filename(pasted_name.strip() or "pasted_notes")
        if not clean_stem.lower().endswith(".txt"):
            clean_stem += ".txt"
        inputs.append((clean_stem, pasted_text.encode("utf-8")))

    results: list[dict] = []
    for filename, data in inputs:
        try:
            add_result(results, filename, data)
        except Exception as exc:
            errors.append(f"{filename}: conversion failed — {exc}")

    st.session_state["conversion_results"] = results
    st.session_state["conversion_errors"] = errors

results = st.session_state.get("conversion_results", [])
errors = st.session_state.get("conversion_errors", [])

for error in errors:
    st.warning(error)

if results:
    st.success(f"Converted {len(results)} document(s).")
    st.dataframe(
        [
            {
                "Source file": item["source_name"],
                "Markdown output": item["output_name"],
                "OCR used": "Yes" if item["used_ocr"] else "No",
                "Characters": len(item["text"]),
            }
            for item in results
        ],
        use_container_width=True,
        hide_index=True,
    )

    st.subheader("Download converted files")
    for index, item in enumerate(results):
        with st.expander(f"{item['source_name']} → {item['output_name']}", expanded=False):
            preview = item["text"][:5000]
            st.text_area(
                "Markdown preview",
                value=preview + ("\n\n[Preview truncated]" if len(item["text"]) > 5000 else ""),
                height=220,
                key=f"preview_{index}",
                disabled=True,
            )
            st.download_button(
                f"Download {item['output_name']}",
                data=item["bytes"],
                file_name=item["output_name"],
                mime="text/markdown",
                key=f"download_md_{index}",
            )

    st.download_button(
        "Download all converted Markdown files (.zip)",
        data=zip_bytes([(item["output_name"], item["bytes"]) for item in results]),
        file_name="converted_md_files.zip",
        mime="application/zip",
        use_container_width=True,
    )

    if merge_enabled:
        st.subheader("Merged Markdown bundles")
        st.caption("Each bundle contains source headings and the converted text; source content is not intentionally summarized or deduplicated.")
        st.download_button(
            "Download merged Markdown bundle(s) (.zip)",
            data=merge_groups(results, int(merge_count)),
            file_name="merged_md_files.zip",
            mime="application/zip",
            use_container_width=True,
        )
else:
    st.info("Add at least one document, Google link, or pasted text, then select **Convert documents**.")

st.caption(
    "Privacy note: conversion happens in the environment hosting this app. Avoid uploading "
    "confidential documents to a public deployment."
)
