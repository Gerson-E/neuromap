"""
FastAPI application for NeuroChron brain age analysis.
Provides REST API endpoints for MRI upload, processing, and result retrieval.
"""

from fastapi import FastAPI, UploadFile, File, Form, Depends, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import Optional
import uuid
from pathlib import Path
import sys
import numpy as np
import io
import matplotlib
matplotlib.use('Agg')  # Non-interactive backend
import matplotlib.pyplot as plt

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
        from sqlalchemy import text
        db = next(database.get_db())
        db.execute(text("SELECT 1"))
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

    # Check if saliency map is available
    saliency_map_available = result.saliency_map_path is not None
    saliency_map_url = f"/api/jobs/{job_id}/saliency" if saliency_map_available else None

    # Format result data
    result_data = models.ResultData(
        predicted_age=result.predicted_age,
        chronological_age=job.chronological_age,
        brain_age_gap=result.brain_age_gap,
        interpretation=models.format_interpretation(result.brain_age_gap),
        saliency_map_available=saliency_map_available,
        saliency_map_url=saliency_map_url
    )

    return models.JobResultResponse(
        job_id=job.id,
        status=models.JobStatus.COMPLETED,
        result=result_data,
        error_message=None,
        completed_at=job.completed_at
    )


@app.get("/api/jobs/{job_id}/saliency")
def get_saliency_map(job_id: str, db: Session = Depends(get_db)):
    """
    Get saliency map visualization for a completed job.

    Returns a PNG image showing three orthogonal slices (axial, coronal, sagittal)
    of the 3D saliency map, highlighting which brain regions contributed most
    to the age prediction.
    """

    job = database.get_job_by_id(db, job_id)

    if not job:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

    if job.status != "completed":
        raise HTTPException(
            status_code=400,
            detail=f"Saliency map not yet available. Job status: {job.status}"
        )

    # Get result to find saliency map path
    result = database.get_result_by_job_id(db, job_id)

    if not result or not result.saliency_map_path:
        raise HTTPException(
            status_code=404,
            detail="Saliency map not available for this job"
        )

    saliency_map_path = Path(result.saliency_map_path)

    if not saliency_map_path.exists():
        raise HTTPException(
            status_code=500,
            detail=f"Saliency map file not found at {saliency_map_path}"
        )

    try:
        # Load saliency map (.npy file contains 3D volume)
        saliency_map = np.load(saliency_map_path)

        # Get middle slices for each view
        x, y, z = saliency_map.shape
        mid_x, mid_y, mid_z = x // 2, y // 2, z // 2

        # Create visualization with three views
        fig, axes = plt.subplots(1, 3, figsize=(15, 5))

        # Axial view (looking down from top)
        axes[0].imshow(saliency_map[:, :, mid_z].T, cmap='hot', origin='lower')
        axes[0].set_title('Axial View (Top-Down)', fontsize=12, fontweight='bold')
        axes[0].axis('off')

        # Coronal view (looking from front)
        axes[1].imshow(saliency_map[:, mid_y, :].T, cmap='hot', origin='lower')
        axes[1].set_title('Coronal View (Front)', fontsize=12, fontweight='bold')
        axes[1].axis('off')

        # Sagittal view (looking from side)
        axes[2].imshow(saliency_map[mid_x, :, :].T, cmap='hot', origin='lower')
        axes[2].set_title('Sagittal View (Side)', fontsize=12, fontweight='bold')
        axes[2].axis('off')

        # Add overall title
        fig.suptitle(
            f'Brain Age Saliency Map - {job.subject_id}',
            fontsize=14,
            fontweight='bold',
            y=0.98
        )

        # Add colorbar
        fig.colorbar(
            axes[0].images[0],
            ax=axes,
            orientation='horizontal',
            fraction=0.046,
            pad=0.04,
            label='Importance for Age Prediction'
        )

        plt.tight_layout()

        # Save to bytes buffer
        buf = io.BytesIO()
        plt.savefig(buf, format='png', dpi=150, bbox_inches='tight', facecolor='white')
        plt.close(fig)
        buf.seek(0)

        # Return as image response
        return StreamingResponse(
            buf,
            media_type="image/png",
            headers={"Content-Disposition": f"inline; filename=saliency_map_{job.subject_id}.png"}
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate saliency map visualization: {str(e)}"
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


@app.post("/api/test/predict")
async def test_predict_with_existing_subject(
    chronological_age: int = Form(...),
    email: str = Form(...),
    subject_id: str = Form(default="002"),
    db: Session = Depends(get_db)
):
    """
    TEST ENDPOINT: Skip FreeSurfer and use existing subject data.

    This endpoint bypasses the 3.5 hour FreeSurfer processing by using
    existing preprocessed data (subject 002 by default).

    Perfect for testing without Docker!
    """

    # Validate age
    if chronological_age < 22:
        raise HTTPException(status_code=400, detail="Age must be > 21")

    # Create test job with unique subject_id to avoid constraint errors
    job_id = str(uuid.uuid4())
    # Use unique test subject ID but still reference existing data for prediction
    test_subject_id = f"test_{subject_id}_{job_id[:8]}"

    job = database.create_job(
        db=db,
        job_id=job_id,
        subject_id=test_subject_id,
        file_path=f"/test/{subject_id}",
        chronological_age=chronological_age,
        email=email
    )

    # Immediately process (skip FreeSurfer, go straight to prediction)
    try:
        import brain_age_predictor

        # Update to processing
        database.update_job_status(db, job_id, "processing")

        # Run brain age prediction (fast - a few seconds)
        # Use the original subject_id (002) for prediction, not the unique test ID
        predicted_age = brain_age_predictor.predict_brain_age(subject_id)

        # Generate saliency map
        saliency_map_path = None
        try:
            saliency_map_path = brain_age_predictor.generate_saliency_map_for_subject(subject_id)
            print(f"✓ Saliency map generated for test: {saliency_map_path}")
        except Exception as e:
            print(f"⚠ Warning: Could not generate saliency map for test: {e}")

        # Save results
        result = database.create_result(
            db=db,
            job_id=job_id,
            predicted_age=predicted_age,
            chronological_age=chronological_age,
            saliency_map_path=str(saliency_map_path) if saliency_map_path else None
        )

        # Update to completed
        database.update_job_status(db, job_id, "completed")

        # Send email in background
        brain_age_gap = predicted_age - chronological_age

        if brain_age_gap > 0:
            interpretation = f"Your brain appears {abs(brain_age_gap):.1f} years older than your chronological age"
        elif brain_age_gap < 0:
            interpretation = f"Your brain appears {abs(brain_age_gap):.1f} years younger than your chronological age"
        else:
            interpretation = "Your brain age matches your chronological age"

        context = {
            "subject_id": f"{subject_id} (test)",
            "status": "completed",
            "predicted_age": f"{predicted_age:.2f}",
            "chronological_age": str(chronological_age),
            "brain_age_gap": f"{brain_age_gap:+.2f}",
            "interpretation": interpretation,
        }

        try:
            # Add path for neuromap imports
            import sys
            from pathlib import Path
            NEUROMAP_ROOT = Path(__file__).parent.parent.parent.parent
            sys.path.insert(0, str(NEUROMAP_ROOT))

            from neuromap.tasks.notify import send_email_task
            send_email_task(email, f"[NeuroChron] Brain Age Analysis Complete - {subject_id}", context)
        except Exception as email_error:
            print(f"Warning: Email notification failed: {email_error}")
            # Don't fail the test if email fails

        # Check if saliency map was generated
        saliency_map_available = saliency_map_path is not None
        saliency_map_url = f"/api/jobs/{job_id}/saliency" if saliency_map_available else None

        return {
            "job_id": job_id,
            "subject_id": f"{subject_id} (test)",
            "status": "completed",
            "predicted_age": predicted_age,
            "brain_age_gap": brain_age_gap,
            "saliency_map_available": saliency_map_available,
            "saliency_map_url": saliency_map_url,
            "message": "Test prediction completed successfully (using existing subject data)"
        }

    except Exception as e:
        database.update_job_status(db, job_id, "failed", str(e))
        raise HTTPException(status_code=500, detail=f"Prediction failed: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
