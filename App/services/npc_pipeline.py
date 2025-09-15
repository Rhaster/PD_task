# services/npc_pipeline.py
from __future__ import annotations
from core.llm import chat_json
from core.prompts import NPC_SYSTEM, NPC_USER_TEMPLATE
from core.rag import FaissRAG
from Config.config import settings
from core.validation import validate_npcs
from core.registry import InMemoryNameRegistry  # prosty rejestr in-memory
import time, random, string
from services.utility import generate_session_id

class NPCPipeline:
    def __init__(self, store: FaissRAG | None = None):
        self.store = store or FaissRAG(
            index_path=settings.faiss_path
        )
        if not hasattr(self.store, "load"):
            raise RuntimeError("FAISS store missing load method. Check implementation.")
        self.store.load()
        self.registry = InMemoryNameRegistry()  # prosty rejestr in-memory

    def generate(self, prompt: str | None, count: int, constraints: dict | None, session_id: str | None = None) -> list[dict]:
        # Jeśli brak session_id, generujemy nowy
        session_id = session_id or generate_session_id()

        seed = prompt or "setting"
        try:
            ctx = self.store.search(seed, k=getattr(settings, "rag_top_k", 4))
        except Exception:
            ctx = []  # fallback, jeśli FAISS niedostępny
        context_str = "\n---\n".join([f"{cid}: {txt}" for cid, txt in ctx])

        avoid = list(self.registry.existing())

        user = NPC_USER_TEMPLATE.format(
            context=context_str,
            prompt=prompt or "",
            constraints=constraints or {},
            avoid=avoid,
        )

        # Przekazanie session_id do chat_json
        npcs = chat_json(system=NPC_SYSTEM, user=user, session_id=session_id, n=count)

        if not isinstance(npcs, list):
            npcs = [npcs]
        npcs = validate_npcs(npcs)
        return self._enforce_uniqueness(npcs, context_str)

    def _enforce_uniqueness(self, npcs: list[dict], context_str: str) -> list[dict]:
        out: list[dict] = []
        for npc in npcs:
            name = npc.get("name", "")
            if self.registry.exists(name):
                alt = chat_json(
                    system="You rename a character keeping style and lore; output JSON {\"name\": \"...\"} only.",
                    user=f"CONTEXT:\n{context_str}\nAVOID:{list(self.registry.existing())}\nORIGINAL:{name}",
                )
                if isinstance(alt, dict) and "name" in alt:
                    npc["name"] = alt["name"]
            self.registry.add(npc["name"])
            out.append(npc)
        return out
