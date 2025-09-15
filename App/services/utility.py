
import time, random, string
def generate_session_id() -> str:
    """Generuje unikalny session_id w formacie timestamp + losowy sufiks"""
    timestamp = int(time.time() * 1000)
    suffix = ''.join(random.choices(string.ascii_letters + string.digits, k=8))
    return f"{timestamp}_{suffix}"


def enforce_json_prompt(prompt: str) -> str:
    if "json" not in prompt.lower():
        return prompt + "\n\nReturn the answer as JSON."
    return prompt