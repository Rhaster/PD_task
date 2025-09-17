
"""Routing pipeline that delegates queries to NPC or QA handlers.

The general pipeline performs a lightweight classification using the LLM and
then forwards the request to either the NPC generation pipeline or the QA
pipeline. It is intentionally conservative and defaults to QA when the
classification is ambiguous.
"""
from App.Core.rag import FaissRAG
from App.Services.utility import generate_session_id, logging_function
from App.Services.npc_pipeline import NPCPipeline
from App.Services.qa_pipeline import QAPipeline
from App.Config.config import settings
from App.Core.llm import chat_json
from groq import BadRequestError
import logging
from App.Core.prompts import CLASSIFICATION_SYSTEM
from App.Services.utility import handle_bad_request_error
import re


class GeneralPipeline:
    """High-level router between the NPC and QA pipelines."""

    def __init__(self):
        """Initialize sub-pipelines, sharing a FAISS-backed RAG store."""
        self.npc_pipeline = NPCPipeline(FaissRAG(index_path=settings.faiss_path))
        self.qa_pipeline = QAPipeline(FaissRAG(index_path=settings.faiss_path))  
    def sanitize_query(self, query: str) -> str:
        """Check prompt for forbitten content"""
        if not isinstance(query, str):
            return ""
        query = query.strip()[:2000]
        query = re.sub(r"(?:<\s*/?\s*system\s*>|\bSYSTEM:)", "", query, flags=re.IGNORECASE)
        return query

    def process(self, query: str):
        """Classify ``query`` and dispatch to the appropriate pipeline."""
        logging_function(f"Processing query: {query} ", level="info")

        query = self.sanitize_query(query)
        if not query.strip():
                logging_function("Empty query received, returning safe fallback", level="warning")
                return {
                "status": "error",
                "message": "Your query was empty. Please provide a valid question or prompt."
                }
        classification_prompt = CLASSIFICATION_SYSTEM + f"\n:\n{query}\n\nRespond with JSON."

        cls_result = "QA"  
        try:
            logging_function("Sending classification prompt to LLM", level="info")
            cls_resp = chat_json(
                system="You are a classifier",
                user=classification_prompt,
                session_id=generate_session_id()
            )
            logging_function(f"Classifier response: {cls_resp}", level="info")
            if isinstance(cls_resp, dict):
                if "type" in cls_resp and isinstance(cls_resp["type"], str):
                    cls_result = cls_resp["type"].strip().upper()
                elif len(cls_resp) == 1:
                    first_val = list(cls_resp.values())[0]
                    if isinstance(first_val, str):
                        cls_result = first_val.strip().upper()
            elif isinstance(cls_resp, list) and len(cls_resp) > 0:
                first_val = cls_resp[0]
                if isinstance(first_val, str):
                    cls_result = first_val.strip().upper()
                elif isinstance(first_val, dict) and "type" in first_val:
                    cls_result = str(first_val["type"]).strip().upper()
            elif isinstance(cls_resp, str):
                cls_result = cls_resp.strip().upper()
            elif cls_resp is None:
                logging_function("Classifier returned None, defaulting to QA", level="warning")
            else:
                logging_function("Unexpected classifier response format, defaulting to QA", level="warning")
        except BadRequestError as e:
            handle_bad_request_error(e, logging_function=logging_function)
            logging_function("Defaulting to QA pipeline due to classification BadRequestError", level="info")
        except Exception as e:
            logging_function(f"Error during classification: {e}", level="error")
            logging_function("Defaulting to QA pipeline due to classification error", level="info")
        logging_function(f"Classification result: {cls_result}", level="info")
        logging_function(f"Routing to pipeline based on classification: {cls_result}", level="info")
        
        if cls_result == "NPC":
                logging_function("Routing to NPC pipeline", level="info")
                amount = 1  
                if isinstance(cls_resp, dict) and cls_resp.get("amount") is not None:
                    try:
                        amount = int(cls_resp.get("amount"))
                    except ValueError:
                        logging.warning(f"Invalid amount value: {cls_resp.get('amount')}, using default 1")
                return self.npc_pipeline.generate(prompt=query, amount=amount)
        elif cls_result == "QA":
            logging_function("Routing to QA pipeline", level="info")
            return self.qa_pipeline.answer(question=query)
        else:
            logging_function("Classification unclear, defaulting to QA pipeline", level="info")
            return self.qa_pipeline.answer(question=query)