from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os

from app.database import engine, Base
from app.config import settings

# Import routers (clean + structured)
from app.api import auth, jobs, applications, reports, webhooks
from app.models import Company, Job, Application, Report  # Ensure models are registered


# -------------------------------------------------
# ✅ Database Initialization
# -------------------------------------------------
try:
    Base.metadata.create_all(bind=engine)
    print("✅ Database tables created successfully!")
except Exception as e:
    print(f"❌ Error creating database tables: {e}")
    print("⚠️ API starting without database connection...")


# -------------------------------------------------
# ✅ FastAPI Application
# -------------------------------------------------
app = FastAPI(
    title="Emil AI Recruitment API",
    description="AI-powered recruitment assistant backend with FastAPI",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)


# -------------------------------------------------
# ✅ CORS Configuration
# -------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        settings.frontend_url,
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# -------------------------------------------------
# ✅ Static Files (Uploads: resumes, reports)
# -------------------------------------------------
os.makedirs(settings.upload_dir, exist_ok=True)
os.makedirs(os.path.join(settings.upload_dir, "resumes"), exist_ok=True)
os.makedirs(os.path.join(settings.upload_dir, "reports"), exist_ok=True)

app.mount("/uploads", StaticFiles(directory=settings.upload_dir), name="uploads")


# -------------------------------------------------
# ✅ Routers
# -------------------------------------------------
app.include_router(auth.router, prefix="/api/auth", tags=["Auth"])
app.include_router(jobs.router, prefix="/api/jobs", tags=["Jobs"])
app.include_router(applications.router, prefix="/api/applications", tags=["Applications"])
app.include_router(reports.router, prefix="/api/reports", tags=["Reports"])
app.include_router(webhooks.router, prefix="/api/webhooks", tags=["Webhooks"])


# -------------------------------------------------
# ✅ Health + Status Endpoints
# -------------------------------------------------
@app.get("/")
async def root():
    """Root endpoint with API info"""
    return {
        "message": "Emil AI Recruitment API",
        "status": "running",
        "version": "1.0.0",
        "docs": "/docs"
    }


@app.get("/health")
async def health_check():
    """Database + service health check"""
    try:
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
    """API status + available features"""
    return {
        "service": "emil-ai-backend",
        "status": "operational",
        "features": {
            "authentication": True,
            "job_management": True,
            "applications": True,
            "reports": True,
            "webhooks": True,
        }
    }


# -------------------------------------------------
# ✅ Run App
# -------------------------------------------------
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.environment == "development"
    )
