from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List
import os
import uuid
from app.database import get_db
from app.models import Application, Job, ApplicationStatus, JobStatus
from app.schemas import ApplicationResponse, ApplicationCreate, WebhookApplication, CompanyResponse  # Added CompanyResponse import
from app.services.cv_parser import CVParser
from app.services.ai_scoring import AIScoringService
from app.services.file_storage import FileStorageService
from app.auth import get_current_company
from app.config import settings

router = APIRouter(prefix="/api/applications", tags=["applications"])

@router.post("/apply/{job_id}")
async def submit_application(
    job_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    applicant_email: str = Form(...),
    resume: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """Submit application via generated link"""
    # Check if job exists and is active
    job = db.query(Job).filter(Job.id == job_id, Job.status == JobStatus.ACTIVE).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found or expired")
    
    # Check if job deadline has passed
    from datetime import datetime
    if job.deadline < datetime.now().astimezone():
        raise HTTPException(status_code=400, detail="Application deadline has passed")
    
    # Validate file type
    allowed_types = [
        'application/pdf', 
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        'application/msword',
        'text/plain'
    ]
    if resume.content_type not in allowed_types:
        raise HTTPException(
            status_code=400, 
            detail="Invalid file type. Please upload PDF, DOC, DOCX, or TXT"
        )
    
    # Save file
    file_storage = FileStorageService()
    try:
        file_path = file_storage.save_uploaded_file(resume, "resumes")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    # Create application record
    application = Application(
        job_id=job_id,
        applicant_email=applicant_email,
        resume_file=file_path,
        status=ApplicationStatus.PENDING
    )
    
    db.add(application)
    db.commit()
    db.refresh(application)
    
    # Process application in background
    background_tasks.add_task(process_application, application.id, db)
    
    return {"message": "Application submitted successfully"}

@router.post("/email-hook/{job_id}")
async def email_webhook(
    job_id: uuid.UUID,
    webhook_data: WebhookApplication,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Webhook endpoint for n8n email processing"""
    # Check if job exists
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    # Create application from email/webhook data
    application = Application(
        job_id=job_id,
        applicant_email=webhook_data.applicant_email,
        resume_file=webhook_data.resume_file,
        status=ApplicationStatus.PENDING
    )
    
    db.add(application)
    db.commit()
    db.refresh(application)
    
    # Process application in background
    background_tasks.add_task(process_application, application.id, db)
    
    return {"message": "Application received via email webhook"}

@router.get("/job/{job_id}", response_model=List[ApplicationResponse])
async def get_job_applications(
    job_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_company: CompanyResponse = Depends(get_current_company)  # Fixed: CompanyResponse is now imported
):
    """Get all applications for a specific job"""
    # Verify job belongs to company
    job = db.query(Job).filter(Job.id == job_id, Job.company_id == current_company.id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    applications = db.query(Application).filter(Application.job_id == job_id).order_by(
        Application.created_at.desc()
    ).all()
    
    return applications

@router.get("/{application_id}", response_model=ApplicationResponse)
async def get_application(
    application_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_company: CompanyResponse = Depends(get_current_company)  # Fixed: CompanyResponse is now imported
):
    """Get specific application details"""
    application = db.query(Application).join(Job).filter(
        Application.id == application_id,
        Job.company_id == current_company.id
    ).first()
    
    if not application:
        raise HTTPException(status_code=404, detail="Application not found")
    
    return application

def process_application(application_id: uuid.UUID, db: Session):
    """Background task to process application (CV parsing + AI scoring)"""
    try:
        application = db.query(Application).filter(Application.id == application_id).first()
        if not application:
            return
        
        job = db.query(Job).filter(Job.id == application.job_id).first()
        if not job:
            return
        
        # Parse CV
        cv_parser = CVParser()
        parsed_data = None
        
        if application.resume_file and os.path.exists(application.resume_file):
            parsed_data = cv_parser.parse_resume(application.resume_file)
        
        # AI Scoring
        ai_scoring = AIScoringService()
        scoring_result = ai_scoring.score_application(job.requirements, parsed_data or {})
        
        # Update application
        application.parsed_data = parsed_data
        application.ai_score = scoring_result['score']
        application.status = ApplicationStatus(scoring_result['status'])
        
        db.commit()
        
        print(f"Application {application_id} processed successfully. Score: {scoring_result['score']}, Status: {scoring_result['status']}")
        
    except Exception as e:
        print(f"Error processing application {application_id}: {e}")
        # You might want to update the application status to indicate processing failure
        try:
            application = db.query(Application).filter(Application.id == application_id).first()
            if application:
                application.status = ApplicationStatus.FLAGGED
                db.commit()
        except Exception:
            pass