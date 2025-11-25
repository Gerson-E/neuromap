"""
File processing module for DICOM to NIfTI conversion.
Handles uploaded MRI files and prepares them for FreeSurfer processing.
"""

import os
import shutil
from pathlib import Path
from typing import Tuple
import pydicom
import nibabel as nib
import numpy as np
from datetime import datetime


# Directory configuration
BACKEND_DIR = Path(__file__).parent.parent
INPUT_DIR = BACKEND_DIR / "input"
UPLOAD_DIR = BACKEND_DIR / "api" / "uploads"

# Ensure directories exist
INPUT_DIR.mkdir(exist_ok=True)
UPLOAD_DIR.mkdir(exist_ok=True)


class FileProcessingError(Exception):
    """Custom exception for file processing errors."""
    pass


def generate_subject_id() -> str:
    """
    Generate a unique subject ID for FreeSurfer processing.

    Returns:
        str: Subject ID in format 'subj_YYYYMMDD_HHMMSS'
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"subj_{timestamp}"


def validate_dicom_file(file_path: Path) -> bool:
    """
    Validate that the uploaded file is a valid DICOM file.

    Args:
        file_path: Path to the file to validate

    Returns:
        bool: True if valid DICOM file

    Raises:
        FileProcessingError: If file is not a valid DICOM
    """
    try:
        # Try to read as DICOM
        dcm = pydicom.dcmread(file_path, force=True)

        # Check for essential DICOM attributes
        if not hasattr(dcm, 'pixel_array'):
            raise FileProcessingError("DICOM file does not contain pixel data")

        # Check if it's an MRI image (optional but recommended)
        if hasattr(dcm, 'Modality') and dcm.Modality not in ['MR', 'MRI']:
            raise FileProcessingError(f"File modality is {dcm.Modality}, expected MR/MRI")

        return True

    except pydicom.errors.InvalidDicomError as e:
        raise FileProcessingError(f"Invalid DICOM file: {str(e)}")
    except Exception as e:
        raise FileProcessingError(f"Error reading DICOM file: {str(e)}")


def dicom_to_nifti(dicom_path: Path, output_path: Path) -> Path:
    """
    Convert a DICOM file to NIfTI format.

    Args:
        dicom_path: Path to input DICOM file
        output_path: Path for output NIfTI file

    Returns:
        Path: Path to the created NIfTI file

    Raises:
        FileProcessingError: If conversion fails
    """
    try:
        # Read DICOM file
        dcm = pydicom.dcmread(dicom_path)

        # Extract pixel data
        pixel_array = dcm.pixel_array

        # Handle different data types and orientations
        if len(pixel_array.shape) == 2:
            # Single slice - add dimension
            pixel_array = np.expand_dims(pixel_array, axis=2)

        # Create NIfTI image
        # Note: This is a simplified conversion. For production, you might need:
        # - Proper affine matrix from DICOM orientation
        # - Handling of multi-frame DICOM
        # - Rescale slope/intercept application
        nifti_img = nib.Nifti1Image(pixel_array.astype(np.float32), affine=np.eye(4))

        # Save as NIfTI
        nib.save(nifti_img, output_path)

        print(f"Successfully converted DICOM to NIfTI: {output_path}")
        return output_path

    except Exception as e:
        raise FileProcessingError(f"Failed to convert DICOM to NIfTI: {str(e)}")


def process_uploaded_file(uploaded_file_path: str, job_id: str, subject_id: str) -> Tuple[Path, Path]:
    """
    Process an uploaded DICOM file: validate, convert to NIfTI, and save.

    Args:
        uploaded_file_path: Path to the uploaded DICOM file
        job_id: Unique job identifier
        subject_id: FreeSurfer subject identifier

    Returns:
        Tuple[Path, Path]: (original_file_path, nifti_file_path)

    Raises:
        FileProcessingError: If processing fails at any stage
    """
    uploaded_path = Path(uploaded_file_path)

    # Validate input file exists
    if not uploaded_path.exists():
        raise FileProcessingError(f"Uploaded file not found: {uploaded_file_path}")

    # Step 1: Validate DICOM
    print(f"Validating DICOM file: {uploaded_path.name}")
    validate_dicom_file(uploaded_path)

    # Step 2: Copy original file to uploads directory with job_id
    original_file = UPLOAD_DIR / f"{job_id}.dcm"
    shutil.copy2(uploaded_path, original_file)
    print(f"Saved original file: {original_file}")

    # Step 3: Convert to NIfTI
    nifti_file = INPUT_DIR / f"{subject_id}.nii"
    print(f"Converting to NIfTI: {nifti_file.name}")
    dicom_to_nifti(uploaded_path, nifti_file)

    # Step 4: Validate NIfTI was created successfully
    if not nifti_file.exists():
        raise FileProcessingError("NIfTI file was not created successfully")

    # Check file size
    nifti_size_mb = nifti_file.stat().st_size / (1024 * 1024)
    print(f"Created NIfTI file: {nifti_file.name} ({nifti_size_mb:.2f} MB)")

    if nifti_size_mb < 0.1:
        raise FileProcessingError("NIfTI file is suspiciously small (< 0.1 MB)")

    return original_file, nifti_file


def save_uploaded_file(file_content: bytes, filename: str) -> Path:
    """
    Save uploaded file content to temporary location.

    Args:
        file_content: File content as bytes
        filename: Original filename

    Returns:
        Path: Path to saved file
    """
    # Create temporary file path
    temp_path = UPLOAD_DIR / f"temp_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{filename}"

    # Write file
    with open(temp_path, 'wb') as f:
        f.write(file_content)

    return temp_path


def cleanup_job_files(job_id: str, subject_id: str):
    """
    Clean up temporary files for a completed or failed job.

    Args:
        job_id: Job identifier
        subject_id: Subject identifier
    """
    # Remove uploaded DICOM
    dicom_file = UPLOAD_DIR / f"{job_id}.dcm"
    if dicom_file.exists():
        dicom_file.unlink()
        print(f"Cleaned up: {dicom_file}")

    # Remove NIfTI input (optional - keep for debugging)
    # nifti_file = INPUT_DIR / f"{subject_id}.nii"
    # if nifti_file.exists():
    #     nifti_file.unlink()
    #     print(f"Cleaned up: {nifti_file}")


def get_dicom_metadata(dicom_path: Path) -> dict:
    """
    Extract useful metadata from DICOM file for logging/debugging.

    Args:
        dicom_path: Path to DICOM file

    Returns:
        dict: Dictionary of metadata
    """
    try:
        dcm = pydicom.dcmread(dicom_path)

        metadata = {
            "patient_id": getattr(dcm, 'PatientID', 'Unknown'),
            "study_date": getattr(dcm, 'StudyDate', 'Unknown'),
            "modality": getattr(dcm, 'Modality', 'Unknown'),
            "manufacturer": getattr(dcm, 'Manufacturer', 'Unknown'),
            "image_shape": dcm.pixel_array.shape if hasattr(dcm, 'pixel_array') else None,
        }

        return metadata

    except Exception as e:
        return {"error": str(e)}


# Example usage
if __name__ == "__main__":
    # Test with sample file
    sample_dicom = "/Users/gersonestrada/Desktop/neuromap/neuromap/backend/input/001.nii"

    if Path(sample_dicom).exists():
        print(f"Testing file processor with: {sample_dicom}")

        job_id = "test_job_123"
        subject_id = generate_subject_id()

        print(f"Generated subject ID: {subject_id}")

        # Note: This example assumes the file is already NIfTI, not DICOM
        # For actual testing, you would need a real DICOM file
    else:
        print("Sample file not found. Please provide a DICOM file for testing.")
