from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os
from app.database import engine, Base
from app.config import settings

# Import models to ensure they are registered with Base
from app.models import Company, Job, Application, Report

# Create database tables with better error handling
try:
    Base.metadata.create_all(bind=engine)
    print("✅ Database tables created successfully!")
except Exception as e:
    print(f"❌ Error creating database tables: {e}")
    print("⚠️  Starting API without database connection...")

app = FastAPI(
    title="Emil AI Recruitment API",
    description="AI-powered recruitment assistant backend with FastAPI",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        settings.frontend_url,
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://0.0.0.0:3000",
        "*"  # Allow all for development
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files for uploaded files
os.makedirs(settings.upload_dir, exist_ok=True)
os.makedirs(os.path.join(settings.upload_dir, "resumes"), exist_ok=True)
os.makedirs(os.path.join(settings.upload_dir, "reports"), exist_ok=True)

app.mount("/uploads", StaticFiles(directory=settings.upload_dir), name="uploads")

# Import and include routers
try:
    from app.api import auth, jobs, applications, reports, webhooks
    
    # Include routers
    app.include_router(auth.router)
    app.include_router(jobs.router)
    app.include_router(applications.router)
    app.include_router(reports.router)
    app.include_router(webhooks.router)
    print("✅ All API routes loaded successfully!")
except Exception as e:
    print(f"❌ Error loading API routes: {e}")

@app.get("/")
async def root():
    return {
        "message": "Emil AI Recruitment API", 
        "status": "running",
        "version": "1.0.0",
        "docs": "/docs"
    }

@app.get("/health")
async def health_check():
    try:
        # Test database connection
        with engine.connect() as conn:
            conn.execute("SELECT 1")
        db_status = "connected"
    except Exception:
        db_status = "disconnected"
    
    return {
        "status": "healthy", 
        "version": "1.0.0",
        "database": db_status,
        "environment": settings.environment
    }

@app.get("/api/status")
async def api_status():
    return {
        "service": "emil-ai-backend",
        "status": "operational",
        "timestamp": "2024-01-01T00:00:00Z",
        "features": {
            "authentication": "enabled",
            "job_management": "enabled",
            "cv_parsing": "enabled",
            "ai_scoring": "enabled",
            "email_reports": "enabled",
            "webhooks": "enabled"
        }
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.environment == "development"
    )