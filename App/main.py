"""FastAPI application entry point for the NPC Generation System.

This module wires the API routers, templating, CORS, and top-level routes:

- Home page rendering with environment values and NPC names.
- Chat endpoint that forwards questions to the QA pipeline service.
- Reset endpoint to clear in-memory chat context.
- Endpoint to list NPC names from MongoDB.
- Endpoint to upload a markdown story used for RAG indexing.

The application relies on configuration values provided via environment
variables and initializes logging at import-time.
"""
from fastapi import FastAPI, Request, Form,  UploadFile, File
from fastapi.templating import Jinja2Templates

from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pymongo import MongoClient
from App.Core.context_cache import context_cache
import os
from App.Api.routes_general import router as qa_router
from App.Api.faiss_router import router as faiss_router
import httpx
import shutil
from App.Config.database import npc_collection 
from App.Config.config import settings
from App.Services.utility import setup_logging, logging_function
from pathlib import Path
from App.Config.paths import get_data_dir
setup_logging()


app = FastAPI(title="NPC Generation System", version="0.2.0-hybrid",root_path="/api/v1")
app.include_router(qa_router, prefix="/qa", tags=["qa"])
app.include_router(faiss_router, prefix="/faiss", tags=["faiss"])
BASE_DIR = Path(__file__).parent
templates = Jinja2Templates(directory=BASE_DIR / "templates")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8000"],  
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def home(request: Request):
    """Render the index page with current environment and NPC list.

    The template consumes two primary values: a list of ``npc_names`` and a
    mapping ``env`` with selected configuration variables for quick inspection.
    """
    npc_names = []
    env_vars = {
        "APP_ENV": settings.app_env,
        "GROQ_API_KEY": settings.groq_api_key,
        "GROQ_BASE_URL": str(settings.groq_base_url),
        "GROQ_MODEL": settings.groq_model,
        "MONGO_URI": settings.mongo_uri,
        "MONGO_DB": settings.mongo_db,
    }
    if npc_collection is not None:
        
        try:
            npcs = list(npc_collection.find({}, {"_id": 0, "name": 1}))
            npc_names = [npc["name"] for npc in npcs]
        except Exception as e:
            print(f"Error fetching NPCs: {e}")
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "npc_names": npc_names,
            "env": env_vars
        }
    )



@app.post("/chat")
async def chat(prompt: str = Form(...)):
    """Send a chat prompt to the QA service and return its JSON result."""
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post("http://localhost:8000/api/v1/qa/qa", json={"question": prompt}, timeout=15)
            return JSONResponse(content=response.json())
        except Exception as e:
            return JSONResponse(content={"error": str(e)}, status_code=500)

@app.post("/reset_chat")
async def reset_chat():
    """Clear the in-memory chat context and acknowledge success."""
    context_cache.clear()
    return JSONResponse(content={"status": "ok"})

 
@app.get("/npcs")
def get_npcs():
    """Return a JSON list of NPC names stored in MongoDB (if available)."""
    npc_names = []
    if npc_collection is not None:
        try:
            npcs = list(npc_collection.find({}, {"_id": 0, "name": 1}))
            npc_names = [npc["name"] for npc in npcs]
        except Exception as e:
            print(f"Error fetching NPCs: {e}")
    return JSONResponse(content={"npc_names": npc_names})


@app.post("/upload_story")
async def upload_story(file: UploadFile = File(...)):
    """Persist an uploaded markdown file as ``App/Data/fantasy.md``."""
    dest_dir = get_data_dir()
    dest_dir.mkdir(parents=True, exist_ok=True)  # na wszelki wypadek
    dest = dest_dir / "fantasy.md"

    with dest.open("wb") as f:
        shutil.copyfileobj(file.file, f)

    return {"status": f"File {file.filename} saved  as {dest.name}"}



