"""
Database module for NeuroChron brain age analysis jobs.
Uses SQLAlchemy with SQLite for persistence.
"""

from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime, timezone
from pathlib import Path

# Database setup
DB_DIR = Path(__file__).parent / "data"
DB_DIR.mkdir(exist_ok=True)
DB_PATH = DB_DIR / "neuromap.db"
DATABASE_URL = f"sqlite:///{DB_PATH}"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


# Database Models
class Job(Base):
    """
    Represents a brain age analysis job.

    Tracks the lifecycle of an MRI processing job from upload through completion.
    """
    __tablename__ = "jobs"

    id = Column(String, primary_key=True, index=True)  # UUID
    status = Column(String, nullable=False, index=True)  # pending, processing, completed, failed
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    completed_at = Column(DateTime, nullable=True)
    error_message = Column(String, nullable=True)

    # File tracking
    file_path = Column(String, nullable=False)  # Path to uploaded DICOM
    nifti_path = Column(String, nullable=True)  # Path to converted NIfTI
    subject_id = Column(String, nullable=False, unique=True)  # FreeSurfer subject ID

    # User input
    chronological_age = Column(Integer, nullable=False)
    email = Column(String, nullable=False)

    # Relationship
    result = relationship("Result", back_populates="job", uselist=False, cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Job(id={self.id}, status={self.status}, subject_id={self.subject_id})>"


class Result(Base):
    """
    Stores brain age prediction results for a completed job.
    """
    __tablename__ = "results"

    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(String, ForeignKey("jobs.id"), nullable=False, unique=True)

    # Prediction outputs
    predicted_age = Column(Float, nullable=False)
    brain_age_gap = Column(Float, nullable=False)  # predicted - chronological

    # Timestamp
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))

    # Relationship
    job = relationship("Job", back_populates="result")

    def __repr__(self):
        return f"<Result(job_id={self.job_id}, predicted_age={self.predicted_age:.1f}, gap={self.brain_age_gap:.1f})>"


# Database initialization
def init_db():
    """
    Create all tables in the database.
    Should be called on application startup.
    """
    Base.metadata.create_all(bind=engine)
    print(f"Database initialized at {DB_PATH}")


def get_db():
    """
    Dependency for FastAPI to get database sessions.

    Usage:
        @app.get("/jobs/{job_id}")
        def get_job(job_id: str, db: Session = Depends(get_db)):
            return db.query(Job).filter(Job.id == job_id).first()
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Helper functions for common database operations
def create_job(db, job_id: str, subject_id: str, file_path: str,
               chronological_age: int, email: str) -> Job:
    """
    Create a new job record in pending status.
    """
    job = Job(
        id=job_id,
        subject_id=subject_id,
        status="pending",
        file_path=file_path,
        chronological_age=chronological_age,
        email=email,
        created_at=datetime.now(timezone.utc)
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


def get_job_by_id(db, job_id: str) -> Job:
    """
    Retrieve a job by its ID.
    """
    return db.query(Job).filter(Job.id == job_id).first()


def update_job_status(db, job_id: str, status: str, error_message: str = None):
    """
    Update the status of a job.
    If status is 'completed' or 'failed', set completed_at timestamp.
    """
    job = db.query(Job).filter(Job.id == job_id).first()
    if job:
        job.status = status
        if error_message:
            job.error_message = error_message
        if status in ["completed", "failed"]:
            job.completed_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(job)
    return job


def update_job_nifti_path(db, job_id: str, nifti_path: str):
    """
    Update the NIfTI file path after DICOM conversion.
    """
    job = db.query(Job).filter(Job.id == job_id).first()
    if job:
        job.nifti_path = nifti_path
        db.commit()
        db.refresh(job)
    return job


def create_result(db, job_id: str, predicted_age: float, chronological_age: int) -> Result:
    """
    Create a result record for a completed job.
    Automatically calculates brain age gap.
    """
    brain_age_gap = predicted_age - chronological_age
    result = Result(
        job_id=job_id,
        predicted_age=predicted_age,
        brain_age_gap=brain_age_gap,
        created_at=datetime.now(timezone.utc)
    )
    db.add(result)
    db.commit()
    db.refresh(result)
    return result


def get_result_by_job_id(db, job_id: str) -> Result:
    """
    Retrieve prediction results for a job.
    """
    return db.query(Result).filter(Result.job_id == job_id).first()


def get_all_jobs(db, limit: int = 100):
    """
    Retrieve all jobs, most recent first.
    """
    return db.query(Job).order_by(Job.created_at.desc()).limit(limit).all()


def get_jobs_by_status(db, status: str, limit: int = 100):
    """
    Retrieve jobs filtered by status.
    """
    return db.query(Job).filter(Job.status == status).order_by(Job.created_at.desc()).limit(limit).all()


# Initialize database on module import
if __name__ == "__main__":
    init_db()
    print("Database tables created successfully!")
