"""
Pydantic models for API request/response validation.
"""

from pydantic import BaseModel, EmailStr, Field, field_validator
from typing import Optional
from datetime import datetime
from enum import Enum


class JobStatus(str, Enum):
    """Enum for job status values."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


# Request Models
class JobCreate(BaseModel):
    """Request model for creating a new brain age analysis job."""
    chronological_age: int = Field(..., ge=22, le=120, description="Patient's chronological age (must be > 21)")
    email: EmailStr = Field(..., description="Email address for result notifications")

    @field_validator('chronological_age')
    @classmethod
    def validate_age(cls, v):
        if v < 22:
            raise ValueError("Brain age prediction is only valid for individuals older than 21 years")
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "chronological_age": 45,
                "email": "user@example.com"
            }
        }


# Response Models
class JobResponse(BaseModel):
    """Response model for job creation."""
    job_id: str = Field(..., description="Unique job identifier")
    subject_id: str = Field(..., description="FreeSurfer subject identifier")
    status: JobStatus = Field(..., description="Current job status")
    created_at: datetime = Field(..., description="Job creation timestamp")
    message: str = Field(..., description="Human-readable status message")

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "job_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
                "subject_id": "subj_20250125_143022",
                "status": "pending",
                "created_at": "2025-01-25T14:30:22.123456Z",
                "message": "Job created successfully. Processing will begin shortly."
            }
        }


class JobStatusResponse(BaseModel):
    """Response model for job status queries."""
    job_id: str
    status: JobStatus
    created_at: datetime
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    chronological_age: int
    progress_message: str = Field(..., description="Human-readable progress message")

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "job_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
                "status": "processing",
                "created_at": "2025-01-25T14:30:22.123456Z",
                "completed_at": None,
                "error_message": None,
                "chronological_age": 45,
                "progress_message": "Running FreeSurfer preprocessing (estimated 3.5 hours)"
            }
        }


class ResultData(BaseModel):
    """Brain age prediction result data."""
    predicted_age: float = Field(..., description="Predicted biological brain age in years")
    chronological_age: int = Field(..., description="Patient's chronological age")
    brain_age_gap: float = Field(..., description="Brain age gap (predicted - chronological)")
    interpretation: str = Field(..., description="Human-readable interpretation of results")
    saliency_map_available: bool = Field(default=False, description="Whether a saliency map is available")
    saliency_map_url: Optional[str] = Field(default=None, description="URL to retrieve saliency map visualization")

    class Config:
        json_schema_extra = {
            "example": {
                "predicted_age": 52.3,
                "chronological_age": 45,
                "brain_age_gap": 7.3,
                "interpretation": "Brain appears 7.3 years older than chronological age",
                "saliency_map_available": True,
                "saliency_map_url": "/api/jobs/a1b2c3d4-e5f6-7890-abcd-ef1234567890/saliency"
            }
        }


class JobResultResponse(BaseModel):
    """Response model for job results."""
    job_id: str
    status: JobStatus
    result: Optional[ResultData] = None
    error_message: Optional[str] = None
    completed_at: Optional[datetime] = None

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "job_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
                "status": "completed",
                "result": {
                    "predicted_age": 52.3,
                    "chronological_age": 45,
                    "brain_age_gap": 7.3,
                    "interpretation": "Brain appears 7.3 years older than chronological age",
                    "saliency_map_available": True,
                    "saliency_map_url": "/api/jobs/a1b2c3d4-e5f6-7890-abcd-ef1234567890/saliency"
                },
                "error_message": None,
                "completed_at": "2025-01-25T18:05:42.789012Z"
            }
        }


class ErrorResponse(BaseModel):
    """Response model for API errors."""
    error: str = Field(..., description="Error type")
    message: str = Field(..., description="Detailed error message")
    job_id: Optional[str] = None

    class Config:
        json_schema_extra = {
            "example": {
                "error": "ValidationError",
                "message": "Brain age prediction is only valid for individuals older than 21 years",
                "job_id": None
            }
        }


# Helper functions
def format_progress_message(status: str) -> str:
    """Generate human-readable progress messages based on job status."""
    messages = {
        "pending": "Job queued. Waiting to start processing.",
        "processing": "Running FreeSurfer preprocessing (estimated 3.5 hours remaining)",
        "completed": "Analysis complete. Results are ready.",
        "failed": "Job failed. Please check error message for details."
    }
    return messages.get(status, "Unknown status")


def format_interpretation(brain_age_gap: float) -> str:
    """Generate human-readable interpretation of brain age gap."""
    gap_abs = abs(brain_age_gap)

    if brain_age_gap > 0:
        return f"Brain appears {gap_abs:.1f} years older than chronological age"
    elif brain_age_gap < 0:
        return f"Brain appears {gap_abs:.1f} years younger than chronological age"
    else:
        return "Brain age matches chronological age"
