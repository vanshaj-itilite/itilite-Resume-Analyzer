import json
import re
import logging  
logger = logging.getLogger("backend.analysis.utils")

def parse_json_block(value):
    if not isinstance(value, str):
        return None

    trimmed = value.strip()

    # If wrapped in a fenced code block (e.g. ```json\n{...}\n``` or ```json{...}```), extract inner content
    fence_match = re.search(r"```(?:\w+)?\s*([\s\S]*?)\s*```", trimmed)
    if fence_match:
        trimmed = fence_match.group(1).strip()

    # First attempt: strict JSON
    try:
        return json.loads(trimmed)
    except Exception:
        pass

    # Fallback: extract first JSON object or array block
    match = re.search(r"(\{[\s\S]*?\}|\[[\s\S]*?\])", trimmed)
    if not match:
        return None

    try:
        return json.loads(match.group(1))
    except Exception:
        return None
    
def _coerce_to_str(value):
    if not isinstance(value, dict):
        return None
    try:
        return {k: str(v).strip() if isinstance(v, str) else str(v) for k, v in value.items()}
    except Exception:
        return None


def retry_policy(task, exc, kind):
    if kind == "rate_limit":
        return task.retry(exc=exc, countdown=120, max_retries=5)
    if kind == "network":
        return task.retry(exc=exc, countdown=30, max_retries=3)
    raise exc
