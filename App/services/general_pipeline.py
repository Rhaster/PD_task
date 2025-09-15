from core.rag import FaissRAG

from services.npc_pipeline import NPCPipeline
from services.qa_pipeline import QAPipeline
from Config.config import settings
from core.llm import chat_json
import time, random, string
def generate_session_id() -> str:
    """Generuje unikalny session_id w formacie timestamp + losowy sufiks"""
    timestamp = int(time.time() * 1000)
    suffix = ''.join(random.choices(string.ascii_letters + string.digits, k=8))
    return f"{timestamp}_{suffix}"



class GeneralPipeline:
    def __init__(self):
        self.npc_pipeline = NPCPipeline(FaissRAG(index_path=settings.faiss_path))
        self.qa_pipeline = QAPipeline(FaissRAG(index_path=settings.faiss_path))


    def process(self, query: str, npc_threshold: float = 0.5):
        print(f"Processing query: {query}")
        print(f"Using npc_threshold: {npc_threshold}")

        classification_prompt = f"""
        Decide if the following user query is asking to GENERATE NPC or is a QA question.
        Respond ONLY with a JSON object containing a single key 'type' with value 'NPC' or 'QA'. 
        Or 'NONE' if you can't specify.  
        Query: {query}
        """

        cls_result = "QA"  # default value
        try:
            cls_resp = chat_json(
                system="You are a classifier",
                user=classification_prompt,
                session_id=generate_session_id()
            )
            print(f"Raw classification response: {cls_resp}")

            # --- Handle different response types ---
            if isinstance(cls_resp, dict):
                # 1. Dictionary with "type"
                if "type" in cls_resp and isinstance(cls_resp["type"], str):
                    cls_result = cls_resp["type"].strip().upper()
                # 2. Dictionary without "type" → take the first value
                elif len(cls_resp) == 1:
                    first_val = list(cls_resp.values())[0]
                    if isinstance(first_val, str):
                        cls_result = first_val.strip().upper()
            elif isinstance(cls_resp, list) and len(cls_resp) > 0:
                # 3. List → check the first element
                first_val = cls_resp[0]
                if isinstance(first_val, str):
                    cls_result = first_val.strip().upper()
                elif isinstance(first_val, dict) and "type" in first_val:
                    cls_result = str(first_val["type"]).strip().upper()
            elif isinstance(cls_resp, str):
                # 4. Plain string
                cls_result = cls_resp.strip().upper()
            elif cls_resp is None:
                print("Classifier returned None – fallback to QA")
            else:
                print(f"Unrecognized classifier response type: {type(cls_resp)}")

        except Exception as e:
            print(f"Error during classification: {e} – fallback to QA")

        print(f"Final classification result: {cls_result}")

        # --- Routing ---
        if cls_result == "NPC":
                return self.npc_pipeline.generate(prompt=query)
        elif cls_result == "QA":
            return self.qa_pipeline.answer(question=query)
        else:
            print("Classification returned NONE/UNKNOWN – fallback to QA")
            return self.qa_pipeline.answer(question=query)