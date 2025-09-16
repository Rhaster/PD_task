"""Small utilities for logging, session IDs, and prompt helpers. exception handling."""
from fastapi import HTTPException
import time, random, string
import logging
def setup_logging(level: int | None = None) -> None:
    """Configure global logging once for the application.

    Args:
        level: Optional logging level. Defaults to ``logging.INFO``.
    """
    logging.getLogger("pymongo").setLevel(logging.WARNING)
    logging.basicConfig(level=level or logging.DEBUG)


def logging_function(message: str, level: str = "info") -> None:
    """Unified logging entry used across the project.

    Args:
        message: Text to log.
        level: One of ``"debug"``, ``"info"``, ``"warning"``, ``"error"``,
            or ``"critical"``.
    """
    level_lower = (level or "info").lower()
    if level_lower == "debug":
        logging.debug(message)
    elif level_lower == "warning":
        logging.warning(message)
    elif level_lower == "error":
        logging.error(message)
    elif level_lower == "critical":
        logging.critical(message)
    else:
        logging.info(message)
def generate_session_id() -> str:
    """Return a unique session identifier composed of a timestamp and suffix."""
    logging.info("Generating new session ID")
    timestamp = int(time.time() * 1000)
    suffix = ''.join(random.choices(string.ascii_letters + string.digits, k=8))
    return f"{timestamp}_{suffix}"


def enforce_json_prompt(prompt: str) -> str:
    """Append a JSON instruction if one is not already present.

    The helper nudges LLM prompts toward structured output without being
    overly prescriptive.
    """
    if "json" not in prompt.lower():
        return prompt + "\n\nReturn the answer as JSON."
    return prompt




def handle_bad_request_error(e, logging_function=logging.error):
    """Handle Groq BadRequestError and raise appropriate HTTPException."""
    err_response = getattr(e, "response", None)
    msg = ""
    code = ""
    
    if err_response:
        try:
            err_json = err_response.json()
            msg = err_json.get("error", {}).get("message", "")
            code = err_json.get("error", {}).get("code", "")
        except Exception:
            msg = str(err_response)

    logging_function(f"Groq BadRequestError caught: {msg}")

    if "max completion tokens reached" in msg or code == "json_validate_failed":
        raise HTTPException(
            status_code=429, 
            detail="API limit exceeded. Please try again later."
        )
    else:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid request to API: {msg}"
        )
