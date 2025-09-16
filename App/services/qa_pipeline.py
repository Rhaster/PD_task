
"""Question-answering pipeline built on top of a FAISS-backed RAG store."""
from App.Services.utility import logging_function
from App.Core.prompts import QA_SYSTEM, QA_USER_TEMPLATE
from App.Core.rag import FaissRAG
from App.Core.llm import chat_json
from App.Core.context_cache import context_cache
from App.Models.queries import QAResponse
from App.Services.utility import generate_session_id
from groq import BadRequestError
from fastapi import HTTPException
from App.Services.utility import handle_bad_request_error
class QAPipeline:
    """Resolve questions using retrieved context and chat LLM calls."""

    def __init__(self, rag: FaissRAG):
        """Bind a ``FaissRAG`` instance used for retrieval."""
        self.rag = rag

    def answer(self, question: str) -> dict:
        """Return an answer and sources for the provided ``question``."""
        logging_function(f"Answering question: {question}", level="info")
        ctx = self.rag.search(question, k=4)
        context_str = "\n---\n".join([f"{cid}: {txt}" for cid, txt in ctx])
        cache_context = "\n".join([f"{q}: {a}" for q, a in context_cache.all().items()])
        full_context = context_str + "\n---\n" + cache_context
        logging_function(f"Full context for QA: {full_context}", level="debug")
        user = QA_USER_TEMPLATE.format(question=question, context=full_context)
        try:
            logging_function("Sending QA prompt to LLM", level="info")
            raw = chat_json(system=QA_SYSTEM, user=user,session_id=generate_session_id())
        except BadRequestError as e:
            handle_bad_request_error(e, logging_function=logging_function)
            raise HTTPException(status_code=400, detail="Bad request to QA API") from e
        logging_function(f"Raw QA response: {raw}", level="debug")
        answer = raw.get("answer") if isinstance(raw, dict) else None
        sources = raw.get("sources") if isinstance(raw, dict) else None
        if not isinstance(sources, list):
            sources = [cid for cid, _ in ctx]
        if not isinstance(answer, str):
            answer = str(raw)
        context_cache.add(question,answer)
        logging_function(f"Final answer: {answer} with sources: {sources}", level="info") 
        return {"answer": answer, "sources": sources}