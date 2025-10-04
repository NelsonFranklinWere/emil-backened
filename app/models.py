from sqlalchemy import Column, String, Text, DateTime, ForeignKey, Enum, Integer, Boolean
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from app.database import Base
from app.schemas import ApplicationStatus, JobStatus, ApplicationMode


# ================================
# Company Model
# ================================
class Company(Base):
    __tablename__ = "companies"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False, unique=True)
    name = Column(String(255), nullable=False)
    email = Column(String(255), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    jobs = relationship("Job", back_populates="company")


# ================================
# Job Model
# ================================
class Job(Base):
    __tablename__ = "jobs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False, unique=True)
    company_id = Column(UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False)

    job_title = Column(String(255), nullable=False)
    job_description = Column(Text, nullable=False)
    requirements = Column(Text, nullable=True)

    application_mode = Column(Enum(ApplicationMode), nullable=False, default=ApplicationMode.LINK)
    application_email = Column(String(255), nullable=True)
    report_emails = Column(Text, nullable=False)  # stored as comma-separated list

    deadline = Column(DateTime, nullable=False)
    interview_time = Column(DateTime, nullable=True)
    interview_link = Column(String(500), nullable=True)

    status = Column(Enum(JobStatus), nullable=False, default=JobStatus.ACTIVE)
    created_at = Column(DateTime, default=datetime.utcnow)

    company = relationship("Company", back_populates="jobs")
    applications = relationship("Application", back_populates="job", cascade="all, delete-orphan")
    reports = relationship("Report", back_populates="job", cascade="all, delete-orphan")


# ================================
# Application Model
# ================================
class Application(Base):
    __tablename__ = "applications"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False, unique=True)
    job_id = Column(UUID(as_uuid=True), ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False)

    applicant_email = Column(String(255), nullable=False)
    resume_file = Column(String(500), nullable=True)  # file path
    parsed_data = Column(JSONB, nullable=True)
    ai_score = Column(Integer, nullable=True)
    status = Column(Enum(ApplicationStatus), nullable=False, default=ApplicationStatus.PENDING)

    created_at = Column(DateTime, default=datetime.utcnow)

    job = relationship("Job", back_populates="applications")


# ================================
# Report Model
# ================================
class Report(Base):
    __tablename__ = "reports"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False, unique=True)
    job_id = Column(UUID(as_uuid=True), ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False)

    summary = Column(JSONB, nullable=False)
    file_url = Column(String(500), nullable=True)
    sent_to = Column(Text, nullable=False)  # comma-separated emails
    created_at = Column(DateTime, default=datetime.utcnow)

    job = relationship("Job", back_populates="reports")
