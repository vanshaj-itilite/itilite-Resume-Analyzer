import json
import os
import tempfile

from django.shortcuts import render, redirect
from django.utils import timezone

from .forms import AnalysisForm
from .models import AnalysisRun
from .services import run_full_analysis, backend_url
from .pdf_utils import pdf_reader

try:
    from utils.pyresparser.resume_parser import ResumeParser
except Exception:
    ResumeParser = None


def _extract_from_pdf(uploaded_file):
    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            for chunk in uploaded_file.chunks():
                tmp.write(chunk)
            tmp_path = tmp.name

        resume_text = pdf_reader(tmp_path)
        resume_data = None
        if ResumeParser is not None:
            resume_data = ResumeParser(tmp_path).get_extracted_data()

        return resume_text, resume_data
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.remove(tmp_path)


def index(request):
    result = request.session.pop("ui_result", None)
    error = request.session.pop("ui_error", None)
    resume_data = request.session.pop("ui_resume_data", None)

    if request.method == "POST":
        form = AnalysisForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                document_text = (form.cleaned_data.get("document_text") or "").strip()
                pdf_file = form.cleaned_data.get("document_pdf")

                if pdf_file:
                    try:
                        pdf_text, resume_data = _extract_from_pdf(pdf_file)
                        if not document_text:
                            document_text = (pdf_text or "").strip()
                    except Exception as exc:
                        error = f"Failed to parse PDF: {exc}"

                if not error:
                    result = run_full_analysis(
                        document_text,
                        ai_model=form.cleaned_data.get("ai_model"),
                        temperature=form.cleaned_data.get("temperature") or 0.2,
                        threshold=form.cleaned_data.get("threshold") or 70,
                    )

                    AnalysisRun.objects.create(
                        created_at=timezone.now(),
                        source="pdf" if pdf_file else "text",
                        ai_model=form.cleaned_data.get("ai_model") or "llama-3.1-8b-instant",
                        temperature=form.cleaned_data.get("temperature") or 0.2,
                        threshold=form.cleaned_data.get("threshold") or 50,
                        has_pdf=bool(pdf_file),
                        document_length=len(document_text),
                        result_json=json.dumps(result),
                    )
            except Exception as exc:
                error = str(exc)
        else:
            error = "Invalid input. Please check the form and try again."

        request.session["ui_result"] = result
        request.session["ui_error"] = error
        request.session["ui_resume_data"] = resume_data
        return redirect("index")

    form = AnalysisForm()
    return render(
        request,
        "ui/index.html",
        {
            "form": form,
            "result": result,
            "error": error,
            "resume_data": resume_data,
            "backend_url": backend_url,
        },
    )


def analytics(request):
    runs = AnalysisRun.objects.all()[:100]
    return render(request, "ui/analytics.html", {"runs": runs})
