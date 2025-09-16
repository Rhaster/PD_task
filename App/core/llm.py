# core/llm.py
# LLM interaction using Groq API with session management in MongoDB.
# Supports chat completions with JSON responses and error handling.
# Caches API key and client instance for efficiency.
# Provides functions to get and save chat messages in a session.
# Loads environment variables from .env if available.
# Handles missing API key with clear error messages.
# Uses Groq's chat completion with a specified model and response format.
# Retries on JSON decode errors with user prompt to return valid JSON only.
from __future__ import annotations
import os, json, time
from typing import Any, Dict, Optional
from groq import Groq
from pymongo import MongoClient
from datetime import datetime
import json, time
from db.database import sessions

try:
    from dotenv import load_dotenv, find_dotenv
    _env_path = find_dotenv()  
    if _env_path:
        load_dotenv(_env_path, override=False)
except Exception:
    _env_path = None

def _get_env_key() -> Optional[str]:
    key = (
        os.getenv("GROQ_API_KEY")
        or os.getenv("GROQ_APIKEY")
        or os.getenv("GROQ_TOKEN")
        or os.getenv("GROQ_KEY")
    )
    if not key:
        return None
    key = key.strip().strip("'").strip('"')
    return key or None

CHAT_MODEL = os.getenv("CHAT_MODEL", "openai/gpt-oss-20b")
class LLMError(RuntimeError):
    pass
_client: Optional[Groq] = None
_api_key_cache: Optional[str] = None

def _get_client() -> Groq:
    global _client, _api_key_cache
    if _client is not None:
        return _client
    api_key = _get_env_key()
    if not api_key:
        # zbuduj czytelny komunikat diagnostyczny
        where = f".env: {_env_path}" if _env_path else "(.env nie znaleziono)"
        tried = "GROQ_API_KEY / GROQ_APIKEY / GROQ_TOKEN / GROQ_KEY"
        raise LLMError(
            f"Missing Groq API key in env ({where})"
        )

    _api_key_cache = api_key
    _client = Groq(api_key=api_key)
    return _client


def get_session(session_id: str) -> dict:
    session = sessions.find_one({"session_id": session_id})
    if not session:
        session = {
            "session_id": session_id,
            "messages": [],
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        }
        sessions.insert_one(session)
    return session


def save_message(session_id: str, role: str, content: str):
    sessions.update_one(
        {"session_id": session_id},
        {
            "$push": {"messages": {"role": role, "content": content}},
            "$set": {"updated_at": datetime.utcnow()},
        },
    )


def chat_json(
    system: str,
    user: str,
    session_id: str,
    *,
    temperature: float = 0.2,
    max_tokens: int = 1000,
    max_retries: int = 2,
):
    client = _get_client()  # Twój kod z Groq
    session = get_session(session_id)

    messages = [{"role": "system", "content": system}]
    messages.extend(session["messages"])
    messages.append({"role": "user", "content": user})

    last_err = None
    for _ in range(max_retries + 1):
        resp = client.chat.completions.create(
            model=CHAT_MODEL,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            response_format={"type": "json_object"},
        )
        content = (resp.choices[0].message.content or "").strip()
        try:
            parsed = json.loads(content)

            # zapisz wiadomości do historii
            save_message(session_id, "user", user)
            save_message(session_id, "assistant", content)

            return parsed
        except json.JSONDecodeError as e:
            last_err = e
            messages.append({
                "role": "user",
                "content": "Return ONLY valid JSON. No prose, no code fences."
            })
            time.sleep(0.2)

    raise LLMError(f"Model nie zwrócił poprawnego JSON po retry: {last_err}")