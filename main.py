from pathlib import Path
import os
import queue
import secrets
import threading
import tkinter as tk
from tkinter import filedialog

# SKIP LLM
os.environ["SKIP_LLM"] = "1"

from bottle import Bottle, HTTPError, static_file
from scan_modules.job_dispatch import get_file_statuses, start_job

import eel
import hashlib
import pymupdf
import copy


# WEBUI FOLDER
PROJECT_FOLDER = Path(__file__).resolve().parent
eel.init(str(PROJECT_FOLDER / "WebUI"))

# WEB APP
web_app = Bottle()

# OPEN DOCUMENTS
open_documents = {}
located_issues = {}
dismissed_issues = {}
review_statuses = {}
import_statuses = {}

# CONVERSION QUEUE
conversion_queue = queue.Queue()

# PDF.JS ASSETS
PDFJS_FOLDER = PROJECT_FOLDER / "WebUI" / "vendor" / "pdfjs"

# PREVIEW DIR
PREVIEW_FOLDER = PROJECT_FOLDER / "WebUI" / "pdf_previews"

# PDF OUT DIR
GENERATED_PDF_FOLDER = PROJECT_FOLDER / "generated_pdfs"


def convert_docx_file(docx_path):
    """DOCX TO PDF."""
    try:
        from docx2pdf import convert
    except ImportError as error:
        raise RuntimeError("DOCX conversion requires docx2pdf.") from error

    # OUT DIR
    GENERATED_PDF_FOLDER.mkdir(parents=True, exist_ok=True)

    # OUTPUT PATH
    pdf_path = GENERATED_PDF_FOLDER / f"{secrets.token_urlsafe(12)}-{docx_path.stem}.pdf"

    # CONVERT
    convert(str(docx_path), str(pdf_path))

    # CHECK PDF
    if not pdf_path.is_file():
        raise RuntimeError(f"Could not convert {docx_path.name} to PDF.")

    return pdf_path


def process_docx_import(import_id, source_path):
    """START DOCX JOB."""
    import_statuses[import_id]["state"] = "converting"

    try:
        # CONVERT DOCX
        pdf_path = convert_docx_file(source_path)
        file_path = str(pdf_path)
        located_issues.pop(file_path, None)
        dismissed_issues.pop(file_path, None)
        review_statuses.pop(file_path, None)

        # URL
        document_id = secrets.token_urlsafe(24)
        open_documents[document_id] = pdf_path

        # START JOB
        import_statuses[import_id].update({
            "state": "processing",
            "filePath": file_path,
            "documentUrl": f"/documents/{document_id}",
        })
        start_job(file_path)
    except Exception as error:
        import_statuses[import_id].update({
            "state": "error",
            "error": str(error),
        })


def run_conversion_queue():
    """RUN DOCX QUEUE."""
    while True:
        import_id, source_path = conversion_queue.get()
        try:
            process_docx_import(import_id, source_path)
        finally:
            conversion_queue.task_done()


# START CONVERTER
threading.Thread(target=run_conversion_queue, daemon=True).start()


def locate_issue_rectangles(document, issue):
    """FIND ISSUE RECTS."""
    try:
        page_number = int(issue.get("page"))
    except (TypeError, ValueError):
        return [], "unavailable"

    text = issue.get("text")
    if not 1 <= page_number <= len(document) or not isinstance(text, str):
        return [], "unavailable"

    # MATCH TEXT
    needle = " ".join(text.split())
    if not needle:
        return [], "unavailable"

    page = document[page_number - 1]
    try:
        found = page.search_for(needle)
        # RETRY RAW TEXT
        if not found and needle != text:
            found = page.search_for(text)
    except Exception as error:
        print(f"Could not search page {page_number}: {error}")
        return [], "unavailable"

    rectangles = []
    seen = set()
    for rect in found:
        # PDF TO VIEW
        pdf_rect = rect * ~page.transformation_matrix
        values = tuple(round(value, 4) for value in pdf_rect)
        if values not in seen:
            seen.add(values)
            rectangles.append(list(pdf_rect))

    return rectangles, "available" if rectangles else "unavailable"


def deduplicate_issues(issues):
    """KEEP TOP ISSUE PER TEXT."""
    selected = {}

    def severity(issue):
        color = str(issue.get("color", "")).lower()
        return {"red": 2, "yellow": 1}.get(color, 0)

    for index, issue in enumerate(issues):
        text = issue.get("text")
        normalized_text = " ".join(str(text).casefold().split()) if text is not None else ""

        # EMPTY ISSUES
        if not normalized_text:
            selected[("unmatched", index)] = (index, issue)
            continue

        key = (str(issue.get("page")), normalized_text)
        current = selected.get(key)
        if current is None or severity(issue) > severity(current[1]):
            selected[key] = (index, issue)

    return [issue for _, issue in sorted(selected.values(), key=lambda item: item[0])]


# SERVE PDFJS
@web_app.get("/vendor/pdfjs/<asset_name>")
def serve_pdfjs_module(asset_name):
    allowed_assets = {"pdf.min.mjs", "pdf.worker.min.mjs"}

    if asset_name not in allowed_assets:
        raise HTTPError(404, "PDF.js asset not found.")

    return static_file(
        asset_name,
        root=str(PDFJS_FOLDER),
        mimetype="application/javascript"
    )


# SERVE OPEN PDF
@web_app.get("/documents/<document_id>")
def serve_document(document_id):
    pdf_path = open_documents.get(document_id)

    if not pdf_path or not pdf_path.is_file():
        raise HTTPError(404, "PDF not found.")

    return static_file(
        pdf_path.name,
        root=str(pdf_path.parent),
        mimetype="application/pdf"
    )


# IMPORT FILES
@eel.expose
def import_pdfs():

    # FILE PICKER
    dialog = tk.Tk()
    dialog.withdraw()
    dialog.attributes("-topmost", True)

    try:
        selected_paths = filedialog.askopenfilenames(
            parent=dialog,
            title="Choose Files",
            filetypes=[
                ("Supported files", "*.pdf *.docx"),
                ("PDF files", "*.pdf"),
                ("Word files", "*.docx"),
            ],
        )
    finally:
        dialog.destroy()

    # NO FILES
    if not selected_paths:
        return []

    selected_documents = []
    for selected_path in selected_paths:
        # SOURCE
        source_path = Path(selected_path).resolve()
        selected_documents.append((source_path, source_path.name))

    imported_documents = []
    for source_path, display_name in selected_documents:
        # QUEUE DOCX
        if source_path.suffix.lower() == ".docx":
            import_id = secrets.token_urlsafe(24)
            import_statuses[import_id] = {
                "state": "queued",
                "displayName": display_name,
            }
            conversion_queue.put((import_id, source_path))
            imported_documents.append({
                "importId": import_id,
                "displayName": display_name,
                "state": "queued",
            })
            continue

        # PDF
        pdf_path = source_path
        file_path = str(pdf_path)
        located_issues.pop(file_path, None)
        dismissed_issues.pop(file_path, None)
        review_statuses.pop(file_path, None)

        # URL
        document_id = secrets.token_urlsafe(24)
        open_documents[document_id] = pdf_path

        # START JOB
        start_job(file_path)

        # ADD DOCUMENT
        imported_documents.append({
            "filePath": file_path,
            "displayName": display_name,
            "state": "processing",
            "documentUrl": f"/documents/{document_id}",
        })

    return imported_documents


# IMPORT STATUS
@eel.expose
def get_import_statuses():
    statuses = []
    for import_id, status in import_statuses.items():
        statuses.append(dict(status, importId=import_id))
    return copy.deepcopy(statuses)


# FILE STATUS
@eel.expose
def get_processing_statuses():
    statuses = copy.deepcopy(get_file_statuses())
    for status in statuses:
        path = status.get("filePath")
        if status.get("processState") == "processed" and path:
            issues = deduplicate_issues(status.get("issues", []))
            # JOB RACE
            # ISSUE CACHE
            fingerprint = repr(issues)
            cached = located_issues.get(path)
            if cached is None or cached[0] != fingerprint:
                # CLEAR DISMISSED ON NEW JOB
                if cached is not None:
                    dismissed_issues.pop(path, None)
                enriched = []
                try:
                    with pymupdf.open(path) as document:
                        for index, issue in enumerate(issues):
                            result = dict(issue, id=f"issue-{index}", rectangles=[], location="unavailable")
                            rectangles, location = locate_issue_rectangles(document, issue)
                            result["rectangles"] = rectangles
                            result["location"] = location
                            enriched.append(result)
                except Exception as error:
                    print(f"Could not locate issues in {path}: {error}")
                    enriched = [dict(issue, id=f"issue-{index}", rectangles=[], location="unavailable") for index, issue in enumerate(issues)]
                located_issues[path] = (fingerprint, enriched)
            dismissed_ids = dismissed_issues.get(path, set())
            status["issues"] = [
                issue for issue in located_issues[path][1]
                if issue["id"] not in dismissed_ids
            ]

        if path in review_statuses:
            status["processState"] = review_statuses[path]
    return statuses


# HIDE ISSUE
@eel.expose
def dismiss_issue(file_path, issue_id):
    """HIDE ISSUE AND MARK."""
    if not isinstance(file_path, str) or not isinstance(issue_id, str):
        return False

    dismissed_issues.setdefault(file_path, set()).add(issue_id)
    return True


# SAVE REVIEW
@eel.expose
def set_review_status(file_path, review_status):
    """SAVE FILE REVIEW."""
    if not isinstance(file_path, str) or review_status not in {"accepted", "denied"}:
        return False

    review_statuses[file_path] = review_status
    return True

# MAKE PDF PAGES
@eel.expose
def render_pdf_pages(file_path):

    # PDF FILE
    pdf_path = Path(file_path).resolve()

    # CHECK FILE
    if not pdf_path.is_file() or pdf_path.suffix.lower() != ".pdf":
        raise ValueError("PDF file not found.")

    # PREVIEW FOLDER
    file_id = hashlib.sha256(str(pdf_path).encode()).hexdigest()
    output_folder = PREVIEW_FOLDER / file_id
    output_folder.mkdir(parents=True, exist_ok=True)

    # OPEN PDF
    document = pymupdf.open(pdf_path)
    page_urls = []

    try:
        for page_number, page in enumerate(document):
            image_name = f"page-{page_number + 1}.png"
            image_path = output_folder / image_name

            # MAKE PAGE IMG
            if not image_path.exists():
                image = page.get_pixmap(
                    matrix=pymupdf.Matrix(1.5, 1.5),
                    alpha=False
                )
                image.save(image_path)

            # IMG URL
            page_urls.append(f"pdf_previews/{file_id}/{image_name}")
    finally:
        document.close()

    return page_urls


# START WEBUI
eel.start("WebUI.html", host="127.0.0.1", mode="default", app=web_app)
