# services/npc_pipeline.py
# 
# Pipeline used for NPC generation and management.
# 
# def generate_npcs(prompt: str, session_id: str | None = None) -> list[dict]:
#    Generate NPCs based on the provided prompt and optional session ID.
#    If session_id is not provided, a new one is generated.
#     Returns a list of NPC dictionaries.
#     Enforces uniqueness of NPC names against existing database entries.
from __future__ import annotations
import logging
from pydantic import ValidationError
from Models.models import NPC
from core.llm import chat_json
from core.prompts import NPC_SYSTEM, NPC_USER_TEMPLATE
from core.rag import FaissRAG
from Config.config import settings
from services.utility import generate_session_id
from db.database import db, save_npcs_to_mongo , existing_names
from copy import deepcopy
from groq import BadRequestError
from services.context_cache import context_cache
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
        """
        Generate NPCs based on the provided prompt and optional session ID.
        If session_id is not provided, a new one is generated.
        Returns a list of NPC dictionaries.
        Enforces uniqueness of NPC names against existing database entries.
         """
        logging.info(f"Generating NPCs with prompt: {prompt} and session_id: {session_id}")
        session_id = session_id or generate_session_id()
        seed = prompt or "setting"
        try:
            logging.info(f"Searching RAG store with seed: {seed}")
            ctx = self.store.search(seed, k=getattr(settings, "rag_top_k", 4))
        except Exception:
            logging.error("Error searching RAG store", exc_info=True)
            ctx = []  
        context_str = "\n---\n".join([f"{cid}: {txt}" for cid, txt in ctx])
        cache_context = "\n".join([f"{q}: {a}" for q, a in context_cache.all().items()])
        full_context = context_str + "\n---\n" + cache_context

        #avoid = list(self.registry.existing())
        avoid = existing_names()
        user = NPC_USER_TEMPLATE.format(
            context=full_context,
            prompt=prompt or "",
            avoid=avoid,
        )
        logging.info(f"NPC generation user prompt: {user}")
        npcs = chat_json(system=NPC_SYSTEM, user=user, session_id=session_id)
        logging.info(f"Raw NPC generation response: {npcs}")
        if not isinstance(npcs, list):
            npcs = [npcs]
        return _enforce_uniqueness(prompt,npcs)

@staticmethod
def _enforce_uniqueness(prompt : str, npcs: list[dict]) -> list[dict]:
    """
        Ensure NPC names are unique against existing database entries.  
        If duplicates are found, request alternative names from the LLM.
        Returns the cleaned list of NPCs with unique names.
    """
    logging.info("Enforcing uniqueness of NPC names")
    npc_database_names = set(existing_names())
    colliding_npcs_dicts = []
    colliding_names = []
    cleaned_npcs = []

    for npc in npcs:
        name = npc.get("name", "")
    
        npc_copy = deepcopy(npc)  
        try:
            npc_obj = NPC(**npc_copy)
            npc_copy.pop("_id", None)         
            cleaned_npcs.append(npc_copy)
            npc_database_names.add(name)
        except ValidationError as ve:
            logging.warning(f"Validation error for NPC '{name}': {ve.errors()}")
            for err in ve.errors():
                if err['loc'][0] == 'name':

                    colliding_npcs_dicts.append(npc)  
                    colliding_names.append(name)  
                    break
            npc_copy.pop("_id", None)         
            cleaned_npcs.append(npc_copy)
            npc_database_names.add(name)
    try:
        if colliding_npcs_dicts:
            logging.info(f"Found colliding NPC names: {colliding_names}")
            alt = chat_json(
                system="You rename character names keeping style and lore; output JSON [{\"name\": \"...\"}] only.",
                user=f"\nAVOID:{npc_database_names}\nORIGINAL:{colliding_names}",
                session_id=generate_session_id()
            )
            logging.info(f"Alternative names from LLM: {alt}")
            if isinstance(alt, dict):
                alt = [alt]
            if isinstance(alt, list):
                for npc_dict, new_name in zip(colliding_npcs_dicts, alt):
                    if isinstance(new_name, dict) and "name" in new_name:
                        npc_dict["name"] = new_name["name"].strip().strip('"').strip("'")
                    elif isinstance(new_name, str):
                        npc_dict["name"] = new_name.strip().strip('"').strip("'")
                    try:
                        npc_copy = deepcopy(npc_dict)
                        npc_obj = NPC(**npc_dict)
                        npc_copy.pop("_id", None)
                        cleaned_npcs.append(npc_copy)
                        npc_database_names.add(npc_dict["name"])
                    except ValidationError as ve:
                        logging.error(f"Renamed NPC still invalid: {npc_dict['name']} due to { ve.errors() }")
    except BadRequestError as e:
        logging.error(f"BadRequestError when requesting alternative names: {e}")
    logging.info(f"Final cleaned NPCs: {cleaned_npcs}")
    context_cache.add(prompt,f"Generated NPCs: {cleaned_npcs}" )
    print(context_cache.all())
    save_npcs_to_mongo(cleaned_npcs)
    logging.info(f"Saved {len(cleaned_npcs)} NPCs to MongoDB")
    return npcs