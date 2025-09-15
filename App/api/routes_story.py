# app/api/routes_story.py
from fastapi import APIRouter
from services.qa_pipeline import QAPipeline
from core.rag import FaissRAG
from Config.config import settings
from Models.queries import QARequest, QAResponse

router = APIRouter()
_rag = FaissRAG(index_path=settings.faiss_path)
_pipeline = QAPipeline(_rag)


@router.post("/qa", response_model=QAResponse)
def story_qa(req: QARequest):
    return _pipeline.answer(req.question)