# services/context_cache.py
# Simple in-memory cache for storing question-answer pairs.
# Note: This cache is not persistent and will be cleared when the application restarts.
# Used for saving user questions and answers in the current session.
# Provides methods to add, retrieve, and clear cached entries.
# Also provides a summary of all cached entries.

from core.llm import chat_json
from services.utility import generate_session_id
class ContextCache:
    def __init__(self):
        self._cache = {}

    def add(self, question, answer=None):
        self._cache["Previous question:" +question] = "Previous answer:" +answer
        if len(self._cache) >5:
            self.summary()

    def get(self, question):
        return self._cache.get(question)

    def all(self):
        return self._cache
    
    def clear(self):

        self._cache.clear()

    def summary(self):
        resp = chat_json(
        system="You are a helpful assistant that summarizes previous Q&A pairs into a concise summary. "
               "Return the result as a JSON object: {\"summary\": \"...\"}",
        user=f"Summarize the following Q&A pairs:\n{self._cache}",
        session_id=generate_session_id()
    )
        self._cache = {"summary": resp.get("summary", str(resp))}

context_cache = ContextCache()