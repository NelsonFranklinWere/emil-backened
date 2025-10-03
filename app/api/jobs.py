from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime
import uuid
from app.database import get_db
from app.models import Job, Company, JobStatus
from app.schemas import JobCreate, JobResponse
from app.auth import get_current_company
from app.services.email_service import EmailService

router = APIRouter(prefix="/api/jobs", tags=["jobs"])

@router.post("/create", response_model=dict)
async def create_job(
    job_data: JobCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_company: Company = Depends(get_current_company)
):
    # Generate job ID and application URL if link mode
    job_id = uuid.uuid4()
    application_url = None
    
    if job_data.application_mode == "link":
        application_url = f"{current_company.frontend_url}/apply/{job_id}"
    
    # Create job
    job = Job(
        id=job_id,
        company_id=current_company.id,
        job_title=job_data.job_title,
        job_description=job_data.job_description,
        requirements=job_data.requirements,
        application_mode=job_data.application_mode,
        application_email=job_data.application_email,
        report_emails=job_data.report_emails,
        deadline=job_data.deadline,
        interview_time=job_data.interview_time,
        interview_link=job_data.interview_link,
        status=JobStatus.ACTIVE
    )
    
    db.add(job)
    db.commit()
    db.refresh(job)
    
    # Send confirmation email
    background_tasks.add_task(
        send_job_creation_confirmation,
        current_company.email,
        job_data.job_title,
        application_url
    )
    
    return {
        "job_id": job_id,
        "application_url": application_url,
        "message": "Job created successfully"
    }

@router.get("/", response_model=List[JobResponse])
async def get_company_jobs(
    db: Session = Depends(get_db),
    current_company: Company = Depends(get_current_company)
):
    jobs = db.query(Job).filter(Job.company_id == current_company.id).all()
    
    # Add applications count to each job
    job_responses = []
    for job in jobs:
        job_dict = JobResponse.from_orm(job).dict()
        job_dict['applications_count'] = len(job.applications)
        job_responses.append(job_dict)
    
    return job_responses

@router.get("/{job_id}", response_model=JobResponse)
async def get_job(
    job_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_company: Company = Depends(get_current_company)
):
    job = db.query(Job).filter(Job.id == job_id, Job.company_id == current_company.id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    job_dict = JobResponse.from_orm(job).dict()
    job_dict['applications_count'] = len(job.applications)
    
    return job_dict

def send_job_creation_confirmation(company_email: str, job_title: str, application_url: str = None):
    email_service = EmailService()
    
    subject = f"✅ Job Created: {job_title}"
    html_content = f"""
    <h2>Your Job Posting is Live! 🎉</h2>
    <p><strong>Job Title:</strong> {job_title}</p>
    """
    
    if application_url:
        html_content += f"""
        <p><strong>Application Link:</strong> 
        <a href="{application_url}">{application_url}</a></p>
        <p>Share this link with applicants to start receiving applications.</p>
        """
    else:
        html_content += """
        <p>Applications will be sent to your specified email address.</p>
        """
    
    html_content += """
    <p><em>You can view and manage this job from your dashboard.</em></p>
    """
    
    email_service.send_email([company_email], subject, html_content)