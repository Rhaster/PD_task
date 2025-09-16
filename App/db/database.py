# db/database.py
# Database connection and operations for NPC management.
# Sets up MongoDB connection and collections.
# Provides functions to save NPCs and retrieve existing NPC names.
from Config.config import settings
from pymongo import MongoClient
import os
from dotenv import load_dotenv
load_dotenv()
import logging
# --- konfiguracja MongoDB ---
try:
    MONGO_URL= os.getenv("MONGO_URI", "mongodb://localhost:27017")
    MONGO_DB = os.getenv("MONGO_DB", "npc_system_db")
    mongo = MongoClient(MONGO_URL)
    db = mongo[MONGO_DB]
    sessions = db["chat_sessions"]
    npc_collection = db["npcs"]
except Exception as e:
    logging.error(f"Nie można połączyć się z MongoDB: {e}")
    db = None
    sessions = None
    npc_collection = None

def save_npcs_to_mongo(npcs: list[dict]) -> list[str]:
    if not npcs:
        return []
    result = npc_collection.insert_many(npcs)
    return [str(_id) for _id in result.inserted_ids]


def existing_names() -> list[str]:
    return [doc["name"] for doc in npc_collection.find({}, {"_id": 0, "name": 1})]


