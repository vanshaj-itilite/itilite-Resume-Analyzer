from django import forms
from .ai_model_choices import AI_MODEL_CHOICES

class AnalysisForm(forms.Form):
    document_text = forms.CharField(
        required=False,
        label="Document Text",
        widget=forms.Textarea(
            attrs={
                "rows": 12,
                "placeholder": "Paste resume text or upload a PDF...",
            }
        ),
    )
    document_pdf = forms.FileField(required=False, label="Resume PDF")

    ai_model = forms.ChoiceField(
        choices=AI_MODEL_CHOICES,
        required=False,
        initial="llama-3.1-8b-instant",
        label="AI Model",
    )
    temperature = forms.FloatField(
        required=False,
        min_value=0.0,
        max_value=1.0,
        initial=0.2,
        label="Temperature",
        widget=forms.NumberInput(attrs={"step": "0.1"}),
    )
    threshold = forms.IntegerField(
        required=False,
        min_value=0,
        max_value=100,
        initial=50,
        label="Threshold",
        widget=forms.NumberInput(attrs={"type": "range", "min": 0, "max": 100}),
    )

    def clean(self):
        cleaned = super().clean()
        text = (cleaned.get("document_text") or "").strip()
        pdf = cleaned.get("document_pdf")

        if not text and not pdf:
            raise forms.ValidationError("Provide document text or upload a PDF.")

        return cleaned
