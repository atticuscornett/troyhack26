from pathlib import Path
import secrets
import tkinter as tk
from tkinter import filedialog

from bottle import Bottle, HTTPError, static_file
from job_dispatch import get_file_statuses, start_job

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

# PDF.JS ASSETS
PDFJS_FOLDER = PROJECT_FOLDER / "WebUI" / "vendor" / "pdfjs"

# PDF PREVIEW FOLDER
PREVIEW_FOLDER = PROJECT_FOLDER / "WebUI" / "pdf_previews"


def locate_issue_rectangles(document, issue):
    """LOCATE ISSUE RECTANGLES."""
    try:
        page_number = int(issue.get("page"))
    except (TypeError, ValueError):
        return [], "unavailable"

    text = issue.get("text")
    if not 1 <= page_number <= len(document) or not isinstance(text, str):
        return [], "unavailable"

    # NORMALIZE MATCH TEXT
    needle = " ".join(text.split())
    if not needle:
        return [], "unavailable"

    page = document[page_number - 1]
    try:
        found = page.search_for(needle)
        # RETRY ORIGINAL TEXT
        if not found and needle != text:
            found = page.search_for(text)
    except Exception as error:
        print(f"Could not search page {page_number}: {error}")
        return [], "unavailable"

    rectangles = []
    seen = set()
    for rect in found:
        # CONVERT PDF COORDINATES
        pdf_rect = rect * ~page.transformation_matrix
        values = tuple(round(value, 4) for value in pdf_rect)
        if values not in seen:
            seen.add(values)
            rectangles.append(list(pdf_rect))

    return rectangles, "available" if rectangles else "unavailable"


# SERVE PDF.JS MODULE
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


# IMPORT PDF
@eel.expose
def import_pdf():

    # NATIVE FILE PICKER
    dialog = tk.Tk()
    dialog.withdraw()
    dialog.attributes("-topmost", True)

    try:
        selected_path = filedialog.askopenfilename(
            parent=dialog,
            title="Choose a PDF",
            filetypes=[("PDF files", "*.pdf")],
        )
    finally:
        dialog.destroy()

    # NO FILE SELECTED
    if not selected_path:
        return None


    # PDF FILE
    pdf_path = Path(selected_path).resolve()
    file_path = str(pdf_path)
    located_issues.pop(file_path, None)

    # DOCUMENT URL
    document_id = secrets.token_urlsafe(24)
    open_documents[document_id] = pdf_path

    # START OTHER PYTHON CODE
    start_job(file_path)

    # RETURN DOCUMENT INFO
    return {
        "filePath": file_path,
        "documentUrl": f"/documents/{document_id}",
    }


# GET FILE STATUSES
@eel.expose
def get_processing_statuses():
    statuses = copy.deepcopy(get_file_statuses())
    for status in statuses:
        path = status.get("filePath")
        if status.get("processState") != "processed" or not path:
            continue
        issues = status.get("issues", [])
        # HANDLE DISPATCH RACE
        # REFRESH ISSUE CACHE
        fingerprint = repr(issues)
        cached = located_issues.get(path)
        if cached is None or cached[0] != fingerprint:
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
        status["issues"] = located_issues[path][1]
    return statuses

# RENDER PDF PAGES
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

            # CREATE PAGE IMAGE
            if not image_path.exists():
                image = page.get_pixmap(
                    matrix=pymupdf.Matrix(1.5, 1.5),
                    alpha=False
                )
                image.save(image_path)

            # WEBUI IMAGE URL
            page_urls.append(f"pdf_previews/{file_id}/{image_name}")
    finally:
        document.close()

    return page_urls


# START WEBUI
eel.start("WebUI.html", host="127.0.0.1", mode="default", app=web_app)
