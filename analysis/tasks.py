import base64
import logging
from analysis.store import load_pdf, store_extracted_text, load_extracted_text, store_analysis, load_analysis
from backend.celery_app import celery_app
from .services import run_full_analysis
from .pdf_utils import pdf_bytes_to_text

logger = logging.getLogger("backend.analysis.tasks")


@celery_app.task(name="analysis.tasks.extract_text_task", bind=True)
def extract_text_task(self, file_id: str):
    try:
        self.update_state(
            state="STARTED",
            meta={"stage": "extracting"}
        )

        file_bytes = load_pdf(file_id)
        text = (pdf_bytes_to_text(file_bytes) or "").strip()
        if not text:
            raise ValueError("No extractable text found in PDF.")
        # store the extracted text
        store_extracted_text(file_id, text)
        return {"file_id": file_id}
    
    except Exception:
        logger.exception("extract_pdf_text_failed", extra={"file_id": file_id})
        raise

@celery_app.task(name="analysis.tasks.analyze_resume_task", bind=True, rate_limit="5/m")
def analyze_resume_task(
    self,
    previous: dict,
    ai_model: str | None = None,
    temperature: float | None = None,
    threshold: int | None = None,
):
    try:
        self.update_state(
            state="STARTED",
            meta={"stage": "analysis"}
        )

        file_id = previous["file_id"]
        text = load_extracted_text(file_id)
        result = run_full_analysis(
            text,
            model=ai_model,
            temperature=temperature,
            threshold=threshold,
            task=self,
        )
        store_analysis(file_id, "full", result)
        return {
            "file_id": file_id
        }
    except Exception:
        logger.exception("analysis_task_failed")
        raise

@celery_app.task(name="analysis.tasks.reporting_task", bind=True, rate_limit="2/m")
def reporting_task(
    self,
    previous: dict
):
    try:
        self.update_state(state="STARTED", meta={"stage": "reporting"})

        file_id = previous["file_id"]
        logger.debug("reporting_task_data", extra={"file_id": file_id})

        # loading data
        result = load_analysis(file_id, "full")
        report = {
            "file_id": file_id,
            "summary": result["summary"],
            "score": result["score"],
        }
        return report 
    except Exception as e:
        logger.exception("reporting_task_failed", extra={"file_id": file_id})
        raise 
