import logging
import os
import secrets
from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from celery.result import AsyncResult
from celery import chain
from analysis.store import store_pdf
from analysis.types import AnalysisRequest, AnalysisResponse
from analysis.services import run_full_analysis
from analysis.tasks import analyze_resume_task, extract_text_task, reporting_task
from project.backend.celery_app import celery_app
from project.utils.logging_config import configure_logging

configure_logging()
logger = logging.getLogger("backend.api")

app = FastAPI(title="AI Resume Analyzer API")
frontend_origin = os.getenv("FRONTEND_URL", "http://localhost:8000")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[frontend_origin],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/analysis", response_model=AnalysisResponse)
def analyze(payload: AnalysisRequest):
    try:
        logger.info(
            "analysis_request",
            extra={
                "model": payload.ai_model,
                "temperature": payload.temperature,
                "threshold": payload.threshold,
                "text_length": len(payload.document_text),
            },
        )
        return run_full_analysis(
            payload.document_text,
            model=payload.ai_model,
            temperature=payload.temperature,
        )
    except Exception as exc:
        logger.exception("analysis_failed")
        raise HTTPException(status_code=500, detail=str(exc)) from exc

@app.post("/analysis/async")
async def analyze_async(
    file: UploadFile = File(...),
    ai_model: str | None = Form(default=None),
    temperature: float | None = Form(default=None),
    threshold: int | None = Form(default=None),
):
    filename = (file.filename or "").strip()
    if not filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")
    
    file_id = secrets.token_hex(16)
    # save the file with file_id
    pdf_bytes = await file.read()
    if not pdf_bytes:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")
    store_pdf(file_id, pdf_bytes)
    
    task = chain(
        extract_text_task.s(file_id),
        analyze_resume_task.s(ai_model=ai_model, temperature=temperature, threshold=threshold),
        reporting_task.s(),
    ).apply_async()
    return {"task_id": task.id, "file_id": file_id, "filename": filename}


@app.get("/analysis/status/{task_id}")
def analysis_status(task_id: str):
    result = AsyncResult(task_id, app=celery_app)

    payload = {
        "task_id": task_id,
        "state": result.state,
        "progress": 0,
        "stage": None,
    }

    # --- Pending ---
    if result.state == "PENDING":
        payload["progress"] = 0

    # --- Running / Retry ---
    elif result.state in ("STARTED", "RETRY"):
        meta = result.info or {}
        stage = meta.get("stage")

        stage_progress = {
            "extracting": 20,
            "analysis": 60,
            "reporting": 90,
        }

        payload["stage"] = stage
        payload["progress"] = stage_progress.get(stage, 10)

    # --- Success ---
    elif result.state == "SUCCESS":
        payload["stage"] = "done"
        payload["progress"] = 100
        payload["result"] = result.result

    # --- Failure ---
    elif result.state == "FAILURE":
        payload["stage"] = "failed"
        payload["progress"] = 100
        payload["error"] = str(result.result)

    return payload
