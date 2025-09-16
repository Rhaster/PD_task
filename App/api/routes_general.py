"""Routes for the general pipeline (QA endpoint)."""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from App.Services.general_pipeline import GeneralPipeline
from App.Core.rag import FaissRAG
from App.Config.config import settings
from App.Models.queries import QARequest
from App.Services.utility import logging_function

router = APIRouter()
_pipeline = GeneralPipeline()



@router.post("/qa")
def story_qa(req: QARequest):
    """Answer a question using the general pipeline (RAG + LLM)."""
    logging_function("Received QA request", level="info")
    return _pipeline.process(req.question)
