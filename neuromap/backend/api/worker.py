"""
Background worker for processing brain age analysis pipeline.
Orchestrates FreeSurfer preprocessing, brain age prediction, and email notifications.
"""

import sys
from pathlib import Path

# Add parent directory to path to import neuromap modules
# From: /Users/.../neuromap/neuromap/backend/api/worker.py
# To:   /Users/.../neuromap (need to go up 4 levels)
NEUROMAP_ROOT = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(NEUROMAP_ROOT))

from neuromap.tasks.notify import send_email_task

# Import sibling modules
try:
    from . import database, freesurfer_runner, brain_age_predictor
except ImportError:
    # Fallback for direct execution
    import database, freesurfer_runner, brain_age_predictor


def process_pipeline(job_id: str):
    """
    Execute the complete brain age analysis pipeline for a job.

    Pipeline stages:
    1. Retrieve job from database
    2. Run FreeSurfer preprocessing (~3.5 hours)
    3. Run brain age prediction model
    4. Calculate brain age gap
    5. Save results to database
    6. Send email notification
    7. Update job status to completed/failed

    This function runs as a background task triggered by the API.

    Args:
        job_id: Unique job identifier
    """

    print(f"\n{'='*70}")
    print(f"STARTING PIPELINE FOR JOB: {job_id}")
    print(f"{'='*70}\n")

    # Get database session
    db = next(database.get_db())

    try:
        # Stage 1: Retrieve job
        job = database.get_job_by_id(db, job_id)

        if not job:
            raise Exception(f"Job {job_id} not found in database")

        print(f"Job Details:")
        print(f"  Subject ID: {job.subject_id}")
        print(f"  Chronological Age: {job.chronological_age}")
        print(f"  Email: {job.email}")
        print(f"  Input File: {job.nifti_path}\n")

        # Stage 2: Run FreeSurfer
        print(f"{'='*70}")
        print(f"STAGE 1/4: FreeSurfer Preprocessing")
        print(f"{'='*70}\n")

        try:
            brain_mgz, freesurfer_time = freesurfer_runner.run_freesurfer(
                subject_id=job.subject_id,
                timeout=None  # No timeout (can take 3.5+ hours)
            )

            print(f"\n✓ FreeSurfer completed in {freesurfer_runner.format_time(freesurfer_time)}")
            print(f"✓ Output: {brain_mgz}\n")

        except freesurfer_runner.FreeSurferError as e:
            raise Exception(f"FreeSurfer failed: {str(e)}")

        # Stage 3: Run Brain Age Prediction
        print(f"{'='*70}")
        print(f"STAGE 2/4: Brain Age Prediction")
        print(f"{'='*70}\n")

        try:
            predicted_age = brain_age_predictor.predict_brain_age(
                subject_id=job.subject_id
            )

            brain_age_gap = predicted_age - job.chronological_age

            print(f"\n✓ Brain Age Prediction Results:")
            print(f"  Predicted Age: {predicted_age:.2f} years")
            print(f"  Chronological Age: {job.chronological_age} years")
            print(f"  Brain Age Gap: {brain_age_gap:+.2f} years\n")

        except brain_age_predictor.BrainAgePredictionError as e:
            raise Exception(f"Brain age prediction failed: {str(e)}")

        # Stage 3: Generate Saliency Map
        print(f"{'='*70}")
        print(f"STAGE 3/4: Generating Saliency Map")
        print(f"{'='*70}\n")

        saliency_map_path = None
        try:
            saliency_map_path = brain_age_predictor.generate_saliency_map_for_subject(
                subject_id=job.subject_id
            )

            print(f"\n✓ Saliency map generated:")
            print(f"  Path: {saliency_map_path}\n")

        except Exception as e:
            # Saliency map failure shouldn't fail the entire job
            print(f"⚠ Warning: Failed to generate saliency map: {str(e)}")
            print(f"  Continuing with results without saliency map\n")

        # Stage 4: Save Results
        print(f"{'='*70}")
        print(f"STAGE 4/4: Saving Results & Sending Notification")
        print(f"{'='*70}\n")

        # Save to database
        result = database.create_result(
            db=db,
            job_id=job_id,
            predicted_age=predicted_age,
            chronological_age=job.chronological_age,
            saliency_map_path=str(saliency_map_path) if saliency_map_path else None
        )

        print(f"✓ Results saved to database")

        # Update job status to completed
        database.update_job_status(db, job_id, "completed")
        print(f"✓ Job status updated to completed")

        # Stage 5: Send Email Notification
        try:
            send_notification_email(
                email=job.email,
                subject_id=job.subject_id,
                predicted_age=predicted_age,
                chronological_age=job.chronological_age,
                brain_age_gap=brain_age_gap
            )
            print(f"✓ Email notification sent to {job.email}")

        except Exception as e:
            # Email failure shouldn't fail the job
            print(f"⚠ Warning: Failed to send email notification: {str(e)}")

        print(f"\n{'='*70}")
        print(f"PIPELINE COMPLETED SUCCESSFULLY")
        print(f"Job ID: {job_id}")
        print(f"Predicted Brain Age: {predicted_age:.2f} years")
        print(f"Brain Age Gap: {brain_age_gap:+.2f} years")
        print(f"{'='*70}\n")

    except Exception as e:
        # Handle pipeline failure
        print(f"\n{'='*70}")
        print(f"PIPELINE FAILED")
        print(f"Job ID: {job_id}")
        print(f"Error: {str(e)}")
        print(f"{'='*70}\n")

        # Update job status to failed
        database.update_job_status(
            db=db,
            job_id=job_id,
            status="failed",
            error_message=str(e)
        )

        # Send failure notification email
        try:
            job = database.get_job_by_id(db, job_id)
            if job:
                send_failure_email(
                    email=job.email,
                    subject_id=job.subject_id,
                    error_message=str(e)
                )
                print(f"✓ Failure notification sent to {job.email}")
        except Exception as email_error:
            print(f"⚠ Could not send failure email: {str(email_error)}")

    finally:
        # Close database session
        db.close()


def send_notification_email(
    email: str,
    subject_id: str,
    predicted_age: float,
    chronological_age: int,
    brain_age_gap: float
):
    """
    Send success notification email with brain age results.

    Args:
        email: Recipient email address
        subject_id: Subject identifier
        predicted_age: Predicted brain age
        chronological_age: Patient's chronological age
        brain_age_gap: Brain age gap (predicted - chronological)
    """

    # Format interpretation
    if brain_age_gap > 0:
        interpretation = f"Your brain appears {abs(brain_age_gap):.1f} years older than your chronological age"
    elif brain_age_gap < 0:
        interpretation = f"Your brain appears {abs(brain_age_gap):.1f} years younger than your chronological age"
    else:
        interpretation = "Your brain age matches your chronological age"

    subject = f"[NeuroChron] Brain Age Analysis Complete - {subject_id}"

    context = {
        "job_name": "Brain Age Analysis",
        "status": "completed",
        "subject_id": subject_id,
        "predicted_age": f"{predicted_age:.2f}",
        "chronological_age": str(chronological_age),
        "brain_age_gap": f"{brain_age_gap:+.2f}",
        "interpretation": interpretation,
        "extra": f"Subject: {subject_id}"
    }

    send_email_task(email, subject, context)


def send_failure_email(email: str, subject_id: str, error_message: str):
    """
    Send failure notification email.

    Args:
        email: Recipient email address
        subject_id: Subject identifier
        error_message: Error description
    """

    subject = f"[NeuroChron] Brain Age Analysis Failed - {subject_id}"

    context = {
        "job_name": "Brain Age Analysis",
        "status": "failed",
        "subject_id": subject_id,
        "error": error_message,
        "extra": f"Subject: {subject_id}"
    }

    send_email_task(email, subject, context)


# Test function for local development
def test_pipeline(subject_id: str = "002", chronological_age: int = 45):
    """
    Test the pipeline with an existing FreeSurfer-processed subject.

    This skips the FreeSurfer step and tests only the prediction and email components.

    Args:
        subject_id: Existing subject ID
        chronological_age: Chronological age for testing
    """

    print(f"\n{'='*70}")
    print(f"TESTING PIPELINE (Prediction + Email Only)")
    print(f"{'='*70}\n")

    try:
        # Test brain age prediction
        print("Testing brain age prediction...")
        predicted_age = brain_age_predictor.predict_brain_age(subject_id)
        brain_age_gap = predicted_age - chronological_age

        print(f"\n✓ Prediction successful:")
        print(f"  Predicted Age: {predicted_age:.2f} years")
        print(f"  Chronological Age: {chronological_age} years")
        print(f"  Brain Age Gap: {brain_age_gap:+.2f} years\n")

        # Test email (comment out if you don't want to send)
        # test_email = "test@example.com"
        # print(f"Sending test email to {test_email}...")
        # send_notification_email(
        #     email=test_email,
        #     subject_id=subject_id,
        #     predicted_age=predicted_age,
        #     chronological_age=chronological_age,
        #     brain_age_gap=brain_age_gap
        # )
        # print("✓ Email sent successfully\n")

        print(f"{'='*70}")
        print(f"TEST COMPLETED SUCCESSFULLY")
        print(f"{'='*70}\n")

    except Exception as e:
        print(f"\n✗ Test failed: {str(e)}\n")


if __name__ == "__main__":
    # Run test with existing subject
    test_pipeline(subject_id="002", chronological_age=45)
