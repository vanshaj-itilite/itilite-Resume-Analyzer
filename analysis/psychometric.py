from typing import Optional
from analysis.utils import _coerce_to_str, parse_json_block, retry_policy
from groq import RateLimitError
from .types import PsychometricAnalysisInput, PsychometricAnalysisOutput
import logging
logger = logging.getLogger("backend.analysis.psychometric")


def psychometric_analysis(
    input: PsychometricAnalysisInput,
    task=None,
) -> PsychometricAnalysisOutput:
    logger.debug("psychometric_analysis_request", extra={"input": input})

    model_config = input.get("modelConfig", {})
    client = model_config["client"]
    model = model_config.get("model", "llama-3.1-8b-instant")
    temperature = model_config.get("temperature", 0.2)
    
    logger.debug("psychometric_analysis_model_config", extra={"model": model, "temperature": temperature})

    try:
        completion = client.chat.completions.create(
            model=model,
            temperature=temperature,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are an expert in psychometric analysis evaluation by reading text and CV. "
                        """Return FORMAT: JSON object with
                        - psychologicalTraits: A detailed analysis of the individual's psychological traits based on the provided text.
                        - risks: An assessment of potential risks or concerns that may arise from the individual's psychological profile.
                        - trends: An identification of any notable trends or patterns in the individual's psychological traits that may
                        """
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        "Analyze the following text to identify psychological traits, "
                        "potential risks, and trends.\n\n"
                        f"Text:\n{input['text']}\n\n"
                        "Return JSON only."
                    ),
                },
            ],
        )
    except RateLimitError as exc:
        if task is not None:
            return retry_policy(task, exc, "rate_limit")
        raise

    try:
        logger.debug("psychometric_analysis_response", extra={"response": completion.choices[0].message.content})
        content = completion.choices[0].message.content or "{}"
        logger.debug("raw_psychometric_response_content", extra={"content": content})
        parsed = parse_json_block(content)
        validated = as_psychometric_analysis_response(parsed)
        return {
            "psychologicalTraits": validated["psychologicalTraits"],
            "risks": validated["risks"],
            "trends": validated["trends"],
            "error": None,
            "code": 200
        }
    
    except Exception as e:
        logger.exception("psychometric_analysis_parsing_failed")
        return {
            "psychologicalTraits": None,
            "risks": None,
            "trends": None,
            "error": str(e),
            "code": 500
        }

def as_psychometric_analysis_response(
    value,
) -> Optional[PsychometricAnalysisOutput]:
    logger.debug("validating_psychometric_analysis_response", extra={"value": value})
    print(value)
    value = _coerce_to_str(value)
    
    if not value:
        return None
    
    return {
        "psychologicalTraits": value["psychologicalTraits"],
        "risks": value["risks"],
        "trends": value["trends"],
    }
