"""NPC generation pipeline and post-processing utilities.

Retrieves context, calls the LLM, validates & deduplicates NPCs, tops up to AMOUNT,
and persists to MongoDB. No heuristics (no story/faction guessing).
"""
from __future__ import annotations

import uuid
import time
from copy import deepcopy
from typing import Any, Iterable, List

from pydantic import ValidationError
from groq import BadRequestError

from App.Models.query_npc import NPC, NPCAmount
from App.Core.llm import chat_json
from App.Core.prompts import NPC_SYSTEM, NPC_USER_TEMPLATE
from App.Core.rag import FaissRAG
from App.Config.config import settings
from App.Services.utility import generate_session_id, logging_function, handle_bad_request_error
from App.Config.database import db, save_npcs_to_mongo, existing_names
from App.Core.context_cache import context_cache


class NPCPipeline:
    """Create and clean up NPC proposals using an LLM with optional RAG context."""

    def __init__(self, store: FaissRAG | None = None):
        self.store = store or FaissRAG(index_path=settings.faiss_path)
        if not hasattr(self.store, "load"):
            raise RuntimeError("FAISS store missing load() method. Check implementation.")
        self.store.load()

        self.npc_collection = db.npc_collection
        self.MAX_ATTEMPTS = 3        
        self.retry_delay_sec = 4     


    def generate(self, prompt: str | None, session_id: str | None = None, amount: int | None = None) -> list[dict]:
        """Generate a list of NPCs based on the given prompt and desired amount."""
        session_id = session_id or generate_session_id()
        logging_function(
            f"Generating NPCs with prompt: '{prompt}' (session: {session_id}, amount: {amount})",
            level="info"
        )
        seed = prompt or "setting"
        try:
            logging_function(f"Searching RAG store with seed: '{seed}'", level="info")
            ctx = self.store.search(seed, k=getattr(settings, "rag_top_k", 4))
        except Exception as e:
            logging_function(f"Error searching RAG store: {e}", level="error")
            ctx = []

        context_str = "\n---\n".join([f"{cid}: {txt}" for cid, txt in ctx])
        cache_context = "\n".join([f"{q}: {a}" for q, a in context_cache.all().items()])
        full_context = context_str + (("\n---\n" + cache_context) if cache_context else "")

        avoid_names = existing_names()
        user_prompt = NPC_USER_TEMPLATE.format(
            context=full_context,
            prompt=prompt or "",
            avoid=avoid_names,
            amount=amount
        )
        logging_function("NPC generation user prompt prepared.", level="debug")

        try:
            raw = chat_json(system=NPC_SYSTEM, user=user_prompt, session_id=session_id, temperature=0.2)
        except BadRequestError as e:
            handle_bad_request_error(e, logging_function=logging_function)
            raw = []

        npcs_initial = self._normalize_to_list(raw)

        amount_req = amount or (len(npcs_initial) or 6)
        result = self._enforce_uniqueness(
            prompt=prompt or "",
            npcs=npcs_initial,
            amount=amount_req,
            full_context=full_context
        )
        return result


    def _normalize_to_list(self, payload: Any) -> list[dict]:
        """Accept model response as either a plain array or an object with 'items'."""
        if isinstance(payload, list):
            return payload
        if isinstance(payload, dict):
            for key in ("items", "npcs", "data", "results"):
                if key in payload and isinstance(payload[key], list):
                    return payload[key]
            return [payload]
        return []

    def _coerce_minimal_defaults(self, npc: dict, fallback_faction: str | None = None) -> dict:
        """Fill minimal defaults to satisfy the NPC schema (no heuristics)."""
        npc = dict(npc or {})
        npc.pop("_id", None)

        name = str(npc.get("name") or "").strip()
        profession = str(npc.get("profession") or "").strip()
        traits = npc.get("personality_traits")
        faction = npc.get("faction")
        notes = npc.get("notes", None)

        if not name:
            name = f"NPC_{uuid.uuid4().hex[:6]}"
        if not profession:
            profession = "Commoner"
        if not isinstance(traits, list) or not traits:
            traits = ["reserved", "practical"]

        # W modelu NPC `faction` powinno być str (nie None) – bez zgadywania.
        if not isinstance(faction, str) or not faction.strip():
            faction = fallback_faction or "Unaffiliated"
        else:
            faction = faction.strip()

        if notes is None:
            notes = ""

        npc["name"] = name
        npc["profession"] = profession
        npc["personality_traits"] = traits
        npc["faction"] = faction
        npc["notes"] = notes
        return npc

    def _rename_batch(self, originals: list[str], avoid: Iterable[str], want_total: int | None = None) -> list[str]:
        """Ask LLM to propose replacement names. Returns a list of new names."""
        extra = f" Also, if necessary, provide additional names to reach ~{want_total} total." if want_total else ""
        system_prompt = (
            'You rename character names keeping style and lore; '
            'Return a JSON OBJECT with key "items" holding an array of {"name": "..."} objects.'
            + extra
        )
        user_content = f"\nAVOID: {list(avoid)}\nORIGINAL: {originals}"
        try:
            resp = chat_json(system=system_prompt, user=user_content, session_id=generate_session_id(), temperature=0.1)
        except BadRequestError as e:
            handle_bad_request_error(e, logging_function=logging_function)
            return []

        items = self._normalize_to_list(resp)
        names: list[str] = []
        for it in items:
            if isinstance(it, dict) and "name" in it and isinstance(it["name"], str):
                names.append(it["name"].strip().strip('"').strip("'"))
            elif isinstance(it, str):
                names.append(it.strip().strip('"').strip("'"))
        return names

    def _top_up_missing(self, missing: int, full_context: str, avoid: set[str]) -> list[dict]:
        """Generate additional NPCs to reach the requested amount (neutral, no hints)."""
        user = (
            f"CONTEXT:\n{full_context}\n\nUSER_REQUEST:\n"
            f"Generate {missing} NPCs\n\n"
            f"AVOID_NAMES:{list(avoid)}\nAMOUNT:{missing}\n"
            "Return JSON OBJECT: {\"items\": [NPC,...]} with EXACTLY AMOUNT items."
        )
        system = (
            'You generate unique, lore-appropriate NPCs based on CONTEXT and USER_REQUEST. '
            'Return JSON OBJECT with key "items", value is an array of NPC objects. '
            'Each NPC MUST match schema: [{"name":str,"profession":str,"personality_traits":[str],"faction":str,"notes":str|null}]. '
            'Names MUST be unique and NOT in AVOID_NAMES. Keep outputs compact.'
        )
        try:
            resp = chat_json(system=system, user=user, session_id=generate_session_id(), temperature=0.2)
        except BadRequestError as e:
            handle_bad_request_error(e, logging_function=logging_function)
            return []
        return self._normalize_to_list(resp)


    def _enforce_uniqueness(
        self,
        prompt: str,
        npcs: list[dict],
        amount: int,
        full_context: str,
    ) -> list[dict]:
        """Ensure unique names, validate NPCs, and top-up to `amount` if needed."""
        logging_function("Enforcing uniqueness of NPC names and validating NPC data...", level="info")

        existing_db = set(existing_names())
        used_names = set(existing_db)

        cleaned_npcs: list[dict] = []
        colliding: list[dict] = []

        for raw in npcs:
            npc_data = self._coerce_minimal_defaults(raw)
            name = npc_data["name"]
            if not name or name in used_names:
                colliding.append(npc_data)
                continue
            try:
                NPC(**npc_data)
                cleaned_npcs.append(npc_data)
                used_names.add(name)
                logging_function(f"Validating uniqueness of name: {name}", level="debug")
            except ValidationError as ve:
                logging_function(f"Validation error for NPC '{name}': {ve.errors()}", level="warning")
                colliding.append(npc_data)

        attempts = 0
        while colliding and attempts < self.MAX_ATTEMPTS:
            attempts += 1
            originals = [c.get("name") or "<no_name>" for c in colliding]
            logging_function(f"Attempt {attempts}: resolving name collisions for {originals}", level="info")

            new_names = self._rename_batch(originals, avoid=used_names, want_total=amount)
            if not new_names:
                break

            new_colliding: list[dict] = []
            for npc_data, new_name in zip(colliding, new_names):
                npc_copy = self._coerce_minimal_defaults(npc_data)
                candidate = (new_name or "").strip().strip('"').strip("'")
                if not candidate or candidate in used_names:
                    new_colliding.append(npc_copy)
                    continue
                npc_copy["name"] = candidate
                try:
                    NPC(**npc_copy)
                    cleaned_npcs.append(npc_copy)
                    used_names.add(candidate)
                except ValidationError as ve:
                    logging_function(f"Renamed NPC invalid '{candidate}': {ve.errors()}", level="error")
                    new_colliding.append(npc_copy)

            colliding = new_colliding
            if colliding:
                time.sleep(self.retry_delay_sec)
        for npc_data in colliding:
            npc_copy = self._coerce_minimal_defaults(npc_data)
            fallback = f"NPC_{uuid.uuid4().hex[:6]}"
            npc_copy["name"] = fallback
            try:
                NPC(**npc_copy)
                cleaned_npcs.append(npc_copy)
                used_names.add(fallback)
                logging_function(f"Fallback name used → '{fallback}'", level="warning")
            except ValidationError as ve:
                logging_function(f"Fallback NPC still invalid, forcing minimal defaults: {ve.errors()}", level="warning")
                npc_min = self._coerce_minimal_defaults({})
                npc_min["name"] = f"NPC_{uuid.uuid4().hex[:6]}"
                cleaned_npcs.append(npc_min)
                used_names.add(npc_min["name"])
        if len(cleaned_npcs) < amount:
            missing = amount - len(cleaned_npcs)
            logging_function(f"Topping up missing NPCs: need {missing} more.", level="info")
            more = self._top_up_missing(missing, full_context, avoid=used_names)
            more_list = self._normalize_to_list(more)

            for raw in more_list:
                npc_data = self._coerce_minimal_defaults(raw)  
                name = npc_data["name"]
                if not name or name in used_names:
                    continue
                try:
                    NPC(**npc_data)
                    cleaned_npcs.append(npc_data)
                    used_names.add(name)
                    logging_function(f"Validating uniqueness of name: {name}", level="debug")
                    if len(cleaned_npcs) >= amount:
                        break
                except ValidationError as ve:
                    logging_function(f"Top-up NPC invalid '{name}': {ve.errors()}", level="warning")

        cleaned_serializable = [dict(n) for n in cleaned_npcs]
        try:
            validated = NPCAmount(npcs=cleaned_serializable, amount=amount)
        except ValidationError as e:
            raise ValueError("Not enough NPCs generated to satisfy the requested amount.") from e
        persistable = [n.model_dump() if hasattr(n, "model_dump") else dict(n) for n in validated.npcs]
        names = [p.get("name") for p in persistable]
        logging_function(f"Final NPC list (count {len(persistable)}): {names}", level="info")
        persistable = [n.model_dump() if hasattr(n, "model_dump") else dict(n) for n in validated.npcs]
        save_npcs_to_mongo(persistable)
        context_cache.add(prompt, f"Generated NPCs: {names}")

        return persistable
