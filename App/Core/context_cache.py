"""In-memory cache for recent question/answer snippets and a rolling summary."""

from App.Core.llm import chat_json
from App.Services.utility import generate_session_id
from App.Core.prompts import SUMMARY_SYSTEM
class ContextCache:
    """Hold a small map of questions to answers for prompt augmentation."""

    def __init__(self):
        """Initialize the underlying mapping."""
        self._cache: dict[str, str] = {}

    def add(self, question, answer=None):
        """Record a question/answer pair and trigger summarization if needed."""
        self._cache["Previous question:" + question] = "Previous answer:" + (answer or "")
        if len(self._cache) >5:
            self.summary()

    def get(self, question):
        """Return the last answer for ``question`` if present."""
        return self._cache.get(question)

    def all(self):
        """Return a shallow copy of the cache mapping."""
        return dict(self._cache)
    
    def clear(self):
        """Reset the cache to an empty state."""
        self._cache.clear()

    def summary(self):
        """Ask the LLM for a compact summary of current Q/A pairs."""
        resp = chat_json(
        system=SUMMARY_SYSTEM,
        user=f"Summarize the following Q&A pairs:\n{self._cache}",
        session_id=generate_session_id()
    )
        self._cache = {"summary": resp.get("summary", str(resp))}
    
context_cache = ContextCache()