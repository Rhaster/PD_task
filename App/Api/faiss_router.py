"""Routes for building and managing FAISS indices from markdown files."""
from App.Services.faiss_converter import build_index
from pydantic import BaseModel
from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from App.Services.utility import logging_function

router = APIRouter()

class RunFaissRequest(BaseModel):
    """Schema for FAISS build requests."""
    story_path: str
    index_path: str = "App/Data/index.faiss"
    meta_path: str = "App/Data/index.faiss.meta.jsonl"
    chunk_words: int = 220
    overlap_words: int = 50

@router.post("/run_faiss")
async def run_faiss(req: RunFaissRequest):
    """Trigger a FAISS index build and return basic metadata or an error."""
    try:
        logging_function("FAISS build requested", level="info")
        result = build_index(
            story_path=req.story_path,
            out_index_path=req.index_path,
            out_meta_path=req.meta_path,
            chunk_words=req.chunk_words,
            overlap_words=req.overlap_words
        )
        return JSONResponse(content=result)
    except Exception as e:
        logging_function(f"FAISS build failed: {e}", level="error")
        return JSONResponse(content={"error": str(e)}, status_code=500)