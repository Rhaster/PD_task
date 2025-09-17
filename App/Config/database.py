"""MongoDB connection and helpers for NPC storage and chat sessions."""
from App.Config.config import settings
from pymongo import MongoClient
from typing import List, Dict, Any
from pymongo.errors import BulkWriteError
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

def save_npcs_to_mongo(npcs: List[Dict[str, Any]]) -> List[str]:
    """Insert NPC documents and return inserted ID strings."""
    logging_function(f"Saving {len(npcs)} NPCs to MongoDB", level="info")
    if not npcs:
        return []

    docs: List[Dict[str, Any]] = []
    for i, doc in enumerate(npcs):
        if not isinstance(doc, dict):
            logging_function(f"Skipping non-dict NPC at index {i}: {type(doc)}", level="warning")
            continue
        d = dict(doc)
        d.pop("_id", None)
        docs.append(d)
    if not docs:
        return []
    try:
        result = npc_collection.insert_many(docs, ordered=False)
        ids = [str(_id) for _id in result.inserted_ids]
        if len(ids) != len(docs):
            logging_function(
                f"Inserted {len(ids)}/{len(docs)} NPCs (some may have failed).",
                level="warning"
            )
        return ids
    except BulkWriteError as e:
        logging_function(f"BulkWriteError during NPC insert: {e.details}", level="error")
        raise
    except Exception as e:
        logging_function(f"Unexpected error inserting NPCs: {e}", level="error")
        raise


def existing_names() -> list[str]:
    """Fetch all existing NPC names from the database."""
    return [doc["name"] for doc in npc_collection.find({}, {"_id": 0, "name": 1})]




