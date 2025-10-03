
from fastapi import FastAPI, UploadFile, Form, HTTPException
from fastapi.responses import JSONResponse
from datetime import datetime
import uuid

app = FastAPI()

# In-memory storage
jobs = {}
applications = {}

@app.post("/api/job/create")
def create_job(
    title: str = Form(...),
    description: str = Form(...),
    requirements: str = Form(...),
    hr_email: str = Form(...),
    application_mode: str = Form(...),  # "link" or "email"
    start_date: str = Form(...),
    end_date: str = Form(...)
):
    job_id = str(uuid.uuid4())
    app_link = None
    if application_mode == "link":
        app_link = f"http://localhost:8000/apply/{job_id}"

    jobs[job_id] = {
        "title": title,
        "description": description,
        "requirements": requirements,
        "hr_email": hr_email,
        "mode": application_mode,
        "start_date": datetime.fromisoformat(start_date),
        "end_date": datetime.fromisoformat(end_date),
        "link": app_link
    }
    applications[job_id] = []

    return {"job_id": job_id, "application_url": app_link}


from fastapi import Request

@app.post("/apply/{job_id}")
async def apply_job(
    job_id: str,
    file: UploadFile = None,
    name: str = Form(None),
    email: str = Form(None),
    request: Request = None
):
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")

    job = jobs[job_id]
    now = datetime.now()
    if now < job["start_date"] or now > job["end_date"]:
        raise HTTPException(status_code=403, detail="Application period closed")

    # Try to parse JSON if no file/form data
    app_data = {
        "timestamp": now.isoformat()
    }
    if file:
        app_data["filename"] = file.filename
        app_data["name"] = name
        app_data["email"] = email
    else:
        try:
            json_body = await request.json()
            app_data.update(json_body)
        except Exception:
            app_data["error"] = "No valid application data received"

    applications[job_id].append(app_data)

    return JSONResponse({"message": "✅ Application received", "data": app_data})

@app.post("/api/job/close/{job_id}")
def close_job(job_id: str):
    job = jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    app_list = applications.get(job_id, [])


        # --- Integration Placeholders ---
        # LangChain/Langflow for CV parsing & ranking
        # scores = langchain_score(app_list)

        # n8n webhook for orchestration
        # trigger_n8n_workflow(job_id)

        # Gmail API for HR/rejection emails
        # send_gmail_invites_and_rejections(scores, job["hr_email"])

        # Google Calendar API for interview scheduling
        # schedule_interviews(scores)

        # Send report to HR email
        # send_report_to_hr(job["hr_email"], report)


    # --- End Integration Placeholders ---
    return {"message": "Job closed and processed", "report": report}

    @app.get("/api/report/{job_id}")
def report(job_id: str):
    job = jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    app_list = applications.get(job_id, [])

    # Placeholder: scoring and flagging logic
    scores = [
        {"name": app.get("name"), "score": 80, "flagged": False, "rejected": False} for app in app_list
    ]

    summary = {
        "total_applicants": len(app_list),
        "shortlisted": sum(1 for s in scores if not s["rejected"]),
        "flagged": sum(1 for s in scores if s["flagged"]),
        "rejected": sum(1 for s in scores if s["rejected"]),
        "details": scores
    }
    return summary
