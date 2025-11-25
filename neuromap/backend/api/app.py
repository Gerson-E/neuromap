"""
FastAPI application for NeuroChron brain age analysis.
Provides REST API endpoints for MRI upload, processing, and result retrieval.
"""

from fastapi import FastAPI, UploadFile, File, Form, Depends, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import Optional
import uuid
from pathlib import Path
import sys

# Add current directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

# Import local modules
try:
    # Try relative imports first (when run as module)
    from . import database, models, file_processor
    from .database import get_db
except ImportError:
    # Fall back to direct imports (when run with uvicorn)
    import database
    import models
    import file_processor
    from database import get_db

# Initialize FastAPI app
app = FastAPI(
    title="NeuroChron API",
    description="Brain Age Analysis API - Upload MRI scans and get biological brain age predictions",
    version="1.0.0"
)

# CORS middleware for Shiny frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict to specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize database on startup
@app.on_event("startup")
def startup_event():
    """Initialize database tables on application startup."""
    database.init_db()
    print("NeuroChron API started successfully!")


@app.get("/")
def read_root():
    """Health check endpoint."""
    return {
        "service": "NeuroChron API",
        "status": "running",
        "version": "1.0.0"
    }


@app.get("/health")
def health_check():
    """Detailed health check with database connectivity."""
    try:
        # Test database connection
        db = next(database.get_db())
        db.execute("SELECT 1")
        db.close()

        return {
            "status": "healthy",
            "database": "connected",
            "api": "operational"
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "database": "disconnected",
            "error": str(e)
        }


@app.post("/api/upload", response_model=models.JobResponse)
async def upload_mri(
    file: UploadFile = File(..., description="DICOM MRI file"),
    chronological_age: int = Form(..., description="Patient's chronological age (must be > 21)"),
    email: str = Form(..., description="Email for notifications"),
    db: Session = Depends(get_db)
):
    """
    Upload a DICOM MRI file and create a new processing job.

    - **file**: DICOM format MRI scan
    - **chronological_age**: Patient's age (must be > 21)
    - **email**: Email address for result notifications

    Returns job_id for tracking processing status.
    """

    # Validate inputs using Pydantic model
    try:
        job_data = models.JobCreate(chronological_age=chronological_age, email=email)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Validate file format
    if not file.filename.lower().endswith(('.dcm', '.dicom')):
        raise HTTPException(
            status_code=400,
            detail="Invalid file format. Please upload a DICOM file (.dcm or .dicom)"
        )

    # Generate IDs
    job_id = str(uuid.uuid4())
    subject_id = file_processor.generate_subject_id()

    try:
        # Save uploaded file temporarily
        file_content = await file.read()
        temp_file = file_processor.save_uploaded_file(file_content, file.filename)

        # Process file: validate and convert DICOM to NIfTI
        original_path, nifti_path = file_processor.process_uploaded_file(
            str(temp_file),
            job_id,
            subject_id
        )

        # Create job record in database
        job = database.create_job(
            db=db,
            job_id=job_id,
            subject_id=subject_id,
            file_path=str(original_path),
            chronological_age=job_data.chronological_age,
            email=job_data.email
        )

        # Update with NIfTI path
        database.update_job_nifti_path(db, job_id, str(nifti_path))

        # Clean up temporary file
        if temp_file.exists():
            temp_file.unlink()

        return models.JobResponse(
            job_id=job.id,
            subject_id=job.subject_id,
            status=models.JobStatus(job.status),
            created_at=job.created_at,
            message="File uploaded successfully. Use POST /api/jobs/{job_id}/process to start processing."
        )

    except file_processor.FileProcessingError as e:
        raise HTTPException(status_code=400, detail=f"File processing error: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@app.post("/api/jobs/{job_id}/process")
async def process_job(
    job_id: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Start processing a job (FreeSurfer + brain age prediction).

    This endpoint triggers the background processing pipeline:
    1. FreeSurfer preprocessing (~3.5 hours)
    2. Brain age prediction
    3. Email notification

    Processing runs in the background. Use GET /api/jobs/{job_id}/status to check progress.
    """

    # Get job from database
    job = database.get_job_by_id(db, job_id)

    if not job:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

    if job.status != "pending":
        raise HTTPException(
            status_code=400,
            detail=f"Job is already {job.status}. Can only process pending jobs."
        )

    # Import worker here to avoid circular dependency
    try:
        from . import worker
    except ImportError:
        import worker

    # Update status to processing
    database.update_job_status(db, job_id, "processing")

    # Add background task
    background_tasks.add_task(worker.process_pipeline, job_id)

    return {
        "job_id": job_id,
        "status": "processing",
        "message": "Processing started. This will take approximately 3.5 hours."
    }


@app.get("/api/jobs/{job_id}/status", response_model=models.JobStatusResponse)
def get_job_status(job_id: str, db: Session = Depends(get_db)):
    """
    Get the current status of a processing job.

    Returns job status: pending, processing, completed, or failed.
    """

    job = database.get_job_by_id(db, job_id)

    if not job:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

    return models.JobStatusResponse(
        job_id=job.id,
        status=models.JobStatus(job.status),
        created_at=job.created_at,
        completed_at=job.completed_at,
        error_message=job.error_message,
        chronological_age=job.chronological_age,
        progress_message=models.format_progress_message(job.status)
    )


@app.get("/api/jobs/{job_id}/results", response_model=models.JobResultResponse)
def get_job_results(job_id: str, db: Session = Depends(get_db)):
    """
    Get prediction results for a completed job.

    Returns brain age prediction and brain age gap.
    Only available for completed jobs.
    """

    job = database.get_job_by_id(db, job_id)

    if not job:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

    if job.status == "failed":
        return models.JobResultResponse(
            job_id=job.id,
            status=models.JobStatus.FAILED,
            result=None,
            error_message=job.error_message,
            completed_at=job.completed_at
        )

    if job.status != "completed":
        return models.JobResultResponse(
            job_id=job.id,
            status=models.JobStatus(job.status),
            result=None,
            error_message="Results not yet available. Job is still processing.",
            completed_at=None
        )

    # Get result from database
    result = database.get_result_by_job_id(db, job_id)

    if not result:
        raise HTTPException(
            status_code=500,
            detail="Job marked as completed but results not found in database"
        )

    # Format result data
    result_data = models.ResultData(
        predicted_age=result.predicted_age,
        chronological_age=job.chronological_age,
        brain_age_gap=result.brain_age_gap,
        interpretation=models.format_interpretation(result.brain_age_gap)
    )

    return models.JobResultResponse(
        job_id=job.id,
        status=models.JobStatus.COMPLETED,
        result=result_data,
        error_message=None,
        completed_at=job.completed_at
    )


@app.get("/api/jobs", response_model=list[models.JobStatusResponse])
def list_jobs(
    status: Optional[str] = None,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """
    List all jobs, optionally filtered by status.

    - **status**: Filter by status (pending, processing, completed, failed)
    - **limit**: Maximum number of jobs to return (default 100)
    """

    if status:
        jobs = database.get_jobs_by_status(db, status, limit)
    else:
        jobs = database.get_all_jobs(db, limit)

    return [
        models.JobStatusResponse(
            job_id=job.id,
            status=models.JobStatus(job.status),
            created_at=job.created_at,
            completed_at=job.completed_at,
            error_message=job.error_message,
            chronological_age=job.chronological_age,
            progress_message=models.format_progress_message(job.status)
        )
        for job in jobs
    ]


@app.delete("/api/jobs/{job_id}")
def delete_job(job_id: str, db: Session = Depends(get_db)):
    """
    Delete a job and its associated files.

    WARNING: This permanently deletes the job, results, and uploaded files.
    """

    job = database.get_job_by_id(db, job_id)

    if not job:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

    # Clean up files
    file_processor.cleanup_job_files(job_id, job.subject_id)

    # Delete from database (cascade will delete result too)
    db.delete(job)
    db.commit()

    return {
        "job_id": job_id,
        "status": "deleted",
        "message": "Job and associated files deleted successfully"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
