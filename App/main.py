from fastapi import FastAPI
from api.routes_general import router as qa_router

app = FastAPI(title="Foregamer NPC Generation System", version="0.2.0-hybrid")
app.include_router(qa_router, prefix="/qa", tags=["qa"])
@app.get("/")
def root():
    return {"message": "Witamy w systemie generowania NPC Foregamer!"}