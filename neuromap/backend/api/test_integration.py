"""
Integration test script for NeuroChron backend.
Tests all components without waiting for FreeSurfer (uses existing subject 002).
"""

import sys
from pathlib import Path

# Add neuromap root to path
# From: /Users/.../neuromap/neuromap/backend/api/test_integration.py
# To:   /Users/.../neuromap (need to go up 4 levels)
NEUROMAP_ROOT = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(NEUROMAP_ROOT))

import database
import brain_age_predictor
import freesurfer_runner
import uuid


def print_section(title):
    """Print a formatted section header."""
    print(f"\n{'='*70}")
    print(f"  {title}")
    print(f"{'='*70}\n")


def test_database():
    """Test database operations."""
    print_section("TEST 1: Database Operations")

    try:
        # Initialize database
        database.init_db()
        print("✓ Database initialized")

        # Create test job
        db = next(database.get_db())
        job_id = str(uuid.uuid4())
        subject_id = "test_002"

        job = database.create_job(
            db=db,
            job_id=job_id,
            subject_id=subject_id,
            file_path="/tmp/test.dcm",
            chronological_age=45,
            email="test@example.com"
        )
        print(f"✓ Created test job: {job_id}")

        # Update status
        database.update_job_status(db, job_id, "processing")
        print("✓ Updated job status to processing")

        # Create result
        result = database.create_result(
            db=db,
            job_id=job_id,
            predicted_age=52.3,
            chronological_age=45
        )
        print(f"✓ Created result: Brain age gap = {result.brain_age_gap:.2f} years")

        # Update to completed
        database.update_job_status(db, job_id, "completed")
        print("✓ Updated job status to completed")

        # Retrieve job
        retrieved_job = database.get_job_by_id(db, job_id)
        print(f"✓ Retrieved job: status = {retrieved_job.status}")

        # Retrieve result
        retrieved_result = database.get_result_by_job_id(db, job_id)
        print(f"✓ Retrieved result: predicted age = {retrieved_result.predicted_age:.2f} years")

        # Clean up
        db.delete(job)
        db.commit()
        db.close()
        print("✓ Cleaned up test data")

        return True

    except Exception as e:
        print(f"✗ Database test failed: {e}")
        return False


def test_freesurfer_check():
    """Test FreeSurfer environment check."""
    print_section("TEST 2: FreeSurfer Environment")

    try:
        # Check Docker
        freesurfer_runner.check_docker_compose()
        print("✓ Docker Compose available")

        # Check license
        freesurfer_runner.check_freesurfer_license()
        print("✓ FreeSurfer license found")

        # Check existing subject
        status = freesurfer_runner.check_freesurfer_output("002")
        if status["exists"]:
            print("✓ Subject 002 FreeSurfer output found")
            print(f"  Directory: {status['subject_dir']}")

            # Check key files
            for name, info in status["files"].items():
                if info["exists"]:
                    print(f"  ✓ {name}: {info['size_mb']:.2f} MB")
                else:
                    print(f"  ✗ {name}: missing")
        else:
            print("✗ Subject 002 not found")
            return False

        return True

    except Exception as e:
        print(f"✗ FreeSurfer check failed: {e}")
        return False


def test_brain_age_prediction():
    """Test brain age prediction with existing subject."""
    print_section("TEST 3: Brain Age Prediction")

    try:
        # Predict brain age for existing subject
        subject_id = "002"
        chronological_age = 45  # Example age

        print(f"Predicting brain age for subject {subject_id}...")
        predicted_age = brain_age_predictor.predict_brain_age(subject_id)

        brain_age_gap = predicted_age - chronological_age

        print(f"\n✓ Prediction successful!")
        print(f"  Predicted Brain Age: {predicted_age:.2f} years")
        print(f"  Chronological Age: {chronological_age} years")
        print(f"  Brain Age Gap: {brain_age_gap:+.2f} years")

        if brain_age_gap > 0:
            print(f"  → Brain appears {abs(brain_age_gap):.1f} years older")
        elif brain_age_gap < 0:
            print(f"  → Brain appears {abs(brain_age_gap):.1f} years younger")
        else:
            print("  → Brain age matches chronological age")

        return True

    except Exception as e:
        print(f"✗ Brain age prediction failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_email_notification():
    """Test email notification (check configuration only)."""
    print_section("TEST 4: Email Notification")

    try:
        print("Email notification configuration check")

        # Check if email module is importable
        from neuromap.tasks.notify import send_email_task
        print("✓ Email notification module importable")

        # Check if .env is configured
        import os
        from neuromap import config

        if config.SENDGRID_API_KEY:
            print("✓ SendGrid API key configured")
        else:
            print("⚠ SendGrid API key not configured (email won't send)")

        print("  Note: Skipping actual send to avoid test emails")

        return True

    except Exception as e:
        print(f"✗ Email test failed: {e}")
        return False


def test_pipeline_mock():
    """Test complete pipeline with mocked FreeSurfer (uses existing output)."""
    print_section("TEST 5: Complete Pipeline (Mock)")

    try:
        # Create a test job in database
        db = next(database.get_db())
        job_id = str(uuid.uuid4())
        subject_id = "002"  # Use existing FreeSurfer output

        print(f"Creating test job with existing subject {subject_id}...")

        job = database.create_job(
            db=db,
            job_id=job_id,
            subject_id=subject_id,
            file_path="/tmp/test.dcm",
            chronological_age=45,
            email="test@example.com"
        )
        print(f"✓ Created job: {job_id}")

        # Update to processing
        database.update_job_status(db, job_id, "processing")
        print("✓ Status: processing")

        # Skip FreeSurfer (already exists)
        print("⊘ Skipping FreeSurfer (using existing output)")

        # Run brain age prediction
        print("Running brain age prediction...")
        predicted_age = brain_age_predictor.predict_brain_age(subject_id)
        brain_age_gap = predicted_age - job.chronological_age

        print(f"✓ Predicted age: {predicted_age:.2f} years")
        print(f"✓ Brain age gap: {brain_age_gap:+.2f} years")

        # Save results
        result = database.create_result(
            db=db,
            job_id=job_id,
            predicted_age=predicted_age,
            chronological_age=job.chronological_age
        )
        print("✓ Results saved to database")

        # Update to completed
        database.update_job_status(db, job_id, "completed")
        print("✓ Status: completed")

        # Retrieve and verify
        final_job = database.get_job_by_id(db, job_id)
        final_result = database.get_result_by_job_id(db, job_id)

        print(f"\n✓ Pipeline completed successfully!")
        print(f"  Job ID: {final_job.id}")
        print(f"  Status: {final_job.status}")
        print(f"  Predicted Age: {final_result.predicted_age:.2f} years")
        print(f"  Brain Age Gap: {final_result.brain_age_gap:+.2f} years")

        # Clean up
        db.delete(job)
        db.commit()
        db.close()
        print("✓ Cleaned up test data")

        return True

    except Exception as e:
        print(f"✗ Pipeline test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def run_all_tests():
    """Run all integration tests."""
    print("\n" + "="*70)
    print("  NEUROMAP BACKEND INTEGRATION TESTS")
    print("  Testing without FreeSurfer wait time (using existing subject 002)")
    print("="*70)

    results = {
        "Database Operations": test_database(),
        "FreeSurfer Environment": test_freesurfer_check(),
        "Brain Age Prediction": test_brain_age_prediction(),
        "Email Notification": test_email_notification(),
        "Complete Pipeline (Mock)": test_pipeline_mock(),
    }

    # Summary
    print_section("TEST SUMMARY")

    passed = sum(results.values())
    total = len(results)

    for test_name, result in results.items():
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status} - {test_name}")

    print(f"\nResults: {passed}/{total} tests passed")

    if passed == total:
        print("\n🎉 All tests passed! Backend is ready.")
        print("\nNext steps:")
        print("  1. Start the API: cd neuromap/backend/api && uvicorn app:app --reload")
        print("  2. Test endpoints at: http://localhost:8000/docs")
        print("  3. Integrate with Shiny frontend")
    else:
        print(f"\n⚠ {total - passed} test(s) failed. Please review errors above.")

    return passed == total


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
