# services/qa_pipeline.py
# QA pipeline for answering user questions based on context from RAG and cached interactions.
# Uses a predefined system prompt and user template for consistent responses.
# Combines retrieved context with previous Q&A pairs for better answers.
# Caches new Q&A pairs for future context.
# Returns answers along with their sources.
import logging
from core.prompts import QA_SYSTEM, QA_USER_TEMPLATE
from core.rag import FaissRAG
from core.llm import chat_json
from Models.queries import QAResponse
from services.utility import generate_session_id
from services.context_cache import context_cache

class QAPipeline:
    def __init__(self, rag: FaissRAG):
        self.rag = rag

    def answer(self, question: str) -> dict:
        logging.info(f"Answering question: {question}")
        ctx = self.rag.search(question, k=4)
        context_str = "\n---\n".join([f"{cid}: {txt}" for cid, txt in ctx])
        cache_context = "\n".join([f"{q}: {a}" for q, a in context_cache.all().items()])
        full_context = context_str + "\n---\n" + cache_context
        logging.info(f"Full context for QA: {full_context}")
        user = QA_USER_TEMPLATE.format(question=question, context=full_context)
        raw = chat_json(system=QA_SYSTEM, user=user,session_id=generate_session_id())
        logging.info(f"Raw QA response: {raw}")
        answer = raw.get("answer") if isinstance(raw, dict) else None
        sources = raw.get("sources") if isinstance(raw, dict) else None
        if not isinstance(sources, list):
            sources = [cid for cid, _ in ctx]
        if not isinstance(answer, str):
            answer = str(raw)
        context_cache.add(question,answer)
        logging.info(f"Final answer: {answer} with sources: {sources}") 
        return {"answer": answer, "sources": sources}