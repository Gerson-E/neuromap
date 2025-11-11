from shiny import App, ui, render, reactive, req
from pathlib import Path
import os
import time

from neuromap.tasks.notify import send_email_task

# ---- UI ----
app_ui = ui.page_fluid(
    ui.h2("Brain MRI Analysis"),
    
    ui.page_sidebar(
        ui.sidebar(
            ui.input_numeric("age", "Chronological Age", value=25, min=0, max=120),
            ui.input_file("mri_file", "Upload MRI (DICOM format)", accept=[".dcm"]),
            ui.hr(),
            ui.output_text("upload_info")
        ),
        ui.output_ui("upload_status")
    )
)

# ---- Domain: your processing function ----
def run_long_process(file_path: str, age: int) -> str:
    """
    Replace this stub with your real pipeline.
    Return a status string like 'success' or 'failed'.
    """
    # Simulate work so you can see the UI update:
    time.sleep(2)
    # TODO: validate DICOM, preprocess, run model, save outputs, etc.
    return "success"

# ---- Server ----
def server(input, output, session):
    # Reactive value to hold the last process status
    process_status = reactive.Value("Idle")

    @output
    @render.text
    def upload_info():
        file = input.mri_file()
        if file is not None:
            return f"File uploaded: {file['name']}\nSize: {file['size']/1024:.2f} KB"
        return "No file uploaded"
    
    @output
    @render.ui
    def upload_status():
        file = input.mri_file()
        if file is not None:
            return ui.div(
                ui.tags.h4("Upload successful!"),
                ui.tags.p(f"Patient age: {input.age()}"),
                ui.tags.p("File is ready for preprocessing")
            )
        return ui.div(
            ui.tags.h4("Waiting for file upload..."),
            ui.tags.p("Please upload a DICOM format MRI file")
        )
    
    # added on 11/11/25
    @output
    @render.text
    def process_status():
        return f"Status: {process_status()}"
    
    # When a file is uploaded, run process + send email
    @reactive.Effect
    @reactive.event(input.mri_file)
    def _on_file_uploaded():
        f = input.mri_file()
        req(f)  # ensure not None

        # Ensure we have an email
        to_email = (input.email() or "").strip()
        if not to_email:
            process_status.set("No email provided; skipping notification.")
            return

        # Persist uploaded file to a temp path (Shiny provides a tmp path already)
        tmp_path = f["datapath"]  # local temp file path provided by Shiny
        age = int(input.age())

        # Run your processing
        try:
            process_status.set("Processing...")
            status = run_long_process(tmp_path, age)
            process_status.set(f"Processing complete: {status}")

            # Build email context and send
            context = {
                "job_name": "Brain MRI Analysis",
                "status": status,
                "extra": f"File: {f['name']} • Age: {age}",
            }
            subject = f"[Neuromap] Brain MRI Analysis finished ({status})"

            # MVP inline send; later you can flip this to Celery .delay(...)
            send_email_task(to_email, subject, context)

        except Exception as e:
            process_status.set(f"Error: {type(e).__name__}: {e}")



app = App(app_ui, server)