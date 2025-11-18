from shiny import App, ui, render, reactive, req
import time
import os
import base64

from neuromap.tasks.notify import send_email_task

def _first_file(val):
    if val is None:
        return None
    if isinstance(val, list):
        return val[0] if val else None
    return val

app_ui = ui.page_fluid(
    # Ensure our custom stylesheet is loaded (served from /www/styles.css)
    ui.tags.head(
        ui.tags.style(
            """
:root{
    /* slightly lighter background tones to match request */
    --bg-1: #0b3550; /* lighter deep navy */
    --bg-2: #0e4a73; /* lighter muted blue */
    --panel: rgba(10,24,42,0.6);
    --accent: #2bb0ff; /* cyan accent */
    --accent-2: #4da6ff;
    --muted: #9fb6d3;
    --glass: rgba(255,255,255,0.04);
}

/* Page background and base font */
html, body {
    height: 100%;
}
body {
    font-family: "Inter", "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    margin: 0;
    padding: 0;
    color: var(--muted);
    background: linear-gradient(135deg, var(--bg-1) 0%, var(--bg-2) 100%);
    -webkit-font-smoothing:antialiased;
    display: flex;
    align-items: center;
    justify-content: center;
}

/* Hero header */
.hero {
    width: 100%;
    max-width: 980px;
    margin: 32px;
    text-align: center;
}
.hero-inner {
    display:flex;
    align-items:center;
    gap:18px;
    justify-content:center;
}
.logo {
    width:72px;
    height:72px;
    object-fit:contain;
    border-radius:12px;
    box-shadow: 0 6px 18px rgba(43,176,255,0.12), inset 0 1px 0 rgba(255,255,255,0.02);
}
.hero h1, .hero h2 {
    margin:0;
    color: #e6f7ff;
    font-weight:700;
    letter-spacing:0.6px;
    font-size:36px; /* smaller, more balanced */
}
.hero p.lead {
    margin:6px 0 0 0;
    color: var(--muted);
    font-size:15px;
}

/* Main UI container - frosted glass */
.container {
    width: 100%;
    max-width: 980px;
    margin: 8px auto;
    background: linear-gradient(180deg, rgba(255,255,255,0.02), rgba(255,255,255,0.01));
    border-radius: 14px;
    padding: 22px;
    box-shadow: 0 8px 30px rgba(2,8,23,0.6), 0 2px 6px rgba(0,0,0,0.25);
    border: 1px solid rgba(255,255,255,0.04);
    backdrop-filter: blur(6px) saturate(140%);
}

.grid {
    display: grid;
    grid-template-columns: 1fr 340px;
    gap: 18px;
    align-items: start;
}

.panel {
    background: var(--panel);
    padding: 18px;
    border-radius: 10px;
    border: 1px solid var(--glass);
    min-height: 220px;
}

.input-group {
    margin-bottom: 14px;
}
.input-group label {
    display:block;
    margin-bottom:8px;
    color: var(--muted);
    font-size:14px;
}

/* Form controls look modern */
input[type="number"],
input[type="text"],
input[type="file"],
select, textarea {
    width:100%;
    padding:10px 12px;
    border-radius:8px;
    border:1px solid rgba(255,255,255,0.06);
    background: rgba(255,255,255,0.02);
    color: #e7f6ff;
    outline: none;
}
input::placeholder, textarea::placeholder { color: rgba(230,247,255,0.35); }

.button, button {
    display:inline-block;
    background: linear-gradient(90deg, var(--accent), var(--accent-2));
    color: #021328;
    padding:10px 16px;
    border-radius:10px;
    border:none;
    font-weight:700;
    cursor:pointer;
    box-shadow: 0 6px 20px rgba(43,176,255,0.12);
}
.button:hover, button:hover { transform: translateY(-1px); }

/* Output text blocks */
.output-text {
    white-space:pre-wrap;
    color: #dff6ff;
    font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, "Roboto Mono", monospace;
    font-size:13px;
}

#process_status {
    font-weight:600;
    color: var(--accent-2);
}

/* Small helpers */
.muted { color: var(--muted); }

/* Responsive adjustments */
@media (max-width: 920px){
    .grid { grid-template-columns: 1fr; }
    .hero { margin: 18px; }
}
            """
        )
    ),
    # Hero header — logo + title
    ui.tags.div(
        ui.tags.div(
                                        # Prefer an inline-embedded PNG if available (avoids static-serving issues).
                        ui.tags.div(
                                                # Try to embed the PNG as a data URL; fall back to the direct path which may be served in some environments.
                                                ui.tags.img(
                                                    src=(lambda: (
                                                        (lambda p: (open(p, 'rb').read()))(os.path.join(os.path.dirname(__file__), 'www', 'logo.png'))
                                                        and ('data:image/png;base64,' + base64.b64encode(open(os.path.join(os.path.dirname(__file__), 'www', 'logo.png'), 'rb').read()).decode('ascii'))
                                                    ) )(),
                                                    class_="logo",
                                                    alt="NeuroChron logo",
                                                    style="display:block;",
                                                    onerror="this.style.display='none';document.getElementById('logo_svg').style.display='block'"
                                                ),
                                            ui.HTML('''
                                            <svg id="logo_svg" xmlns="http://www.w3.org/2000/svg" width="72" height="72" viewBox="0 0 400 120" class="logo" role="img" aria-label="NeuroChron logo" style="display:none;">
                <defs>
                    <linearGradient id="g1" x1="0%" x2="100%" y1="0%" y2="100%">
                        <stop offset="0%" stop-color="#2bb0ff"/>
                        <stop offset="100%" stop-color="#4da6ff"/>
                    </linearGradient>
                </defs>
                <g transform="translate(10,10)">
                    <path d="M40 10 C55 5, 75 5, 90 16 C105 27, 110 45, 98 60 C90 72, 70 78, 56 74 C44 71, 30 62, 24 50 C18 38, 21 22, 34 14 C36 13,38 11,40 10 Z" fill="url(#g1)"/>
                    <path d="M96 34 C104 36, 110 44, 110 52 C110 64, 102 76, 92 82" fill="none" stroke="#bfe8ff" stroke-width="2" opacity="0.85"/>
                </g>
            </svg>
            ''')
                                    ),
            ui.tags.div(
                ui.h1("NeuroChron"),
                ui.p("Brain MRI Analysis", class_="lead"),
            ),
            class_="hero-inner",
        ),
        class_="hero",
    ),

    # Main container with grid layout
    ui.tags.div(
        ui.tags.div(
            # Left column: inputs
            ui.tags.div(
                ui.input_numeric("age", "Chronological Age", value=25, min=0, max=120),
                ui.input_text("email", "Notification Email", value=""),
                ui.input_file("mri_file", "Upload MRI (DICOM format)", accept=[".dcm"]),
                ui.hr(),
                ui.output_text("upload_info"),
                class_="panel",
            ),

            # Right column: status and upload UI
            ui.tags.div(
                ui.tags.h4("Status"),
                ui.output_text("process_status"),
                ui.output_ui("upload_status"),
                class_="panel",
                id="right_panel",
            ),

            class_="grid",
        ),
        class_="container",
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
