from motor.motor_asyncio import AsyncIOMotorClient
from Config.config import settings


_client: AsyncIOMotorClient | None = None


def get_client() -> AsyncIOMotorClient:
    global _client
    if _client is None:
        _client = AsyncIOMotorClient(settings.mongo_uri)
    return _client


async def get_db():
    return get_client()[settings.mongo_db]


async def ensure_indexes(db):
    await db["npcs"].create_index("name", unique=True)
    await db["npcs"].create_index([("personality", 1), ("mood", 1)])
    await db["npcs"].create_index("knowledge_tags") # multikey
    await db["npcs"].create_index("updated_at")


    await db["interactions"].create_index([("npc_id", 1), ("timestamp", -1)])