"""
Test full pipeline with Docker and FreeSurfer.
WARNING: This will take ~3.5 hours to complete!
"""

import requests
import time
from pathlib import Path

API_URL = "http://localhost:8000"

def test_full_pipeline():
    """Test complete pipeline with FreeSurfer preprocessing."""

    print("\n" + "="*70)
    print("  FULL PIPELINE TEST (with FreeSurfer)")
    print("  WARNING: This will take approximately 3.5 hours!")
    print("="*70 + "\n")

    # Test data
    test_file = Path("/Users/gersonestrada/Desktop/neuromap/neuromap/backend/input/001.nii")

    if not test_file.exists():
        print(f"✗ Test file not found: {test_file}")
        print("Please ensure 001.nii exists in the input directory")
        return

    test_data = {
        "chronological_age": 45,
        "email": "gdestrad@usc.edu",  # Your email
    }

    print(f"Test Parameters:")
    print(f"  File: {test_file.name}")
    print(f"  Chronological Age: {test_data['chronological_age']} years")
    print(f"  Email: {test_data['email']}")
    print()

    try:
        # Check API health
        print("1. Checking API health...")
        health_response = requests.get(f"{API_URL}/health", timeout=5)
        health = health_response.json()

        if health.get('status') != 'healthy':
            print(f"   ✗ API unhealthy: {health}")
            return

        print("   ✓ API is healthy")

        # Upload file (convert to "DICOM" even though it's NIfTI for testing)
        print("\n2. Uploading file to API...")

        with open(test_file, 'rb') as f:
            files = {'file': (f'{test_file.name}.dcm', f, 'application/dicom')}
            data = test_data

            response = requests.post(
                f"{API_URL}/api/upload",
                files=files,
                data=data,
                timeout=30
            )

        if response.status_code != 200:
            print(f"   ✗ Upload failed: {response.status_code}")
            print(f"   Error: {response.text}")
            return

        upload_result = response.json()
        job_id = upload_result['job_id']

        print(f"   ✓ File uploaded successfully")
        print(f"   Job ID: {job_id}")
        print(f"   Subject ID: {upload_result['subject_id']}")

        # Start processing
        print("\n3. Starting FreeSurfer processing...")
        print("   ⏱  This will take approximately 3.5 hours")
        print("   You can close this script and check status later")
        print()

        process_response = requests.post(
            f"{API_URL}/api/jobs/{job_id}/process",
            timeout=10
        )

        if process_response.status_code != 200:
            print(f"   ✗ Failed to start processing: {process_response.text}")
            return

        print("   ✓ Processing started!")
        print()
        print("="*70)
        print("  MONITORING STATUS")
        print("="*70)
        print()

        # Poll for status
        start_time = time.time()
        last_status = None
        poll_count = 0

        while True:
            poll_count += 1
            elapsed = time.time() - start_time

            # Get status
            status_response = requests.get(
                f"{API_URL}/api/jobs/{job_id}/status",
                timeout=10
            )

            if status_response.status_code != 200:
                print(f"   ✗ Failed to get status: {status_response.text}")
                time.sleep(30)
                continue

            status_data = status_response.json()
            current_status = status_data['status']
            progress_msg = status_data.get('progress_message', '')

            # Print status update if changed
            if current_status != last_status:
                print(f"[{time.strftime('%H:%M:%S')}] Status: {current_status}")
                print(f"              {progress_msg}")
                last_status = current_status

            # Check if completed
            if current_status == 'completed':
                print()
                print("="*70)
                print("  ✓ PROCESSING COMPLETE!")
                print("="*70)

                # Get results
                results_response = requests.get(
                    f"{API_URL}/api/jobs/{job_id}/results",
                    timeout=10
                )

                if results_response.status_code == 200:
                    results = results_response.json()
                    result_data = results.get('result')

                    if result_data:
                        print()
                        print(f"Predicted Brain Age:  {result_data['predicted_age']:.2f} years")
                        print(f"Chronological Age:    {result_data['chronological_age']} years")
                        print(f"Brain Age Gap:        {result_data['brain_age_gap']:+.2f} years")
                        print()
                        print(f"Interpretation: {result_data['interpretation']}")
                        print()

                elapsed_hours = elapsed / 3600
                print(f"Total time: {elapsed_hours:.2f} hours")
                print()
                print(f"Email sent to: {test_data['email']}")
                print("="*70)
                break

            # Check if failed
            if current_status == 'failed':
                error = status_data.get('error_message', 'Unknown error')
                print()
                print("="*70)
                print("  ✗ PROCESSING FAILED")
                print("="*70)
                print(f"Error: {error}")
                print("="*70)
                break

            # Print progress indicator every 10 polls (~5 minutes)
            if poll_count % 10 == 0:
                elapsed_mins = elapsed / 60
                print(f"[{time.strftime('%H:%M:%S')}] Still processing... ({elapsed_mins:.0f} minutes elapsed)")

            # Wait 30 seconds before next poll
            time.sleep(30)

    except KeyboardInterrupt:
        print("\n\nInterrupted by user.")
        print(f"Job ID: {job_id}")
        print("You can check status later with:")
        print(f"  curl http://localhost:8000/api/jobs/{job_id}/status")

    except Exception as e:
        print(f"\n✗ Error: {type(e).__name__}: {e}")


if __name__ == "__main__":
    print("\n⚠️  WARNING: This test will take ~3.5 hours to complete!")
    print("Make sure:")
    print("  1. Docker Desktop is running")
    print("  2. API server is running (uvicorn app:app)")
    print("  3. FreeSurfer license is in backend/license/license.txt")
    print()

    response = input("Continue? (yes/no): ")

    if response.lower() in ['yes', 'y']:
        test_full_pipeline()
    else:
        print("Test cancelled.")
