from fastapi import FastAPI
from api.routes_story import router as story_router
from api.routes_npc import router as npc_router
from api.routes_qa import router as qa_router

app = FastAPI(title="Foregamer NPC Generation System", version="0.2.0-hybrid")
app.include_router(story_router, prefix="/story", tags=["story"])
app.include_router(npc_router, prefix="/npc", tags=["npc"])
app.include_router(qa_router, prefix="/qa", tags=["qa"])
@app.get("/")
def root():
    return {"message": "Witamy w systemie generowania NPC Foregamer!"}