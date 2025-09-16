"""Groq LLM client and session utilities.

This module wraps API-key discovery, a lazily initialized Groq client, basic
session persistence in MongoDB, and a helper ``chat_json`` that requests a
JSON-formatted response with retries.
"""
from __future__ import annotations
import  json, time
from typing import Optional
from groq import Groq
from datetime import datetime
import json, time
from App.Config.database import sessions
from App.Config.config import settings




CHAT_MODEL = settings.groq_model
class LLMError(RuntimeError):
    pass
_client: Optional[Groq] = None
_api_key_cache: Optional[str] = None

def _get_client() -> Groq:
    """Return a cached Groq client, initializing it on first use."""
    global _client, _api_key_cache
    if _client is not None:
        return _client
    api_key = settings.groq_api_key
    if not api_key:
        raise LLMError(
            f"Missing Groq API key"
        )
    _api_key_cache = api_key
    _client = Groq(api_key=api_key)
    return _client


def get_session(session_id: str) -> dict:
    """Fetch or create a session document for the given ``session_id``."""
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
    """Append a chat message to the session and bump ``updated_at``."""
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
    max_tokens: int = 2000,
    max_retries: int = 2,
):
    """ Send a chat request and parse the JSON response."""
    client = _get_client()
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
            print("Prompt:", user)
            print("content", content)
            save_message(session_id, "user", user)
            save_message(session_id, "assistant", content)

            return parsed
        except json.JSONDecodeError as e:
            last_err = e
            messages.append({
                "role": "user",
                "content": "Return ONLY valid JSON. No prose, no code fences."
            })
            time.sleep(10)

    raise LLMError(f"Model did not return valid JSON after retries: {last_err}")