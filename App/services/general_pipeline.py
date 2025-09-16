# services/general_pipeline.py
# General pipeline that routes between NPC generation and QA based on user input.
# Uses a classification prompt to determine the intent of the query.
# Routes to the appropriate sub-pipeline (NPC or QA) accordingly.
# Combines context from RAG and cached previous interactions for better responses.
from core.rag import FaissRAG

from services.npc_pipeline import NPCPipeline
from services.qa_pipeline import QAPipeline
from Config.config import settings
from core.llm import chat_json
import time, random, string
import logging
from core.prompts import CLASSIFICATION_SYSTEM
def generate_session_id() -> str:
    timestamp = int(time.time() * 1000)
    suffix = ''.join(random.choices(string.ascii_letters + string.digits, k=8))
    return f"{timestamp}_{suffix}"



class GeneralPipeline:
    def __init__(self):
        self.npc_pipeline = NPCPipeline(FaissRAG(index_path=settings.faiss_path))
        self.qa_pipeline = QAPipeline(FaissRAG(index_path=settings.faiss_path))  
    def process(self, query: str):
        logging.info(f"Processing query: {query} ")

        
        # --- Classification Prompt ---
        classification_prompt = CLASSIFICATION_SYSTEM + f"\n:\n{query}\n\nRespond with JSON."

        cls_result = "QA"  

        try:
            logging.info("Sending classification prompt to LLM")
            cls_resp = chat_json(
                system="You are a classifier",
                user=classification_prompt,
                session_id=generate_session_id()
            )
            logging.info(f"Classifier response: {cls_resp}")
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
                print("Classifier returned None – fallback to QA")
            else:
                print(f"Unrecognized classifier response type: {type(cls_resp)}")

        except Exception as e:
            print(f"Error during classification: {e} – fallback to QA")

        print(f"Final classification result: {cls_result}")

        # --- Routing ---
        logging.info(f"Routing to pipeline based on classification: {cls_result}")
        if cls_result == "NPC":
                logging.info("Routing to NPC pipeline")
                return self.npc_pipeline.generate(prompt=query)
        elif cls_result == "QA":
            logging.info("Routing to QA pipeline")
            return self.qa_pipeline.answer(question=query)
        else:
            logging.info("Classification unclear, defaulting to QA pipeline")
            return self.qa_pipeline.answer(question=query)