# main.py
# FastAPI application for NPC Generation System.
# Sets up routes, templates, and static files.
# Integrates with MongoDB for NPC storage and retrieval.
# Provides endpoints for chat, resetting chat, uploading stories, and running FAISS conversion.
# Uses Jinja2 for templating and httpx for async HTTP requests.
# CORS middleware for frontend AJAX support.
# Loads environment variables from .env file.
# Includes logging for debugging and monitoring.
# Fetches and displays existing NPC names on the homepage.
# Imports necessary modules and initializes FastAPI app.
# Defines routes for home, chat, reset chat, get NPCs, upload story, and run FAISS conversion.
# Uses context cache for chat history management.
# Handles file uploads and subprocess execution for FAISS conversion.
# Provides JSON responses for API endpoints.
from fastapi import FastAPI, Request, Form,  UploadFile, File
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from pymongo import MongoClient
from services.context_cache import context_cache
import os
from api.routes_general import router as qa_router
import httpx
import shutil, subprocess

load_dotenv()

from db.database import npc_collection 

# FastAPI setup
app = FastAPI(title="Foregamer NPC Generation System", version="0.2.0-hybrid")
app.include_router(qa_router, prefix="/qa", tags=["qa"])
templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")

# CORS do frontend AJAX (jeśli trzeba)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Strona główna
@app.get("/")
def home(request: Request):
    npc_names = []
    if npc_collection is not None:
        
        try:
            npcs = list(npc_collection.find({}, {"_id": 0, "name": 1}))
            npc_names = [npc["name"] for npc in npcs]
        except Exception as e:
            print(f"Błąd przy pobieraniu NPC: {e}")

    env_vars = {
        "APP_ENV": os.getenv("APP_ENV", ""),
        "GROQ_API_KEY": os.getenv("GROQ_API_KEY", ""),
        "GROQ_BASE_URL": os.getenv("GROQ_BASE_URL", ""),
        "GROQ_MODEL": os.getenv("GROQ_MODEL", ""),
        "MONGO_URI": os.getenv("MONGO_URI", ""),
        "MONGO_DB": os.getenv("MONGO_DB", ""),
    }

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
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post("http://localhost:8000/qa/qa", json={"question": prompt}, timeout=15)
            return JSONResponse(content=response.json())
        except Exception as e:
            return JSONResponse(content={"error": str(e)}, status_code=500)
# Reset czatu
@app.post("/reset_chat")
async def reset_chat():
    context_cache.clear()
    return JSONResponse(content={"status": "ok"})

# Endpoint do pobierania listy NPC (dla AJAX)
@app.get("/npcs")
def get_npcs():
    npc_names = []
    if npc_collection is not None:
        try:
            npcs = list(npc_collection.find({}, {"_id": 0, "name": 1}))
            npc_names = [npc["name"] for npc in npcs]
        except Exception as e:
            print(f"Błąd przy pobieraniu NPC: {e}")
    return JSONResponse(content={"npc_names": npc_names})



@app.post("/upload_story")
async def upload_story(file: UploadFile = File(...)):
    path = "fantasy.md"
    with open(path, "wb") as f:
        shutil.copyfileobj(file.file, f)
    return {"status": f"Plik {file.filename} zapisany jako fantasy.md"}

@app.post("/run_faiss")
async def run_faiss():
    try:
        subprocess.run(["python", "faiss_converter.py"], check=True)
        return {"status": "faiss_converter.py uruchomiony pomyślnie"}
    except subprocess.CalledProcessError as e:
        return {"status": f"Błąd uruchamiania skryptu: {e}"}

