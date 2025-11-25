"""
Quick test script for NeuroChron without Docker.
Uses existing subject 002 data - completes in seconds!
"""

import requests
import time

API_URL = "http://localhost:8000"

def test_quick_prediction():
    """Test brain age prediction with existing subject 002."""

    print("\n" + "="*60)
    print("  QUICK TEST - Brain Age Prediction")
    print("  (Using existing subject 002 - no Docker needed)")
    print("="*60 + "\n")

    # Test data
    test_data = {
        "chronological_age": 45,
        "email": "test@example.com",  # Change to your email to receive notification
        "subject_id": "002"
    }

    print(f"Test Parameters:")
    print(f"  Chronological Age: {test_data['chronological_age']} years")
    print(f"  Email: {test_data['email']}")
    print(f"  Subject: {test_data['subject_id']}")
    print()

    try:
        # Check API health
        print("1. Checking API health...")
        health_response = requests.get(f"{API_URL}/health")
        health = health_response.json()

        if health.get('status') == 'healthy':
            print("   ✓ API is healthy")
        else:
            print(f"   ✗ API unhealthy: {health}")
            return

        # Call test prediction endpoint
        print("\n2. Running brain age prediction...")
        print("   (This should take 5-10 seconds)")

        start_time = time.time()

        response = requests.post(
            f"{API_URL}/api/test/predict",
            data=test_data,
            timeout=30
        )

        elapsed = time.time() - start_time

        if response.status_code == 200:
            result = response.json()

            print(f"   ✓ Prediction completed in {elapsed:.1f} seconds\n")

            # Display results
            print("="*60)
            print("  RESULTS")
            print("="*60)
            print(f"Job ID:            {result['job_id'][:16]}...")
            print(f"Subject ID:        {result['subject_id']}")
            print(f"Status:            {result['status']}")
            print()
            print(f"Predicted Age:     {result['predicted_age']:.2f} years")
            print(f"Chronological Age: {test_data['chronological_age']} years")
            print(f"Brain Age Gap:     {result['brain_age_gap']:+.2f} years")
            print()

            if result['brain_age_gap'] > 0:
                print(f"→ Brain appears {abs(result['brain_age_gap']):.1f} years OLDER")
            elif result['brain_age_gap'] < 0:
                print(f"→ Brain appears {abs(result['brain_age_gap']):.1f} years YOUNGER")
            else:
                print("→ Brain age matches chronological age")

            print("="*60)
            print()

            # Check if job exists in database
            print("3. Verifying job in database...")
            job_response = requests.get(f"{API_URL}/api/jobs/{result['job_id']}/results")
            if job_response.status_code == 200:
                print("   ✓ Job saved to database")
            else:
                print("   ✗ Job not found in database")

            print("\n4. Checking email notification...")
            print(f"   Email should be sent to: {test_data['email']}")
            print("   (Check your inbox if using a real email)")

            print("\n✓ TEST COMPLETED SUCCESSFULLY!")
            print("\nYou can now:")
            print("  - Check http://localhost:8000/api/jobs to see all jobs")
            print("  - Visit http://localhost:8080 to test the Shiny frontend")

        else:
            print(f"   ✗ Request failed: {response.status_code}")
            print(f"   Error: {response.text}")

    except requests.exceptions.ConnectionError:
        print("\n✗ ERROR: Cannot connect to API")
        print("Make sure the API is running:")
        print("  cd /Users/gersonestrada/Desktop/neuromap/neuromap/backend/api")
        print("  uvicorn app:app --reload --port 8000")

    except Exception as e:
        print(f"\n✗ ERROR: {type(e).__name__}: {e}")


if __name__ == "__main__":
    test_quick_prediction()
