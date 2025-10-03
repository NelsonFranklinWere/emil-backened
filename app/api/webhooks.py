from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session
import uuid
from app.database import get_db
from app.models import Job, Application
from app.schemas import WebhookApplication, EmailWebhookData
from app.services.file_storage import FileStorageService
import base64
import os

router = APIRouter(prefix="/api/webhooks", tags=["webhooks"])

@router.post("/n8n/{job_id}")
async def n8n_webhook(
    job_id: uuid.UUID,
    webhook_data: WebhookApplication,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Generic webhook endpoint for n8n automation"""
    # Check if job exists
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    # Handle file if provided in webhook
    resume_file_path = None
    if webhook_data.resume_content:
        # Decode base64 content and save file
        try:
            file_storage = FileStorageService()
            
            # Determine file extension
            file_extension = ".pdf"  # Default to PDF, you might want to detect from metadata
            if webhook_data.metadata and "file_type" in webhook_data.metadata:
                file_extension = webhook_data.metadata["file_type"]
            
            # Generate filename
            filename = f"webhook_{uuid.uuid4()}{file_extension}"
            file_path = os.path.join(settings.upload_dir, "resumes", filename)
            
            # Decode and save file
            file_content = base64.b64decode(webhook_data.resume_content)
            with open(file_path, "wb") as f:
                f.write(file_content)
            
            resume_file_path = file_path
            
        except Exception as e:
            print(f"Error processing webhook file: {e}")
    
    # Create application
    application = Application(
        job_id=job_id,
        applicant_email=webhook_data.applicant_email,
        resume_file=resume_file_path,
        status="pending",
        parsed_data=webhook_data.metadata or {}
    )
    
    db.add(application)
    db.commit()
    db.refresh(application)
    
    # Process application in background
    from app.api.applications import process_application
    background_tasks.add_task(process_application, application.id, db)
    
    return {
        "message": "Webhook processed successfully",
        "application_id": str(application.id),
        "status": "processing"
    }

@router.post("/email-parser/{job_id}")
async def email_parser_webhook(
    job_id: uuid.UUID,
    email_data: EmailWebhookData,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Webhook specifically for email parsing services"""
    # Check if job exists
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    # Extract applicant email from sender
    applicant_email = email_data.from_email
    
    # Handle attachments
    resume_file_path = None
    if email_data.attachments:
        file_storage = FileStorageService()
        
        for attachment in email_data.attachments:
            if attachment.get("filename", "").lower().endswith(('.pdf', '.doc', '.docx', '.txt')):
                try:
                    # Save attachment
                    filename = f"email_attachment_{uuid.uuid4()}_{attachment['filename']}"
                    file_path = os.path.join(settings.upload_dir, "resumes", filename)
                    
                    # Decode base64 content if provided
                    if "content" in attachment:
                        file_content = base64.b64decode(attachment["content"])
                    else:
                        # Handle other attachment formats if needed
                        continue
                    
                    with open(file_path, "wb") as f:
                        f.write(file_content)
                    
                    resume_file_path = file_path
                    break  # Use first valid resume file
                    
                except Exception as e:
                    print(f"Error processing email attachment: {e}")
    
    # Create application
    application = Application(
        job_id=job_id,
        applicant_email=applicant_email,
        resume_file=resume_file_path,
        status="pending",
        parsed_data={
            "source": "email_webhook",
            "subject": email_data.subject,
            "body_preview": email_data.body[:200] + "..." if email_data.body and len(email_data.body) > 200 else email_data.body
        }
    )
    
    db.add(application)
    db.commit()
    db.refresh(application)
    
    # Process application in background
    from app.api.applications import process_application
    background_tasks.add_task(process_application, application.id, db)
    
    return {
        "message": "Email webhook processed successfully",
        "application_id": str(application.id),
        "applicant_email": applicant_email,
        "resume_processed": resume_file_path is not None
    }