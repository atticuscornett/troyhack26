from pathlib import Path
import secrets
import tkinter as tk
from tkinter import filedialog

from bottle import Bottle, HTTPError, static_file
from job_dispatch import get_file_statuses, start_job

import eel
import hashlib
import pymupdf


# WEBUI FOLDER
PROJECT_FOLDER = Path(__file__).resolve().parent
eel.init(str(PROJECT_FOLDER / "WebUI"))

# WEB APP
web_app = Bottle()

# OPEN DOCUMENTS
open_documents = {}

# PDF.JS ASSETS
PDFJS_FOLDER = PROJECT_FOLDER / "WebUI" / "vendor" / "pdfjs"

# PDF PREVIEW FOLDER
PREVIEW_FOLDER = PROJECT_FOLDER / "WebUI" / "pdf_previews"


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
    return get_file_statuses()

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
eel.start("WebUI.html", size=(1400, 900), app=web_app)
