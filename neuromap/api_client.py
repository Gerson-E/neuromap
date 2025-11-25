"""
API Client for NeuroChron Shiny Application.
Provides Python functions to interact with the FastAPI backend.
"""

import requests
from typing import Optional, Dict, Any
import time


# API Configuration
API_BASE_URL = "http://localhost:8000"  # Change to production URL when deployed


class APIError(Exception):
    """Custom exception for API errors."""
    pass


def check_api_health() -> Dict[str, Any]:
    """
    Check if the API server is running and healthy.

    Returns:
        dict: Health status response

    Raises:
        APIError: If API is not reachable
    """
    try:
        response = requests.get(f"{API_BASE_URL}/health", timeout=5)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        raise APIError(f"API health check failed: {str(e)}")


def upload_file(
    file_path: str,
    chronological_age: int,
    email: str
) -> Dict[str, Any]:
    """
    Upload a DICOM file and create a new processing job.

    Args:
        file_path: Path to the DICOM file
        chronological_age: Patient's chronological age (must be > 21)
        email: Email address for notifications

    Returns:
        dict: Job creation response with job_id

    Raises:
        APIError: If upload fails
    """
    try:
        # Open the file
        with open(file_path, 'rb') as f:
            files = {'file': (file_path.split('/')[-1], f, 'application/dicom')}
            data = {
                'chronological_age': chronological_age,
                'email': email
            }

            # Upload to API
            response = requests.post(
                f"{API_BASE_URL}/api/upload",
                files=files,
                data=data,
                timeout=30
            )

        response.raise_for_status()
        return response.json()

    except requests.exceptions.RequestException as e:
        raise APIError(f"File upload failed: {str(e)}")
    except FileNotFoundError:
        raise APIError(f"File not found: {file_path}")


def start_processing(job_id: str) -> Dict[str, Any]:
    """
    Start processing a job (FreeSurfer + brain age prediction).

    Args:
        job_id: Job identifier

    Returns:
        dict: Processing status response

    Raises:
        APIError: If request fails
    """
    try:
        response = requests.post(
            f"{API_BASE_URL}/api/jobs/{job_id}/process",
            timeout=10
        )
        response.raise_for_status()
        return response.json()

    except requests.exceptions.RequestException as e:
        raise APIError(f"Failed to start processing: {str(e)}")


def get_job_status(job_id: str) -> Dict[str, Any]:
    """
    Get the current status of a processing job.

    Args:
        job_id: Job identifier

    Returns:
        dict: Job status response with status field

    Raises:
        APIError: If request fails
    """
    try:
        response = requests.get(
            f"{API_BASE_URL}/api/jobs/{job_id}/status",
            timeout=10
        )
        response.raise_for_status()
        return response.json()

    except requests.exceptions.RequestException as e:
        raise APIError(f"Failed to get job status: {str(e)}")


def get_job_results(job_id: str) -> Dict[str, Any]:
    """
    Get the prediction results for a completed job.

    Args:
        job_id: Job identifier

    Returns:
        dict: Results response with predicted age and brain age gap

    Raises:
        APIError: If request fails or job not complete
    """
    try:
        response = requests.get(
            f"{API_BASE_URL}/api/jobs/{job_id}/results",
            timeout=10
        )
        response.raise_for_status()
        return response.json()

    except requests.exceptions.RequestException as e:
        raise APIError(f"Failed to get results: {str(e)}")


def list_jobs(status: Optional[str] = None, limit: int = 100) -> list:
    """
    List all jobs, optionally filtered by status.

    Args:
        status: Filter by status (pending, processing, completed, failed)
        limit: Maximum number of jobs to return

    Returns:
        list: List of job status dictionaries

    Raises:
        APIError: If request fails
    """
    try:
        params = {'limit': limit}
        if status:
            params['status'] = status

        response = requests.get(
            f"{API_BASE_URL}/api/jobs",
            params=params,
            timeout=10
        )
        response.raise_for_status()
        return response.json()

    except requests.exceptions.RequestException as e:
        raise APIError(f"Failed to list jobs: {str(e)}")


def delete_job(job_id: str) -> Dict[str, Any]:
    """
    Delete a job and its associated files.

    Args:
        job_id: Job identifier

    Returns:
        dict: Deletion confirmation

    Raises:
        APIError: If request fails
    """
    try:
        response = requests.delete(
            f"{API_BASE_URL}/api/jobs/{job_id}",
            timeout=10
        )
        response.raise_for_status()
        return response.json()

    except requests.exceptions.RequestException as e:
        raise APIError(f"Failed to delete job: {str(e)}")


def upload_and_process(
    file_path: str,
    chronological_age: int,
    email: str
) -> Dict[str, Any]:
    """
    Convenience function: Upload file and immediately start processing.

    Args:
        file_path: Path to the DICOM file
        chronological_age: Patient's chronological age (must be > 21)
        email: Email address for notifications

    Returns:
        dict: Job information with job_id and status

    Raises:
        APIError: If any step fails
    """
    # Step 1: Upload file
    upload_response = upload_file(file_path, chronological_age, email)
    job_id = upload_response['job_id']

    # Step 2: Start processing
    process_response = start_processing(job_id)

    return {
        'job_id': job_id,
        'subject_id': upload_response['subject_id'],
        'status': process_response['status'],
        'message': process_response['message']
    }


def poll_until_complete(
    job_id: str,
    poll_interval: int = 30,
    max_wait: int = 14400,  # 4 hours default
    callback = None
) -> Dict[str, Any]:
    """
    Poll job status until completion or failure.

    Args:
        job_id: Job identifier
        poll_interval: Seconds between status checks (default 30)
        max_wait: Maximum seconds to wait (default 4 hours)
        callback: Optional function to call with status updates

    Returns:
        dict: Final job results

    Raises:
        APIError: If job fails or timeout occurs
    """
    start_time = time.time()

    while True:
        # Check if max wait time exceeded
        elapsed = time.time() - start_time
        if elapsed > max_wait:
            raise APIError(f"Timeout: Job did not complete within {max_wait} seconds")

        # Get current status
        status_response = get_job_status(job_id)
        status = status_response['status']

        # Call callback if provided
        if callback:
            callback(status_response)

        # Check if completed
        if status == 'completed':
            return get_job_results(job_id)

        # Check if failed
        if status == 'failed':
            error = status_response.get('error_message', 'Unknown error')
            raise APIError(f"Job failed: {error}")

        # Wait before next poll
        time.sleep(poll_interval)


# Example usage for testing
if __name__ == "__main__":
    print("Testing API Client...")

    try:
        # Check API health
        health = check_api_health()
        print(f"✓ API Health: {health['status']}")

        # List jobs
        jobs = list_jobs()
        print(f"✓ Found {len(jobs)} jobs")

        print("\nAPI Client is working correctly!")

    except APIError as e:
        print(f"✗ API Error: {e}")
    except Exception as e:
        print(f"✗ Unexpected Error: {e}")
