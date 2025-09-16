""" Tests for Services/general_pipeline.py """


import pytest
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent.parent)) 

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
from types import SimpleNamespace
from unittest.mock import Mock


from App.Services.general_pipeline import GeneralPipeline


def make_gp_with_pipelines(npc_ret=None, qa_ret=None, classifier_resp=None, monkeypatch=None):
    """Helper to create a GeneralPipeline with mocked sub-pipelines and classifier."""
    if monkeypatch is not None:
        monkeypatch.setattr("Services.general_pipeline.chat_json", lambda **kwargs: classifier_resp)

    gp = GeneralPipeline.__new__(GeneralPipeline)
    gp.npc_pipeline = SimpleNamespace(generate=lambda prompt, amount=None: npc_ret)
    gp.qa_pipeline = SimpleNamespace(answer=lambda question: qa_ret)
    return gp

def test_process_routes_to_npc_when_classifier_returns_type(monkeypatch):
    """ Test routing to NPC pipeline when classifier returns {'type': 'NPC'}. """
    gp = make_gp_with_pipelines(npc_ret={"npc": "ok"}, qa_ret={"answer": "no"}, classifier_resp={"type": "NPC"}, monkeypatch=monkeypatch)
    result = gp.process("generate npc")
    assert result == {"npc": "ok"}


def test_process_routes_to_qa_when_classifier_returns_string(monkeypatch):
    """ Test routing to QA pipeline when classifier returns "QA". """
    gp = make_gp_with_pipelines(npc_ret={"npc": "no"}, qa_ret={"answer": "ok"}, classifier_resp="qa", monkeypatch=monkeypatch)
    result = gp.process("ask question")
    assert result == {"answer": "ok"}


def test_process_defaults_to_qa_when_classifier_none(monkeypatch):
    """ Test default routing to QA pipeline when classifier returns None. """
    gp = make_gp_with_pipelines(npc_ret={"npc": "no"}, qa_ret={"answer": "ok"}, classifier_resp=None, monkeypatch=monkeypatch)
    result = gp.process("ambiguous")
    assert result == {"answer": "ok"}
