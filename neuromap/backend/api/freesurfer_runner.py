"""
FreeSurfer Docker wrapper for MRI preprocessing.
Handles FreeSurfer recon-all execution via docker-compose.
"""

import subprocess
import time
from pathlib import Path
from typing import Optional, Tuple


# Paths
BACKEND_DIR = Path(__file__).parent.parent
DOCKER_COMPOSE_FILE = BACKEND_DIR / "docker-compose.yml"
SUBJECTS_DIR = BACKEND_DIR / "subjects"
INPUT_DIR = BACKEND_DIR / "input"


class FreeSurferError(Exception):
    """Custom exception for FreeSurfer processing errors."""
    pass


def check_docker_compose():
    """
    Check if docker-compose is available.

    Raises:
        FreeSurferError: If docker-compose is not installed
    """
    try:
        result = subprocess.run(
            ["docker", "compose", "version"],
            capture_output=True,
            text=True,
            check=False
        )
        if result.returncode != 0:
            raise FreeSurferError("docker-compose is not available. Please install Docker.")
        print(f"Docker Compose version: {result.stdout.strip()}")
        return True
    except FileNotFoundError:
        raise FreeSurferError("docker command not found. Please install Docker.")


def check_freesurfer_license() -> bool:
    """
    Check if FreeSurfer license file exists.

    Returns:
        bool: True if license exists

    Raises:
        FreeSurferError: If license file is missing
    """
    license_file = BACKEND_DIR / "license" / "license.txt"

    if not license_file.exists():
        raise FreeSurferError(
            f"FreeSurfer license file not found at {license_file}. "
            "Please obtain a FreeSurfer license from https://surfer.nmr.mgh.harvard.edu/registration.html"
        )

    print(f"FreeSurfer license found: {license_file}")
    return True


def check_input_file(subject_id: str) -> Path:
    """
    Check if input NIfTI file exists for the subject.

    Args:
        subject_id: Subject identifier

    Returns:
        Path: Path to the input NIfTI file

    Raises:
        FreeSurferError: If input file not found
    """
    nifti_file = INPUT_DIR / f"{subject_id}.nii"

    if not nifti_file.exists():
        raise FreeSurferError(f"Input file not found: {nifti_file}")

    print(f"Input file found: {nifti_file} ({nifti_file.stat().st_size / (1024*1024):.2f} MB)")
    return nifti_file


def run_freesurfer(subject_id: str, timeout: Optional[int] = None) -> Tuple[Path, float]:
    """
    Run FreeSurfer recon-all processing on a subject.

    This executes the full FreeSurfer pipeline (recon-all -all) which includes:
    1. Motion correction and averaging
    2. Intensity normalization
    3. Skull stripping
    4. Talairach transformation
    5. Subcortical segmentation
    6. Cortical surface reconstruction
    7. Parcellation and labeling

    Expected runtime: ~3.5 hours

    Args:
        subject_id: Subject identifier (must match filename in input/)
        timeout: Optional timeout in seconds (default: None = no timeout)

    Returns:
        Tuple[Path, float]: (path to brain.mgz, elapsed time in seconds)

    Raises:
        FreeSurferError: If processing fails
    """

    # Validate prerequisites
    check_docker_compose()
    check_freesurfer_license()
    input_file = check_input_file(subject_id)

    print(f"\n{'='*60}")
    print(f"Starting FreeSurfer recon-all for subject: {subject_id}")
    print(f"Input file: {input_file.name}")
    print(f"Expected runtime: ~3.5 hours")
    print(f"{'='*60}\n")

    # Build docker-compose command
    cmd = [
        "docker", "compose",
        "-f", str(DOCKER_COMPOSE_FILE),
        "run", "--rm",
        "freesurfer",
        "recon-all",
        "-i", f"/input/{subject_id}.nii",  # Path inside container
        "-s", subject_id,
        "-all"  # Run full pipeline (autorecon1, 2, 3)
    ]

    print(f"Command: {' '.join(cmd)}\n")

    # Execute command
    start_time = time.time()

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True,
            timeout=timeout,
            cwd=BACKEND_DIR  # Run from backend directory
        )

        elapsed_time = time.time() - start_time

        print(f"\n{'='*60}")
        print(f"FreeSurfer completed successfully!")
        print(f"Elapsed time: {format_time(elapsed_time)}")
        print(f"{'='*60}\n")

        # Verify output
        brain_mgz = SUBJECTS_DIR / subject_id / "mri" / "brain.mgz"

        if not brain_mgz.exists():
            raise FreeSurferError(
                f"FreeSurfer completed but brain.mgz not found at {brain_mgz}. "
                "This may indicate an incomplete reconstruction."
            )

        print(f"Output file: {brain_mgz} ({brain_mgz.stat().st_size / (1024*1024):.2f} MB)")

        return brain_mgz, elapsed_time

    except subprocess.TimeoutExpired:
        elapsed_time = time.time() - start_time
        raise FreeSurferError(
            f"FreeSurfer processing timed out after {format_time(elapsed_time)}. "
            f"Timeout was set to {timeout} seconds."
        )

    except subprocess.CalledProcessError as e:
        elapsed_time = time.time() - start_time
        error_msg = f"FreeSurfer failed after {format_time(elapsed_time)}\n"
        error_msg += f"Return code: {e.returncode}\n"

        if e.stderr:
            error_msg += f"Error output:\n{e.stderr[-1000:]}"  # Last 1000 chars

        raise FreeSurferError(error_msg)

    except Exception as e:
        elapsed_time = time.time() - start_time
        raise FreeSurferError(
            f"Unexpected error after {format_time(elapsed_time)}: {str(e)}"
        )


def format_time(seconds: float) -> str:
    """
    Format elapsed time in HH:MM:SS.mmm format.

    Args:
        seconds: Time in seconds

    Returns:
        str: Formatted time string
    """
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = seconds % 60
    return f"{hours:02d}:{minutes:02d}:{secs:06.3f}"


def check_freesurfer_output(subject_id: str) -> dict:
    """
    Check what FreeSurfer outputs exist for a subject.

    Args:
        subject_id: Subject identifier

    Returns:
        dict: Dictionary of output files and their status
    """
    subject_dir = SUBJECTS_DIR / subject_id

    if not subject_dir.exists():
        return {"exists": False, "subject_dir": str(subject_dir)}

    # Key files to check
    key_files = {
        "brain.mgz": subject_dir / "mri" / "brain.mgz",
        "orig.mgz": subject_dir / "mri" / "orig.mgz",
        "T1.mgz": subject_dir / "mri" / "T1.mgz",
        "lh.white": subject_dir / "surf" / "lh.white",
        "rh.white": subject_dir / "surf" / "rh.white",
        "lh.pial": subject_dir / "surf" / "lh.pial",
        "rh.pial": subject_dir / "surf" / "rh.pial",
    }

    status = {
        "exists": True,
        "subject_dir": str(subject_dir),
        "files": {}
    }

    for name, path in key_files.items():
        status["files"][name] = {
            "exists": path.exists(),
            "path": str(path),
            "size_mb": path.stat().st_size / (1024*1024) if path.exists() else 0
        }

    return status


def cleanup_freesurfer_output(subject_id: str):
    """
    Clean up FreeSurfer output directory for a subject.

    WARNING: This permanently deletes the FreeSurfer output.

    Args:
        subject_id: Subject identifier
    """
    import shutil

    subject_dir = SUBJECTS_DIR / subject_id

    if subject_dir.exists():
        shutil.rmtree(subject_dir)
        print(f"Removed FreeSurfer output: {subject_dir}")
    else:
        print(f"No FreeSurfer output found for {subject_id}")


# Example usage
if __name__ == "__main__":
    # Test with existing subject
    test_subject = "002"

    print("Checking FreeSurfer environment...")
    try:
        check_docker_compose()
        check_freesurfer_license()
        print("✓ FreeSurfer environment OK\n")

        # Check existing output
        status = check_freesurfer_output(test_subject)
        print(f"Subject {test_subject} status:")
        print(f"  Exists: {status['exists']}")
        if status['exists']:
            print(f"  Directory: {status['subject_dir']}")
            print("  Files:")
            for name, info in status['files'].items():
                exists_str = "✓" if info['exists'] else "✗"
                size_str = f"({info['size_mb']:.2f} MB)" if info['exists'] else ""
                print(f"    {exists_str} {name} {size_str}")

    except FreeSurferError as e:
        print(f"✗ Error: {e}")
