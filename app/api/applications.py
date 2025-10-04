from fastapi import (
    APIRouter, Depends, HTTPException, UploadFile, File, Form, BackgroundTasks
)
from sqlalchemy.orm import Session
from typing import List
import os, uuid
from datetime import datetime

from app.database import get_db, SessionLocal
from app.models import Application, Job, ApplicationStatus, JobStatus
from app.schemas import ApplicationResponse, WebhookApplication
from app.services.cv_parser import CVParser
from app.services.ai_scoring import AIScoringService
from app.services.file_storage import FileStorageService
from app.core.auth_utils import get_current_company

router = APIRouter(prefix="/api/applications", tags=["Applications"])


# -------------------------------------------------
# Submit Application
# -------------------------------------------------
@router.post("/apply/{job_id}", response_model=dict)
async def submit_application(
    job_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    applicant_email: str = Form(...),
    resume: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """Submit application via frontend/apply link."""
    job = db.query(Job).filter(Job.id == job_id, Job.status == JobStatus.ACTIVE).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found or expired")

    if job.deadline < datetime.now().astimezone():
        raise HTTPException(status_code=400, detail="Application deadline has passed")

    allowed_types = [
        "application/pdf",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/msword",
        "text/plain",
    ]
    if resume.content_type not in allowed_types:
        raise HTTPException(
            status_code=400,
            detail="Invalid file type. Upload PDF, DOC, DOCX, or TXT only."
        )

    # Save file
    file_storage = FileStorageService()
    try:
        file_path = file_storage.save_uploaded_file(resume, "resumes")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"File save failed: {str(e)}")

    # Create application record
    application = Application(
        job_id=job_id,
        applicant_email=applicant_email,
        resume_file=file_path,
        status=ApplicationStatus.PENDING,
    )
    db.add(application)
    db.commit()
    db.refresh(application)

    # Background processing (new DB session inside)
    background_tasks.add_task(process_application, application.id)

    return {"message": "Application submitted successfully", "application_id": str(application.id)}


# -------------------------------------------------
# Email/Webhook Application (from n8n or email parser)
# -------------------------------------------------
@router.post("/email-hook/{job_id}", response_model=dict)
async def email_webhook(
    job_id: uuid.UUID,
    webhook_data: WebhookApplication,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """Receive application via email parser or n8n webhook."""
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    application = Application(
        job_id=job_id,
        applicant_email=webhook_data.applicant_email,
        resume_file=webhook_data.resume_file,
        status=ApplicationStatus.PENDING,
    )
    db.add(application)
    db.commit()
    db.refresh(application)

    background_tasks.add_task(process_application, application.id)

    return {"message": "Application received via email webhook", "application_id": str(application.id)}


# -------------------------------------------------
# Get Applications for a Job
# -------------------------------------------------
@router.get("/job/{job_id}", response_model=List[ApplicationResponse])
async def get_job_applications(
    job_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_company=Depends(get_current_company),
):
    """Get all applications for a specific job belonging to the current company."""
    job = db.query(Job).filter(Job.id == job_id, Job.company_id == current_company.id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    applications = (
        db.query(Application)
        .filter(Application.job_id == job_id)
        .order_by(Application.created_at.desc())
        .all()
    )

    return applications


# -------------------------------------------------
# Get Specific Application
# -------------------------------------------------
@router.get("/{application_id}", response_model=ApplicationResponse)
async def get_application(
    application_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_company=Depends(get_current_company),
):
    """Get detailed info about one application."""
    application = (
        db.query(Application)
        .join(Job)
        .filter(Application.id == application_id, Job.company_id == current_company.id)
        .first()
    )
    if not application:
        raise HTTPException(status_code=404, detail="Application not found")

    return application


# -------------------------------------------------
# Background Processing
# -------------------------------------------------
def process_application(application_id: uuid.UUID):
    """Parse resume + AI score in background."""
    db = SessionLocal()
    try:
        application = db.query(Application).filter(Application.id == application_id).first()
        if not application:
            return

        job = db.query(Job).filter(Job.id == application.job_id).first()
        if not job:
            return

        # Parse CV
        parsed_data = None
        if application.resume_file and os.path.exists(application.resume_file):
            parsed_data = CVParser().parse_resume(application.resume_file)

        # AI Scoring
        scoring_result = AIScoringService().score_application(job.requirements, parsed_data or {})

        application.parsed_data = parsed_data
        application.ai_score = scoring_result["score"]
        application.status = ApplicationStatus(scoring_result["status"])

        db.commit()
        print(
            f"✅ Application {application_id} processed. "
            f"Score: {scoring_result['score']}, Status: {scoring_result['status']}"
        )

    except Exception as e:
        print(f"❌ Error processing application {application_id}: {e}")
        if application:
            application.status = ApplicationStatus.FLAGGED
            db.commit()
    finally:
        db.close()
