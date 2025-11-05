from shiny import App, ui, render, reactive
from pathlib import Path
import os

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

def server(input, output, session):
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

app = App(app_ui, server)