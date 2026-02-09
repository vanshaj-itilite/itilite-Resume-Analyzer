import json
import os
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError
import dotenv

dotenv.load_dotenv()
backend_port = os.getenv("BACKEND_PORT", "8001")
backend_url = f'http://localhost:{backend_port}'.rstrip("/")

def run_full_analysis(document_text: str, ai_model: str | None = None, temperature: float | None = None, threshold: int | None = None):
    url = f"{backend_url}/analysis"

    payload = json.dumps(
        {
            "document_text": document_text,
            "ai_model": ai_model,
            "temperature": temperature,
            "threshold": threshold,
        }
    ).encode("utf-8")
    req = Request(url, data=payload, headers={"Content-Type": "application/json"})

    try:
        with urlopen(req, timeout=60) as resp:
            body = resp.read().decode("utf-8")
            return json.loads(body)
    except HTTPError as exc:
        detail = exc.read().decode("utf-8") if exc.fp else str(exc)
        raise RuntimeError(f"Analysis API error: {detail}") from exc
    except URLError as exc:
        raise RuntimeError(f"Analysis API unavailable: {exc}") from exc
