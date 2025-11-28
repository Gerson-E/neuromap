# NeuroChron - Quick Start Guide

Get the project running in 5 minutes.

## Prerequisites
- Python 3.11+
- Docker Desktop (for FreeSurfer processing)

## Setup Steps

### 1. Install Dependencies
```bash
cd neuromap
pip install -r requirements.txt
pip install -r backend/api/requirements.txt
```

### 2. Create Environment File
```bash
cp .env.example .env
```

**Email is OPTIONAL** - If you don't have SendGrid, just leave the `.env` file as is. The system will work fine without email notifications.

### 3. Get FreeSurfer License (Free)
1. Register at https://surfer.nmr.mgh.harvard.edu/registration.html
2. Save license to `neuromap/backend/license/license.txt`

### 4. Start the Backend API
```bash
cd neuromap/backend/api
python3 -m uvicorn app:app --reload
```

Should see: `NeuroChron API started successfully!`

### 5. Start the Frontend (New Terminal)
```bash
cd neuromap
shiny run app.py --port 8080
```

### 6. Access the App
- **Web UI:** http://localhost:8080
- **API Docs:** http://localhost:8000/docs

## Quick Test (No Docker Required)
```bash
cd neuromap
python3 test_quick.py
```

This tests the brain age prediction in ~5 seconds using pre-processed data.

## Troubleshooting

**"Address already in use"** - Port 8000 is already in use:
```bash
lsof -ti:8000 | xargs kill -9
```

**"Could not import module 'app.main'"** - Wrong directory or command:
```bash
cd neuromap/backend/api
python3 -m uvicorn app:app --reload  # NOT app.main:app
```

**"Docker not found"** - Make sure Docker Desktop is running:
```bash
open -a Docker
```

**Email errors** - Email is optional. The system works without SendGrid configured.

## Full Documentation
See `TEAMMATE_SETUP.md` for complete details, architecture, and advanced usage.
