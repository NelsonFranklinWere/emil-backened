from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List
import uuid
import json
from datetime import datetime
from app.database import get_db
from app.models import Report, Job, Application, ApplicationStatus
from app.schemas import ReportResponse, ReportCreate, JobStatistics
from app.auth import get_current_company
from app.services.email_service import EmailService
from app.services.file_storage import FileStorageService

router = APIRouter(prefix="/api/reports", tags=["reports"])

@router.post("/generate/{job_id}", response_model=ReportResponse)
async def generate_report(
    job_id: uuid.UUID,
    report_data: ReportCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_company: CompanyResponse = Depends(get_current_company)
):
    """Generate and send report for a job"""
    # Verify job belongs to company
    job = db.query(Job).filter(Job.id == job_id, Job.company_id == current_company.id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    # Get applications for the job
    applications = db.query(Application).filter(Application.job_id == job_id).all()
    
    # Generate report summary
    summary = generate_report_summary(job, applications)
    
    # Create report record
    report = Report(
        job_id=job_id,
        summary=summary,
        sent_to=job.report_emails,
        file_url=None  # Will be updated if PDF is generated
    )
    
    db.add(report)
    db.commit()
    db.refresh(report)
    
    # Generate PDF and send email in background
    if report_data.include_pdf:
        background_tasks.add_task(
            generate_and_send_report,
            report.id,
            job,
            summary,
            job.report_emails,
            db
        )
    else:
        # Send email without PDF attachment
        background_tasks.add_task(
            send_report_email,
            job,
            summary,
            job.report_emails
        )
    
    return ReportResponse.from_orm(report)

@router.get("/job/{job_id}", response_model=List[ReportResponse])
async def get_job_reports(
    job_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_company: CompanyResponse = Depends(get_current_company)
):
    """Get all reports for a specific job"""
    # Verify job belongs to company
    job = db.query(Job).filter(Job.id == job_id, Job.company_id == current_company.id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    reports = db.query(Report).filter(Report.job_id == job_id).order_by(
        Report.created_at.desc()
    ).all()
    
    return reports

@router.get("/{report_id}", response_model=ReportResponse)
async def get_report(
    report_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_company: CompanyResponse = Depends(get_current_company)
):
    """Get specific report"""
    report = db.query(Report).join(Job).filter(
        Report.id == report_id,
        Job.company_id == current_company.id
    ).first()
    
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    
    return report

def generate_report_summary(job: Job, applications: List[Application]) -> dict:
    """Generate comprehensive report summary"""
    total_applications = len(applications)
    shortlisted = len([app for app in applications if app.status == ApplicationStatus.SHORTLISTED])
    flagged = len([app for app in applications if app.status == ApplicationStatus.FLAGGED])
    rejected = len([app for app in applications if app.status == ApplicationStatus.REJECTED])
    
    # Calculate scores statistics
    scores = [app.ai_score for app in applications if app.ai_score is not None]
    average_score = sum(scores) / len(scores) if scores else 0
    max_score = max(scores) if scores else 0
    min_score = min(scores) if scores else 0
    
    # Get top candidates
    top_candidates = sorted(
        [app for app in applications if app.ai_score is not None],
        key=lambda x: x.ai_score,
        reverse=True
    )[:5]
    
    top_candidates_data = [
        {
            "email": app.applicant_email,
            "score": app.ai_score,
            "status": app.status.value,
            "skills": app.parsed_data.get("skills", []) if app.parsed_data else []
        }
        for app in top_candidates
    ]
    
    # Skills analysis
    all_skills = []
    for app in applications:
        if app.parsed_data and "skills" in app.parsed_data:
            all_skills.extend(app.parsed_data["skills"])
    
    from collections import Counter
    skill_frequency = Counter(all_skills)
    top_skills = skill_frequency.most_common(10)
    
    return {
        "job_title": job.job_title,
        "generated_at": datetime.now().isoformat(),
        "statistics": {
            "total_applications": total_applications,
            "shortlisted": shortlisted,
            "flagged": flagged,
            "rejected": rejected,
            "average_score": round(average_score, 2),
            "max_score": max_score,
            "min_score": min_score
        },
        "top_candidates": top_candidates_data,
        "skills_analysis": {
            "top_skills": [{"skill": skill, "count": count} for skill, count in top_skills],
            "total_unique_skills": len(skill_frequency)
        },
        "processing_notes": {
            "ai_model_used": "Basic scoring algorithm",
            "cv_parsing_success_rate": f"{len([app for app in applications if app.parsed_data])}/{total_applications}"
        }
    }

def generate_and_send_report(report_id: uuid.UUID, job: Job, summary: dict, recipients: List[str], db: Session):
    """Generate PDF report and send email (background task)"""
    try:
        # For now, we'll create a simple text file as PDF placeholder
        # In production, integrate with a proper PDF generation library like ReportLab or WeasyPrint
        file_storage = FileStorageService()
        
        # Create report content
        report_content = f"""
        EMIL AI RECRUITMENT REPORT
        =========================
        
        Job Title: {job.job_title}
        Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        
        SUMMARY STATISTICS:
        - Total Applications: {summary['statistics']['total_applications']}
        - Shortlisted: {summary['statistics']['shortlisted']}
        - Flagged for Review: {summary['statistics']['flagged']}
        - Rejected: {summary['statistics']['rejected']}
        - Average Score: {summary['statistics']['average_score']}/100
        
        TOP CANDIDATES:
        {chr(10).join([f"- {candidate['email']} (Score: {candidate['score']}/100)" for candidate in summary['top_candidates']])}
        
        SKILLS ANALYSIS:
        Top skills found in applications:
        {chr(10).join([f"- {skill['skill']}: {skill['count']} applicants" for skill in summary['skills_analysis']['top_skills'][:5]])}
        
        This report was generated automatically by Emil AI.
        """
        
        # Save as text file (PDF placeholder)
        filename = f"report_{job.job_title.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        file_path = os.path.join(settings.upload_dir, "reports", filename)
        
        with open(file_path, "w") as f:
            f.write(report_content)
        
        # Update report with file URL
        report = db.query(Report).filter(Report.id == report_id).first()
        if report:
            report.file_url = file_storage.get_file_url(file_path)
            db.commit()
        
        # Send email with PDF attachment
        email_service = EmailService()
        email_service.send_report_email(recipients, job.job_title, summary, file_path)
        
    except Exception as e:
        print(f"Error generating and sending report: {e}")

def send_report_email(job: Job, summary: dict, recipients: List[str]):
    """Send report email without PDF attachment"""
    try:
        email_service = EmailService()
        email_service.send_report_email(recipients, job.job_title, summary)
    except Exception as e:
        print(f"Error sending report email: {e}")