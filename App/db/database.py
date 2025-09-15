
from Config.config import settings
from pymongo import MongoClient



# --- konfiguracja MongoDB ---
mongo = MongoClient("mongodb://localhost:27017/")
db = mongo["npc_system_db"]
sessions = db["chat_sessions"]
npc_collection = db["npcs"]



from bson import ObjectId

def save_npcs_to_mongo(npcs: list[dict]) -> list[str]:
    if not npcs:
        return []
    print(f"Saving {len(npcs)} NPCs to MongoDB")
    result = npc_collection.insert_many(npcs)
    return [str(_id) for _id in result.inserted_ids]


def existing_names() -> list[str]:
    return [doc["name"] for doc in npc_collection.find({}, {"_id": 0, "name": 1})]


