from pydantic import BaseModel, EmailStr, validator, field_validator
from typing import Optional, List, Any
from datetime import datetime
from uuid import UUID
from enum import Enum

# Enums
class ApplicationMode(str, Enum):
    EMAIL = "email"
    LINK = "link"

class ApplicationStatus(str, Enum):
    PENDING = "pending"
    SHORTLISTED = "shortlisted"
    FLAGGED = "flagged"
    REJECTED = "rejected"

class JobStatus(str, Enum):
    ACTIVE = "active"
    EXPIRED = "expired"
    CLOSED = "closed"

# Auth Schemas
class CompanyBase(BaseModel):
    name: str
    email: EmailStr

class CompanyCreate(CompanyBase):
    password: str

    @field_validator('password')
    @classmethod
    def validate_password(cls, v):
        if len(v) < 6:
            raise ValueError('Password must be at least 6 characters long')
        return v

class CompanyLogin(BaseModel):
    email: EmailStr
    password: str

class CompanyResponse(CompanyBase):
    id: UUID
    created_at: datetime
    
    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str
    company: CompanyResponse

# Job Schemas
class JobBase(BaseModel):
    job_title: str
    job_description: str
    requirements: str
    application_mode: ApplicationMode
    application_email: Optional[EmailStr] = None
    report_emails: List[EmailStr]
    deadline: datetime
    interview_time: Optional[datetime] = None
    interview_link: Optional[str] = None
    
    @field_validator('application_email')
    @classmethod
    def validate_application_email(cls, v, info):
        if info.data.get('application_mode') == ApplicationMode.EMAIL and not v:
            raise ValueError('Application email is required for email mode')
        return v

    @field_validator('report_emails')
    @classmethod
    def validate_report_emails(cls, v):
        if not v:
            raise ValueError('At least one report email is required')
        return v

class JobCreate(JobBase):
    pass

class JobResponse(JobBase):
    id: UUID
    company_id: UUID
    status: JobStatus
    created_at: datetime
    applications_count: Optional[int] = 0
    
    class Config:
        from_attributes = True

# Application Schemas
class ApplicationBase(BaseModel):
    applicant_email: EmailStr

class ApplicationCreate(ApplicationBase):
    pass

class ApplicationResponse(ApplicationBase):
    id: UUID
    job_id: UUID
    resume_file: Optional[str]
    parsed_data: Optional[dict]
    ai_score: Optional[int]
    status: ApplicationStatus
    created_at: datetime
    
    class Config:
        from_attributes = True

# Report Schemas
class ReportBase(BaseModel):
    pass

class ReportCreate(BaseModel):
    include_pdf: bool = True

class ReportResponse(BaseModel):
    id: UUID
    job_id: UUID
    summary: dict
    file_url: Optional[str]
    sent_to: List[str]
    created_at: datetime
    
    class Config:
        from_attributes = True

# Webhook Schemas
class WebhookApplication(BaseModel):
    applicant_email: EmailStr
    resume_file: Optional[str] = None
    resume_content: Optional[str] = None
    metadata: Optional[dict] = None

class EmailWebhookData(BaseModel):
    from_email: EmailStr
    subject: str
    body: Optional[str]
    attachments: List[dict] = []

# Statistics Schemas
class JobStatistics(BaseModel):
    total_applications: int
    shortlisted: int
    flagged: int
    rejected: int
    average_score: Optional[float]