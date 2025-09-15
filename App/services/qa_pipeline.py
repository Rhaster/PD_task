from core.prompts import QA_SYSTEM, QA_USER_TEMPLATE
from core.rag import FaissRAG
from core.llm import chat_json
from Models.queries import QAResponse
from services.utility import generate_session_id

class QAPipeline:
    def __init__(self, rag: FaissRAG):
        self.rag = rag

    def answer(self, question: str) -> dict:
        ctx = self.rag.search(question, k=4)
        context_str = "\n---\n".join([f"{cid}: {txt}" for cid, txt in ctx])
        user = QA_USER_TEMPLATE.format(question=question, context=context_str)
        raw = chat_json(system=QA_SYSTEM, user=user,session_id=generate_session_id())
        # Normalize to {answer, sources}
        answer = raw.get("answer") if isinstance(raw, dict) else None
        sources = raw.get("sources") if isinstance(raw, dict) else None
        if not isinstance(sources, list):
            sources = [cid for cid, _ in ctx]
        if not isinstance(answer, str):
            answer = str(raw)
        return {"answer": answer, "sources": sources}