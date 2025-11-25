from shiny import App, ui, render, reactive, req
import time
import os
import base64

from neuromap.api_client import (
    check_api_health,
    upload_and_process,
    get_job_status,
    get_job_results,
    APIError
)

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

def check_api_status():
    """Check if API is available."""
    try:
        health = check_api_health()
        return health.get('status') == 'healthy'
    except:
        return False

def server(input, output, session):
    status_val = reactive.Value("Idle")
    job_id_val = reactive.Value(None)
    results_val = reactive.Value(None)

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
        results = results_val()

        if results:
            # Show results when available
            result_data = results.get('result')
            if result_data:
                return ui.div(
                    ui.tags.h4("✓ Analysis Complete!"),
                    ui.tags.p(f"Predicted Brain Age: {result_data['predicted_age']:.2f} years"),
                    ui.tags.p(f"Chronological Age: {result_data['chronological_age']} years"),
                    ui.tags.p(f"Brain Age Gap: {result_data['brain_age_gap']:+.2f} years"),
                    ui.tags.p(f"Interpretation: {result_data['interpretation']}", class_="muted"),
                    ui.tags.p("Email notification sent!", class_="muted"),
                )

        if f is not None:
            return ui.div(
                ui.tags.h4("Upload successful!"),
                ui.tags.p(f"Patient age: {input.age()}"),
                ui.tags.p("Processing will begin automatically..."),
            )

        return ui.div(
            ui.tags.h4("Waiting for file upload..."),
            ui.tags.p("Please upload a DICOM format MRI file"),
        )

    @output(id="process_status")
    @render.text
    def _process_status_text():
        return f"Status: {status_val()}"

    @reactive.Effect
    @reactive.event(input.mri_file)
    def _on_file_uploaded():
        """Handle file upload and start processing via API."""
        f = _first_file(input.mri_file())
        req(f)

        to_email = (input.email() or "").strip()
        if not to_email:
            status_val.set("No email provided; skipping notification.")
            return

        dicom_path = f["datapath"]
        age = int(input.age())

        # Validate age
        if age < 22:
            status_val.set("Error: Age must be > 21 for brain age prediction")
            return

        try:
            # Check API availability
            status_val.set("Checking API connection...")
            if not check_api_status():
                status_val.set("Error: API server not available. Please start the API server.")
                return

            # Upload and start processing
            status_val.set("Uploading file to API...")
            response = upload_and_process(dicom_path, age, to_email)

            job_id = response['job_id']
            job_id_val.set(job_id)

            status_val.set(f"Processing started (Job ID: {job_id[:8]}...)")

            # Start polling for status
            _poll_job_status()

        except APIError as e:
            status_val.set(f"API Error: {str(e)}")
        except Exception as e:
            status_val.set(f"Error: {type(e).__name__}: {e}")

    @reactive.Effect
    def _poll_job_status():
        """Poll job status every 10 seconds."""
        job_id = job_id_val()
        if not job_id:
            return

        try:
            # Get current status
            status_response = get_job_status(job_id)
            current_status = status_response['status']
            progress_msg = status_response.get('progress_message', '')

            # Update status display
            status_val.set(f"{current_status.title()}: {progress_msg}")

            # Check if completed
            if current_status == 'completed':
                # Get results
                results = get_job_results(job_id)
                results_val.set(results)
                status_val.set("Analysis complete! Results ready.")
                return

            # Check if failed
            if current_status == 'failed':
                error_msg = status_response.get('error_message', 'Unknown error')
                status_val.set(f"Failed: {error_msg}")
                return

            # Continue polling if still processing
            if current_status in ['pending', 'processing']:
                # Schedule next poll in 10 seconds
                reactive.invalidate_later(10)

        except APIError as e:
            status_val.set(f"Error checking status: {str(e)}")
        except Exception as e:
            status_val.set(f"Error: {type(e).__name__}: {e}")

app = App(app_ui, server)
