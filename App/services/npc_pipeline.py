# services/npc_pipeline.py
from __future__ import annotations

from bson import ObjectId
from core.llm import chat_json
from core.prompts import NPC_SYSTEM, NPC_USER_TEMPLATE
from core.rag import FaissRAG
from Config.config import settings
from core.validation import validate_npcs
import time, random, string
from services.utility import generate_session_id
from db.database import db, save_npcs_to_mongo , existing_names
from copy import deepcopy

class NPCPipeline:
    def __init__(self, store: FaissRAG | None = None):
        self.store = store or FaissRAG(
            index_path=settings.faiss_path
        )
        if not hasattr(self.store, "load"):
            raise RuntimeError("FAISS store missing load method. Check implementation.")
        self.store.load()
        self.npc_collection = db.npc_collection

    
    def generate(self, prompt: str | None, session_id: str | None = None) -> list[dict]:
        # Jeśli brak session_id, generujemy nowy
        session_id = session_id or generate_session_id()
        print("Generating NPCs with session ID:", session_id)
        print("Prompt:", prompt)
        seed = prompt or "setting"
        try:
            ctx = self.store.search(seed, k=getattr(settings, "rag_top_k", 4))
        except Exception:
            ctx = [] 
        context_str = "\n---\n".join([f"{cid}: {txt}" for cid, txt in ctx])

        #avoid = list(self.registry.existing())
        avoid = existing_names()
        print(f"Existing NPC names to avoid: {avoid}")
        user = NPC_USER_TEMPLATE.format(
            context=context_str,
            prompt=prompt or "",
            avoid=avoid,
        )
        print(f"NPC Generation prompt:\n{user}")
        # Przekazanie session_id do chat_json
        npcs = chat_json(system=NPC_SYSTEM, user=user, session_id=session_id)

        if not isinstance(npcs, list):
            npcs = [npcs]
        npcs = validate_npcs(npcs)
        return self._enforce_uniqueness(npcs, context_str)

    
    def _enforce_uniqueness(self, npcs: list[dict], context_str: str) -> list[dict]:
        npc_database_names = set(existing_names())
        cleaned_npcs = []
        for npc in npcs:
            name = npc.get("name", "")
            print(f"Checking NPC name for uniqueness: {name}")
            print(f"Current DB names: {npc_database_names}")
            npc = deepcopy(npc)
            if name in npc_database_names:  
                print(f"Name conflict detected: {name}. Generating alternative.")
                alt = chat_json(
                    system="You rename a character keeping style and lore; output JSON {\"name\": \"...\"} only.",
                    user=f"\nAVOID:{npc_database_names}\nORIGINAL:{name}",session_id=generate_session_id()
                )
                print(alt)
                if isinstance(alt, dict) and "name" in alt:
                    npc["name"] = alt["name"]
            npc.pop("_id", None)
            cleaned_npcs.append(npc)
        save_npcs_to_mongo(npcs)
        return cleaned_npcs