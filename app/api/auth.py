from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer
from sqlalchemy.orm import Session
from datetime import timedelta
from app.database import get_db
from app.models import Company
from app.schemas import CompanyCreate, CompanyLogin, CompanyResponse, Token
from app.auth import authenticate_company, create_access_token, get_password_hash, get_current_company
from app.config import settings

router = APIRouter(prefix="/api/auth", tags=["authentication"])

@router.post("/register", response_model=CompanyResponse)
async def register(company_data: CompanyCreate, db: Session = Depends(get_db)):
    # Check if company already exists
    existing_company = db.query(Company).filter(Company.email == company_data.email).first()
    if existing_company:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Company with this email already exists"
        )
    
    # Create new company
    hashed_password = get_password_hash(company_data.password)
    company = Company(
        name=company_data.name,
        email=company_data.email,
        password_hash=hashed_password
    )
    
    db.add(company)
    db.commit()
    db.refresh(company)
    
    return CompanyResponse.from_orm(company)

@router.post("/login", response_model=Token)
async def login(login_data: CompanyLogin, db: Session = Depends(get_db)):
    company = authenticate_company(db, login_data.email, login_data.password)
    if not company:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
    access_token = create_access_token(
        data={"sub": company.email}, expires_delta=access_token_expires
    )
    
    return Token(
        access_token=access_token,
        token_type="bearer",
        company=CompanyResponse.from_orm(company)
    )

@router.get("/me", response_model=CompanyResponse)
async def get_me(current_company: CompanyResponse = Depends(get_current_company)):
    return current_company