from shiny import App, ui, render, reactive, req
import time

from neuromap.tasks.notify import send_email_task

def _first_file(val):
    if val is None:
        return None
    if isinstance(val, list):
        return val[0] if val else None
    return val

app_ui = ui.page_fluid(
    ui.h2("Brain MRI Analysis"),
    ui.page_sidebar(
        ui.sidebar(
            ui.input_numeric("age", "Chronological Age", value=25, min=0, max=120),
            ui.input_text("email", "Notification Email", value=""),
            ui.input_file("mri_file", "Upload MRI (DICOM format)", accept=[".dcm"]),
            ui.hr(),
            ui.output_text("upload_info"),
            ui.output_text("process_status"),   # <- id stays 'process_status'
        ),
        ui.output_ui("upload_status"),
    ),
)

def run_long_process(file_path: str, age: int) -> str:
    time.sleep(2)  # simulate work
    return "success"

def server(input, output, session):
    status_val = reactive.Value("Idle")   # <- renamed

    @output
    @render.text
    def upload_info():
        f = _first_file(input.mri_file())
        if f is not None:
            return f"File uploaded: {f['name']}\nSize: {f['size']/1024:.2f} KB"
        return "No file uploaded"

    @output
    @render.ui
    def upload_status():
        f = _first_file(input.mri_file())
        if f is not None:
            return ui.div(
                ui.tags.h4("Upload successful!"),
                ui.tags.p(f"Patient age: {input.age()}"),
                ui.tags.p("File is ready for preprocessing"),
            )
        return ui.div(
            ui.tags.h4("Waiting for file upload..."),
            ui.tags.p("Please upload a DICOM format MRI file"),
        )

    # Keep output id 'process_status' but use a different Python function name
    @output(id="process_status")
    @render.text
    def _process_status_text():
        return f"Status: {status_val()}"

    @reactive.Effect
    @reactive.event(input.mri_file)
    def _on_file_uploaded():
        f = _first_file(input.mri_file()); req(f)

        to_email = (input.email() or "").strip()
        if not to_email:
            status_val.set("No email provided; skipping notification.")
            return

        dicom_path = f["datapath"]
        age = int(input.age())

        try:
            status_val.set("Processing...")
            status = run_long_process(dicom_path, age)
            status_val.set(f"Processing complete: {status}")

            subject = f"[NeuroChron] Brain MRI Analysis finished ({status})"
            context = {
                "job_name": "Brain MRI Analysis",
                "status": status,
                "extra": f"File: {f['name']} • Age: {age}",
            }
            # You can comment this next line to test UI without sending email
            send_email_task(to_email, subject, context)
            status_val.set(f"Email sent to {to_email}")

        except Exception as e:
            status_val.set(f"Error: {type(e).__name__}: {e}")

app = App(app_ui, server)
