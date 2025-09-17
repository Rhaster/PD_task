"""
Pytest suite for NPCPipeline: validates normalization, defaults filling, collisions/renames, top-up generation, persistence, and absence of Mongo ObjectId leaks. The tests mock all external dependencies (RAG, LLM, DB, cache) and avoid heuristics.
"""

import uuid
import pytest

import App.Services.npc_pipeline as npc_module
from App.Services.npc_pipeline import NPCPipeline


def make_valid_npc(name: str, profession: str = "Blacksmith", faction: str = "Unaffiliated"):
    return {
        "name": name,
        "profession": profession,
        "faction": faction,
        "personality_traits": ["reserved", "practical"],
        "notes": "",
    }


class DummyStore:
    def load(self):
        """ No-op FAISS loader replacement. """
        pass

    def search(self, seed: str, k: int = 4):
        """ Returns fixed fake context tuples. """
        return [("ctx1", "lore1"), ("ctx2", "lore2")]


class DummyCache:
    def __init__(self):
        """ Initializes in-memory cache for context. """
        self._data = {}
        self._last_add = None

    def all(self):
      
        return dict(self._data)

    def add(self, key, val):
        
        self._last_add = (key, val)
        self._data[key] = val


@pytest.fixture(autouse=True)
def patch_common(monkeypatch):
    """ Patches common externals: FAISS, existing names, persistence, and cache. """
    monkeypatch.setattr(npc_module, "FaissRAG", lambda index_path=None: DummyStore())
    monkeypatch.setattr(npc_module, "existing_names", lambda: [])

    saved = {"docs": None}

    def fake_save(docs):
        saved["docs"] = docs
        return [str(uuid.uuid4()) for _ in docs]

    monkeypatch.setattr(npc_module, "save_npcs_to_mongo", fake_save)
    monkeypatch.setattr(npc_module, "context_cache", DummyCache())
    yield


def test_normalize_to_list_variants():
    """ Ensures various model shapes are normalized to a list of dicts. """
    p = NPCPipeline(store=DummyStore())
    assert p._normalize_to_list([{"a": 1}]) == [{"a": 1}]
    assert p._normalize_to_list({"items": [{"a": 1}, {"b": 2}]}) == [{"a": 1}, {"b": 2}]
    assert p._normalize_to_list({"npcs": [{"x": 1}]}) == [{"x": 1}]
    assert p._normalize_to_list({"data": [{"y": 1}]}) == [{"y": 1}]
    assert p._normalize_to_list({"results": [{"z": 1}]}) == [{"z": 1}]
    assert p._normalize_to_list({"a": 1}) == [{"a": 1}]
    assert p._normalize_to_list("oops") == []


def test_coerce_minimal_defaults_fills_fields():
    """ Ensures minimal defaults are populated to meet schema requirements.  """
    p = NPCPipeline(store=DummyStore())
    npc = p._coerce_minimal_defaults({})
    assert npc["name"].startswith("NPC_")
    assert npc["profession"] == "Commoner"
    assert npc["faction"] == "Unaffiliated"
    assert npc["personality_traits"] and isinstance(npc["personality_traits"], list)
    assert npc["notes"] == ""


def test_generate_happy_path_exact_amount(monkeypatch):
    """ Verifies exact AMOUNT is returned when LLM yields enough valid NPCs. """
    amount = 3
    out = [make_valid_npc(f"Name{i}") for i in range(amount)]

    def fake_chat_json(system, user, session_id=None, temperature=None):
        return out

    monkeypatch.setattr(npc_module, "chat_json", fake_chat_json)

    p = NPCPipeline(store=DummyStore())
    res = p.generate(prompt="anything", amount=amount)

    assert len(res) == amount
    assert [r["name"] for r in res] == [f"Name{i}" for i in range(amount)]
    assert all("_id" not in r for r in res)


def test_generate_top_up_when_underfilled(monkeypatch):
    """ Ensures top-up logic fills missing NPCs to reach AMOUNT. """
    initial = [make_valid_npc(f"Init{i}") for i in range(4)]
    missing_n = 11
    topup = [make_valid_npc(f"Top{i}") for i in range(missing_n)]

    def fake_chat_json(system, user, session_id=None, temperature=None):
        
        return initial

    monkeypatch.setattr(npc_module, "chat_json", fake_chat_json)

    called = {"args": None}

    def fake_top_up(self, missing, full_context, avoid):
        
        called["args"] = (missing, full_context, set(avoid))
        return topup

    monkeypatch.setattr(NPCPipeline, "_top_up_missing", fake_top_up)

    p = NPCPipeline(store=DummyStore())
    res = p.generate(prompt="gimme 15", amount=15)

    assert len(res) == 15
    assert called["args"][0] == 11
    assert all("_id" not in doc for doc in res)


def test_rename_collision_resolved(monkeypatch):
    """ Verifies collisions are resolved by renaming through the LLM helper. """
    initial = [make_valid_npc("Dup"), make_valid_npc("Dup")]

    def fake_chat_json(system, user, session_id=None, temperature=None):
       
        return initial

    def fake_rename(self, originals, avoid, want_total=None):
        
        return ["NewName"]

    monkeypatch.setattr(npc_module, "chat_json", fake_chat_json)
    monkeypatch.setattr(NPCPipeline, "_rename_batch", fake_rename)

    p = NPCPipeline(store=DummyStore())
    res = p.generate(prompt="prompt", amount=2)
    names = sorted(r["name"] for r in res)
    assert names == ["Dup", "NewName"]


def test_rename_failure_fallback(monkeypatch):
    """ Ensures fallback naming is used when rename attempts fail. """
    initial = [make_valid_npc("Same"), make_valid_npc("Same")]

    def fake_chat_json(system, user, session_id=None, temperature=None):
        
        return initial

    def fake_rename(self, originals, avoid, want_total=None):
        
        return []

    monkeypatch.setattr(npc_module, "chat_json", fake_chat_json)
    monkeypatch.setattr(NPCPipeline, "_rename_batch", fake_rename)

    p = NPCPipeline(store=DummyStore())
    res = p.generate(prompt="prompt", amount=2)
    names = [r["name"] for r in res]
    assert "Same" in names
    assert any(n.startswith("NPC_") for n in names)


def test_no_objectid_leak_and_id_strs(monkeypatch):
    """ Verifies no _id/ObjectId leaks into persisted or returned documents. """
    initial = [dict(make_valid_npc("A"), _id="XYZ"), dict(make_valid_npc("B"), _id="XYZ2")]

    def fake_chat_json(system, user, session_id=None, temperature=None):
        
        return initial

    captured = {"docs": None}

    def fake_save(docs):
        
        captured["docs"] = docs
        return ["1", "2"]

    monkeypatch.setattr(npc_module, "chat_json", fake_chat_json)
    monkeypatch.setattr(npc_module, "save_npcs_to_mongo", fake_save)

    p = NPCPipeline(store=DummyStore())
    res = p.generate(prompt="prompt", amount=2)

    assert captured["docs"] is not None
    assert all("_id" not in d for d in captured["docs"])
    assert all("_id" not in d for d in res)


def test_not_enough_npcs_raises(monkeypatch):
    """ Ensures ValueError is raised when generation and top-up both fail. """
    def fake_chat_json(system, user, session_id=None, temperature=None):
        
        return []

    def fake_top_up(self, missing, full_context, avoid):

        return []

    monkeypatch.setattr(npc_module, "chat_json", fake_chat_json)
    monkeypatch.setattr(NPCPipeline, "_top_up_missing", fake_top_up)

    p = NPCPipeline(store=DummyStore())
    with pytest.raises(ValueError):
        p.generate(prompt="need 5", amount=5)
