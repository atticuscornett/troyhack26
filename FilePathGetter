from pathlib import Path
import tkinter as tk
from tkinter import filedialog

from job_dispatch import get_file_statuses, start_job

import eel


# WEBUI FOLDER
PROJECT_FOLDER = Path(__file__).resolve().parent
eel.init(str(PROJECT_FOLDER / "WebUI"))


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


    # FILE PATH
    file_path = str(Path(selected_path).resolve())

    # START OTHER PYTHON CODE
    start_job(file_path)

    # RETURN PATH TO WEBUI
    return file_path


# GET FILE STATUSES
@eel.expose
def get_processing_statuses():
    return get_file_statuses()


# START WEBUI
eel.start("WebUI.html", size=(1400, 900))
