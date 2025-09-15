from fastapi import APIRouter
from pydantic import BaseModel
from services.general_pipeline import GeneralPipeline
from core.rag import FaissRAG
from Config.config import settings


router = APIRouter()
_rag = FaissRAG(index_path="faiss.index")  # Adjust path as needed
_pipeline = GeneralPipeline()


class QARequest(BaseModel):
    question: str


@router.post("/qa")
def story_qa(req: QARequest):
    return _pipeline.answer(req.question)