# services/utility.py
# Utility functions for session ID generation and prompt enforcement.
# Provides a function to generate unique session IDs.
# Provides a function to enforce JSON response format in prompts.
import time, random, string
import logging
def generate_session_id() -> str:
    logging.info("Generating new session ID")
    timestamp = int(time.time() * 1000)
    suffix = ''.join(random.choices(string.ascii_letters + string.digits, k=8))
    return f"{timestamp}_{suffix}"


def enforce_json_prompt(prompt: str) -> str:
    if "json" not in prompt.lower():
        return prompt + "\n\nReturn the answer as JSON."
    return prompt