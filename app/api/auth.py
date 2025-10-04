from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import timedelta

from app.database import get_db
from app.models import Company
from app.schemas import CompanyCreate, CompanyLogin, CompanyResponse, Token
from app.core.auth_utils import (
    get_password_hash,
    verify_password,
    create_access_token,
    get_current_company,
)
from app.config import settings

router = APIRouter(prefix="/api/auth", tags=["Auth"])

# -------------------------------
# Register a company
# -------------------------------
@router.post("/register", response_model=CompanyResponse)
async def register(company_data: CompanyCreate, db: Session = Depends(get_db)):
    """Register a new company account"""
    # Check if email already exists
    existing_company = db.query(Company).filter(Company.email == company_data.email).first()
    if existing_company:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Company with this email already exists",
        )

    # Hash password and create new company
    hashed_password = get_password_hash(company_data.password)
    company = Company(
        name=company_data.name,
        email=company_data.email,
        password=hashed_password  # 🔑 ensure your Company model has `password` field
    )

    db.add(company)
    db.commit()
    db.refresh(company)

    return company  # Pydantic will convert via CompanyResponse


# -------------------------------
# Login (get JWT token)
# -------------------------------
@router.post("/login", response_model=Token)
async def login(login_data: CompanyLogin, db: Session = Depends(get_db)):
    """Authenticate company and return access token"""
    company = db.query(Company).filter(Company.email == login_data.email).first()
    if not company or not verify_password(login_data.password, company.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Create JWT
    access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
    access_token = create_access_token(
        data={"sub": str(company.id)},
        expires_delta=access_token_expires,
    )

    return Token(
        access_token=access_token,
        token_type="bearer",
        company=company
    )


# -------------------------------
# Get current logged-in company
# -------------------------------
@router.get("/me", response_model=CompanyResponse)
async def get_me(current_company: CompanyResponse = Depends(get_current_company)):
    """Return details of the logged-in company"""
    return current_company
