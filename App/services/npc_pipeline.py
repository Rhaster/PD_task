"""NPC generation pipeline and post-processing utilities.

This module provides an ``NPCPipeline`` that retrieves context, calls the LLM
to propose characters, validates and de-duplicates results, and finally stores
accepted NPCs in MongoDB.
"""
from __future__ import annotations
from pydantic import ValidationError
from App.Models.query_npc import NPC,NPCAmount
from App.Core.llm import chat_json
from App.Core.prompts import NPC_SYSTEM, NPC_USER_TEMPLATE
from App.Core.rag import FaissRAG
from App.Config.config import settings
from App.Services.utility import generate_session_id, logging_function, handle_bad_request_error
from App.Config.database import db, save_npcs_to_mongo , existing_names
from copy import deepcopy
from groq import BadRequestError
from App.Core.context_cache import context_cache
import uuid
import time
class NPCPipeline:
    """Create and clean up NPC proposals using an LLM and RAG context."""

    def __init__(self, store: FaissRAG | None = None):
        """Initialize with a ``FaissRAG`` store and configure limits."""
        self.store = store or FaissRAG(
            index_path=settings.faiss_path
        )
        if not hasattr(self.store, "load"):
            raise RuntimeError("FAISS store missing load method. Check implementation.")
        self.store.load()
        self.npc_collection = db.npc_collection 
        self.MAX_ATTEMPTS = 3  
        self.retry_delay_sec = 10
    
    def generate(self, prompt: str | None, session_id: str | None = None,amount: int | None = None) -> list[dict]:
        """Generate NPCs from ``prompt`` and return cleaned documents.

        The method ensures names are unique relative to existing database
        entries, and falls back to synthetic names when necessary.
        """
        time.sleep(self.retry_delay_sec)
        session_id = session_id or generate_session_id()
        logging_function(f"Generating NPCs with prompt: {prompt} and session_id: {session_id} and amount { amount}", level="info")
        
        seed = prompt or "setting"
        try:
            logging_function(f"Searching RAG store with seed: {seed}", level="info")
            ctx = self.store.search(seed, k=getattr(settings, "rag_top_k", 4))
        except Exception as e:
            logging_function(f"Error searching RAG store: {e}", level="error")
            ctx = []  
        context_str = "\n---\n".join([f"{cid}: {txt}" for cid, txt in ctx])
        cache_context = "\n".join([f"{q}: {a}" for q, a in context_cache.all().items()])
        full_context = context_str + "\n---\n" + cache_context

     
        avoid = existing_names()
        user = NPC_USER_TEMPLATE.format(
            context=full_context,
            prompt=prompt   or "",
            avoid=avoid,
            amount=amount
        )
        logging_function(f"NPC generation user prompt: {user}", level="debug")
        try:
            npcs = chat_json(system=NPC_SYSTEM, user=user, session_id=session_id)
        except BadRequestError as e:
                handle_bad_request_error(e, logging_function=logging_function)
               
    
        return self._enforce_uniqueness(prompt,npcs,amount)
    def _enforce_uniqueness(self,prompt: str, npcs: list[dict],amount:int) -> list[dict]:
        """Ensure unique names and return a serializable list of NPCs."""
        logging_function("Enforcing uniqueness of NPC names", level="info")
        npc_database_names = set(existing_names())
        cleaned_npcs = []
        colliding_npcs = []
        for npc in npcs:
            npc_copy = deepcopy(npc)
            npc_copy.pop("_id", None) 
            name = npc_copy.get("name", "")

            if not name or name in npc_database_names:
                colliding_npcs.append(npc_copy)
                continue

            try:
                NPC(**npc_copy)  
                cleaned_npcs.append(npc_copy)
                npc_database_names.add(name)
            except ValidationError as ve:
                logging_function(f"Validation error for NPC '{name}': {ve.errors()}", level="warning")
                colliding_npcs.append(npc_copy)

        attempts = 0
        message = " Also if nessesery try to add more npcs to generate. required amount is " + str(amount)
        while colliding_npcs and attempts < self.MAX_ATTEMPTS:
            attempts += 1
            colliding_names = [npc["name"] for npc in colliding_npcs]
            logging_function(f"Attempt {attempts}: fixing NPCs {colliding_names}", level="info")

            try:
                alt = chat_json(
                    system="You rename character names keeping style and lore; output JSON [{\"name\": \"...\"}] only." + message,
                    user=f"\nAVOID:{npc_database_names}\nORIGINAL:{colliding_names}",
                    session_id=generate_session_id(),
                )
                if isinstance(alt, dict):
                    alt = [alt]

                new_colliding = []
                for npc_dict, new_name in zip(colliding_npcs, alt or []):
                    npc_copy = deepcopy(npc_dict)
                    npc_copy.pop("_id", None)  

                    if isinstance(new_name, dict) and "name" in new_name:
                        npc_copy["name"] = new_name["name"].strip('"').strip("'")
                    elif isinstance(new_name, str):
                        npc_copy["name"] = new_name.strip('"').strip("'")

                    if npc_copy["name"] not in npc_database_names:
                        try:
                            NPC(**npc_copy)
                            cleaned_npcs.append(npc_copy)
                            npc_database_names.add(npc_copy["name"])
                        except ValidationError as ve:
                            logging_function(f"Renamed NPC invalid: {npc_copy['name']} {ve.errors()}", level="error")
                            new_colliding.append(npc_copy)
                    else:
                        logging_function(f"Name still collides after rename: {npc_copy['name']}", level="warning")
                        new_colliding.append(npc_copy)
                colliding_npcs = new_colliding
                time.sleep(self.retry_delay_sec) 
            except BadRequestError as e:
                handle_bad_request_error(e, logging_function=logging_function)
                break
            except Exception as e:
                logging_function(f"Error during renaming attempt: {e}", level="error")
                break
        
        for npc_dict in colliding_npcs:
            npc_copy = deepcopy(npc_dict)
            npc_copy.pop("_id", None)

            fallback_name = f"NPC_{uuid.uuid4().hex[:6]}"
            logging_function(f"Fallback name used for NPC {npc_dict.get('name')} → {fallback_name}", level="warning")
            npc_copy["name"] = fallback_name
            cleaned_npcs.append(npc_copy)
            npc_database_names.add(fallback_name)

    
        cleaned_npcs_serializable = []
        for npc in cleaned_npcs:
            npc_copy = npc.copy()
            npc_copy.pop("_id", None)
            cleaned_npcs_serializable.append(npc_copy)

    
        try:
            validated_npcs = NPCAmount(npcs=cleaned_npcs_serializable, amount=amount)
        except ValidationError as e:
            raise ValueError("Not enough NPCs returned from generator") from e
        context_cache.add(prompt, f"Generated NPCs: {validated_npcs.npcs}")
        logging_function(f"Final cleaned NPCs: {validated_npcs.npcs}", level="info")
        save_npcs_to_mongo(cleaned_npcs)
        return validated_npcs.npcs