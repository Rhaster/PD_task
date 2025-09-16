"""MongoDB connection and helpers for NPC storage and chat sessions."""
from App.Config.config import settings
from pymongo import MongoClient
import os
from dotenv import load_dotenv
load_dotenv()
from App.Services.utility import logging_function

try:
    MONGO_URL= os.getenv("MONGO_URI", "mongodb://localhost:27017")
    MONGO_DB = os.getenv("MONGO_DB", "npc_system_db")
    mongo = MongoClient(MONGO_URL)
    db = mongo[MONGO_DB]
    sessions = db["chat_sessions"]
    npc_collection = db["npcs"]
except Exception as e:
    logging_function(f"Cannot connect to MongoDB: {e}", level="error")
    db = None
    sessions = None
    npc_collection = None

def save_npcs_to_mongo(npcs: list[dict]) -> list[str]:
    """Insert NPC documents and return inserted ID strings."""
    logging_function(f"Saving {len(npcs)} NPCs to MongoDB", level="info")
    if not npcs:
        return []
    result = npc_collection.insert_many(npcs)
    return [str(_id) for _id in result.inserted_ids]


def existing_names() -> list[str]:
    """Fetch all existing NPC names from the database."""
    return [doc["name"] for doc in npc_collection.find({}, {"_id": 0, "name": 1})]




