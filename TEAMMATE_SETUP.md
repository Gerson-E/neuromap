# NeuroChron Setup Guide

Quick setup guide for running the complete brain age analysis pipeline.

**Prerequisites:** Docker Desktop installed and running on your machine.

---

## 🚀 Quick Start (5 minutes)

### 1. Pull Latest Code

```bash
cd /path/to/neuromap
git pull origin main
```

### 2. Install Python Dependencies

```bash
# Install root dependencies
pip install -r neuromap/requirements.txt

# Install backend API dependencies
pip install -r neuromap/backend/api/requirements.txt
```

### 3. Set Up Environment Variables

```bash
# Copy environment template
cp .env.example .env

# Edit with your credentials
nano .env
```

**Add your SendGrid API key** (for email notifications):
```env
SENDGRID_API_KEY=your_api_key_here
SENDGRID_FROM_EMAIL=noreply@yourdomain.com
SENDGRID_REPLY_TO=support@yourdomain.com
```

> **Note:** SendGrid is optional. System works without it, but won't send email notifications.

### 4. Get FreeSurfer License (2 minutes)

FreeSurfer requires a **free license** for research use:

1. Register at: https://surfer.nmr.mgh.harvard.edu/registration.html
2. You'll receive the license via email instantly
3. Save the license file:

```bash
# Create license directory
mkdir -p neuromap/backend/license

# Save your license as:
# neuromap/backend/license/license.txt
```

The license file should look like:
```
your.email@domain.com
12345
 *AbCdEfGhIj
```

### 5. Verify Docker Setup

```bash
# Check Docker is running
docker --version
# Should output: Docker version 24.x.x

# Check Docker Compose
docker compose version
# Should output: Docker Compose version v2.x.x

# Test FreeSurfer image (this will download ~10GB on first run)
cd neuromap/backend
docker compose run --rm freesurfer recon-all --version
# Should output: freesurfer-darwin-macOS-7.4.1-...
```

> **First run:** Docker will download the FreeSurfer image (~10GB). This takes 10-15 minutes depending on your internet speed.

---

## 🏃 Running the System

### Start the Services

Open two terminal windows:

**Terminal 1: Start the API Server**
```bash
cd neuromap/backend/api
uvicorn app:app --reload --host 0.0.0.0 --port 8000
```

You should see:
```
NeuroChron API started successfully!
INFO:     Application startup complete.
```

**Terminal 2: Start the Shiny Frontend**
```bash
cd neuromap
shiny run app.py --port 8080
```

You should see:
```
INFO:     Uvicorn running on http://127.0.0.1:8080
```

### Access the Application

- **Frontend UI:** http://localhost:8080
- **API Documentation:** http://localhost:8000/docs
- **API Health Check:** http://localhost:8000/health

---

## 🧪 Testing

### Quick Test (5 seconds - No Docker Required)

Test the system without waiting for FreeSurfer:

```bash
cd neuromap
python3 test_quick.py
```

Expected output:
```
✓ API is healthy
✓ Prediction completed in 7.6 seconds

Predicted Age:     81.51 years
Chronological Age: 45 years
Brain Age Gap:     +36.51 years

✓ TEST COMPLETED SUCCESSFULLY!
```

This tests:
- ✅ API connectivity
- ✅ Database operations
- ✅ Brain age model prediction
- ✅ Email system
- ✅ Complete integration (skips FreeSurfer)

### Full Pipeline Test (3.5 hours - With Docker)

Test the complete pipeline including FreeSurfer:

```bash
cd neuromap
python3 test_full_pipeline.py
```

This will:
1. Upload test MRI file
2. Run FreeSurfer preprocessing (~3.5 hours)
3. Run brain age prediction
4. Send email notification
5. Display results

**Or use the Web UI:**
1. Visit http://localhost:8080
2. Enter age (must be > 21) and email
3. Upload a DICOM MRI file
4. Wait ~3.5 hours
5. Receive results via email

---

## 📁 Using Your Own MRI Data

### Preparing Files

The system accepts **DICOM format** MRI files:

1. **T1-weighted MRI scans** (required)
2. **Age > 21 years** (model requirement)
3. **DICOM format** (.dcm extension)

### Upload via Web Interface

1. Go to http://localhost:8080
2. Fill in:
   - **Chronological Age:** Patient's actual age
   - **Email:** For result notifications
3. **Upload DICOM file**
4. Processing starts automatically

### Monitor Progress

**Via Web UI:**
- Real-time status updates every 10 seconds
- Shows current pipeline stage

**Via API:**
```bash
# List all jobs
curl http://localhost:8000/api/jobs

# Check specific job status
curl http://localhost:8000/api/jobs/{job_id}/status

# Get results
curl http://localhost:8000/api/jobs/{job_id}/results
```

**Via Docker:**
```bash
cd neuromap/backend
docker compose logs -f freesurfer
```

---

## ⏱️ Expected Processing Time

- **File Upload:** < 1 second
- **DICOM → NIfTI Conversion:** 1-2 seconds
- **FreeSurfer Preprocessing:** ~3.5 hours
- **Brain Age Prediction:** 5-10 seconds
- **Email Notification:** < 1 second

**Total:** ~3.5 hours per MRI scan

---

## 🐛 Troubleshooting

### "Docker command not found"

Make sure Docker Desktop is running (whale icon in menu bar).

```bash
# Start Docker Desktop from Applications
open -a Docker
```

### "FreeSurfer license not found"

```bash
# Check license file exists
ls -la neuromap/backend/license/license.txt

# Should show file with your license
```

If missing, get a new license from: https://surfer.nmr.mgh.harvard.edu/registration.html

### "API server not available"

```bash
# Check if API is running
curl http://localhost:8000/health

# Should return:
{"status":"healthy","database":"connected","api":"operational"}
```

If not running, start the API:
```bash
cd neuromap/backend/api
uvicorn app:app --reload --port 8000
```

### "Database locked" error

```bash
# Stop all API instances
pkill -f uvicorn

# Restart API
cd neuromap/backend/api
uvicorn app:app --reload --port 8000
```

### FreeSurfer fails with "Out of memory"

FreeSurfer needs ~4-6GB RAM. Close other applications and try again.

### Docker disk space issues

```bash
# Clean up Docker
docker system prune -a --volumes -f

# This frees up space from old containers/images
```

---

## 📊 Understanding Results

### Output Format

When processing completes, you'll receive:

**Via Email:**
```
Predicted Brain Age:  81.51 years
Chronological Age:    45 years
Brain Age Gap:        +36.51 years

Interpretation: Brain appears 36.5 years older than chronological age
```

**Via Web UI:**
- Same information displayed in the Status panel
- Updates automatically when processing completes

**Via API:**
```json
{
  "job_id": "abc123...",
  "status": "completed",
  "result": {
    "predicted_age": 81.51,
    "chronological_age": 45,
    "brain_age_gap": 36.51,
    "interpretation": "Brain appears 36.5 years older..."
  }
}
```

### Brain Age Gap Interpretation

- **Positive gap:** Brain appears older than chronological age
- **Negative gap:** Brain appears younger than chronological age
- **Near zero:** Brain age matches chronological age

> **Note:** This model is valid only for individuals **older than 21 years**. Results for younger individuals are not clinically validated.

---

## 🏗️ System Architecture

```
User (Browser) → Shiny Frontend (Port 8080)
                      ↓ HTTP
                 FastAPI Backend (Port 8000)
                      ↓
                 Background Worker
                      ↓
         ┌────────────────────────────┐
         │  Processing Pipeline       │
         │  1. DICOM → NIfTI         │
         │  2. FreeSurfer (Docker)   │
         │  3. Brain Age Model (TF)  │
         │  4. Save Results (SQLite) │
         │  5. Send Email            │
         └────────────────────────────┘
```

**Components:**
- **Frontend:** Python Shiny (Web UI)
- **Backend:** FastAPI (REST API)
- **Processing:** FreeSurfer 7.4.1 (Docker)
- **Model:** TensorFlow 3D CNN
- **Database:** SQLite
- **Email:** SendGrid API

---

## 📂 Project Structure

```
neuromap/
├── app.py                          # Shiny frontend
├── .env                           # Your environment variables
├── test_quick.py                  # Quick test (no Docker)
├── test_full_pipeline.py          # Full test (with Docker)
├── neuromap/
│   ├── api_client.py              # API client for Shiny
│   ├── config.py                  # Configuration
│   ├── requirements.txt           # Python dependencies
│   └── backend/
│       ├── docker-compose.yml     # Docker configuration
│       ├── input/                 # Input MRI files (NIfTI)
│       ├── subjects/              # FreeSurfer output
│       ├── license/
│       │   └── license.txt        # YOUR FreeSurfer license
│       ├── api/
│       │   ├── app.py            # FastAPI application
│       │   ├── database.py       # Database models
│       │   ├── models.py         # API schemas
│       │   ├── worker.py         # Pipeline orchestrator
│       │   ├── freesurfer_runner.py
│       │   ├── brain_age_predictor.py
│       │   ├── file_processor.py
│       │   ├── requirements.txt  # API dependencies
│       │   └── data/
│       │       └── neuromap.db   # SQLite database
│       └── model/
│           ├── model/
│           │   ├── NativeSpacemodel.py
│           │   └── NativeSpaceWeight.h5  # Model weights (9MB)
│           └── utils/            # Data processing utilities
```

---

## 🔐 Security Notes

- **Don't commit** your `.env` file (contains API keys)
- **Don't commit** `license.txt` (personal license)
- **Don't commit** `.db` files (may contain patient data)

These are already in `.gitignore`.

---

## 📞 Getting Help

### Check Status

```bash
# API health
curl http://localhost:8000/health

# List all jobs
curl http://localhost:8000/api/jobs

# Check specific job
curl http://localhost:8000/api/jobs/{job_id}/status
```

### View Logs

```bash
# API logs (in Terminal 1)
# Just read the terminal output

# Docker logs
cd neuromap/backend
docker compose logs freesurfer
```

### Common Issues

1. **Docker not running:** Start Docker Desktop
2. **License missing:** Get license from FreeSurfer website
3. **Port already in use:** Change port in commands
4. **Out of memory:** Close other apps, increase Docker memory limit

---

## ✅ Checklist Before Running

- [ ] Docker Desktop installed and running
- [ ] Python dependencies installed
- [ ] `.env` file configured (optional for email)
- [ ] FreeSurfer license in `backend/license/license.txt`
- [ ] API server running on port 8000
- [ ] Shiny frontend running on port 8080
- [ ] Can access http://localhost:8080
- [ ] Can access http://localhost:8000/docs

---

## 🎯 Quick Commands Reference

```bash
# Start API
cd neuromap/backend/api && uvicorn app:app --reload --port 8000

# Start Shiny
cd neuromap && shiny run app.py --port 8080

# Quick test
cd neuromap && python3 test_quick.py

# Full pipeline test
cd neuromap && python3 test_full_pipeline.py

# Check API health
curl http://localhost:8000/health

# List jobs
curl http://localhost:8000/api/jobs

# Docker logs
cd neuromap/backend && docker compose logs -f
```

---

**Last updated:** 2025-01-25

**Questions?** Check the troubleshooting section above or review API docs at http://localhost:8000/docs
