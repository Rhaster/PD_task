from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, conint
from typing import List, Optional
from services.npc_pipeline import NPCPipeline
from core.rag import FaissRAG
from Config.config import settings

router = APIRouter()

class NPCRequest(BaseModel):
    prompt: Optional[str] = None
    count: conint(ge=1, le=10) = 1
    constraints: Optional[dict] = None

class NPCItem(BaseModel):
    name: str
    faction: Optional[str] = None
    profession: str
    personality_traits: List[str]
    notes: Optional[str] = None

class NPCResponse(BaseModel):
    items: List[NPCItem]

def get_pipeline() -> NPCPipeline:
    if not hasattr(get_pipeline, "_pipeline"):
        store = FaissRAG(settings.faiss_path)
        get_pipeline._pipeline = NPCPipeline(store)
    return get_pipeline._pipeline  # type: ignore

@router.post("/generate", response_model=NPCResponse)
def generate_npc(req: NPCRequest, pipeline: NPCPipeline = Depends(get_pipeline)):
    try:
        items = pipeline.generate(req.prompt, req.count, req.constraints)
        return {"items": items}
    except Exception as e:
        raise HTTPException(500, str(e))