# Backend Testing Guide

Quick guide to test the NeuroChron backend without waiting for FreeSurfer (3.5 hours).

## Setup

1. **Install dependencies:**
   ```bash
   cd neuromap/backend/api
   pip install -r requirements.txt
   ```

2. **Ensure subject 002 exists:**
   The test uses existing FreeSurfer output at `neuromap/backend/subjects/002/mri/brain.mgz`

3. **Configure environment (optional for email testing):**
   ```bash
   # Copy from root .env or create new one
   cp ../../../.env .env
   ```

## Quick Test (5-10 minutes)

Run the integration test suite:

```bash
cd /Users/gersonestrada/Desktop/neuromap/neuromap/backend/api
python test_integration.py
```

This will test:
- ✅ Database operations (SQLite + SQLAlchemy)
- ✅ FreeSurfer environment check
- ✅ Brain age prediction with existing subject 002
- ✅ Email notification setup
- ✅ Complete pipeline (mocked - skips FreeSurfer)

## Test the API Server

1. **Start the FastAPI server:**
   ```bash
   cd /Users/gersonestrada/Desktop/neuromap/neuromap/backend/api
   uvicorn app:app --reload --host 0.0.0.0 --port 8000
   ```

2. **Open interactive API docs:**
   - Visit: http://localhost:8000/docs
   - Try the endpoints:
     - `GET /` - Health check
     - `GET /health` - Detailed health check
     - `GET /api/jobs` - List all jobs

3. **Test with curl (optional):**
   ```bash
   # Health check
   curl http://localhost:8000/health

   # List jobs
   curl http://localhost:8000/api/jobs
   ```

## Component Tests

### Test Brain Age Predictor Only
```bash
cd /Users/gersonestrada/Desktop/neuromap/neuromap/backend/api
python brain_age_predictor.py
```

### Test FreeSurfer Environment
```bash
cd /Users/gersonestrada/Desktop/neuromap/neuromap/backend/api
python freesurfer_runner.py
```

### Test Worker (without FreeSurfer)
```bash
cd /Users/gersonestrada/Desktop/neuromap/neuromap/backend/api
python worker.py
```

## What Gets Tested

### Without Long Waits ✅
- Database CRUD operations
- File processing logic
- Brain age prediction (uses existing subject 002)
- Pipeline orchestration logic
- Error handling

### Skipped (requires 3.5 hours) ⊘
- Full FreeSurfer `recon-all` processing
- DICOM file upload (requires actual DICOM file)

## Expected Output

If all tests pass, you should see:
```
======================================================================
  TEST SUMMARY
======================================================================
✓ PASS - Database Operations
✓ PASS - FreeSurfer Environment
✓ PASS - Brain Age Prediction
✓ PASS - Email Notification
✓ PASS - Complete Pipeline (Mock)

Results: 5/5 tests passed

🎉 All tests passed! Backend is ready.
```

## Troubleshooting

### "Module not found" errors
```bash
# Make sure you're in the right directory
cd /Users/gersonestrada/Desktop/neuromap/neuromap/backend/api

# Install dependencies
pip install -r requirements.txt
```

### "TensorFlow not found" or GPU errors
```bash
# Install TensorFlow (CPU version is fine for testing)
pip install tensorflow>=2.12.0

# The code will automatically use CPU if no GPU is available
```

### "Subject 002 not found"
```bash
# Check if subject 002 exists
ls -la ../subjects/002/mri/brain.mgz

# If missing, you'll need to either:
# 1. Run FreeSurfer on a sample file (takes 3.5 hours)
# 2. Use a different existing subject
```

### "FreeSurfer license not found"
```bash
# Check license location
ls -la ../license/license.txt

# Get a free license from:
# https://surfer.nmr.mgh.harvard.edu/registration.html
```

## Next Steps After Testing

Once tests pass:
1. ✅ Backend is fully functional
2. 🔜 Connect Shiny frontend to API
3. 🔜 Test complete end-to-end flow
4. 🔜 Deploy to production

## Notes

- Tests use existing FreeSurfer output to avoid 3.5 hour wait
- Email sending is mocked unless `.env` is configured
- Database is created at `neuromap/backend/api/data/neuromap.db`
- All test data is cleaned up after tests complete
