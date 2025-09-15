from fastapi import APIRouter, HTTPException
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
    try:
        return _pipeline.process(req.question)
    except Exception as e:
        print(f"Error in QA endpoint: {e}")
        raise HTTPException(status_code=500, detail="Internal error while processing your request.")