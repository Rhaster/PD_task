from core.rag import FaissRAG

from services.npc_pipeline import NPCPipeline
from services.qa_pipeline import QAPipeline
from Config.config import settings
from core.llm import chat_json




class GeneralPipeline:
    def __init__(self):
        self.npc_pipeline = NPCPipeline(FaissRAG(index_path=settings.faiss_path))
        self.qa_pipeline = QAPipeline(FaissRAG(index_path=settings.faiss_path))

    def process(self, query: str, npc_threshold: float = 0.5):
        """
        Klasyfikacja pytania:
        - jeśli pytanie dotyczy NPC → generowanie NPC
        - jeśli pytanie dotyczy QA → odpowiedź
        """
        # Prosta klasyfikacja za pomocą modelu LLM
        classification_prompt = f"""
        Decide if the following user query is asking to GENERATE NPC or is a QA question.
        Respond ONLY with one word: NPC or QA.
        Query: {query}
        """
        cls_resp = chat_json(system="You are a classifier", user=classification_prompt)
        cls_result = str(cls_resp).strip().upper()
        if cls_result == "NPC":
            return self.npc_pipeline.generate(prompt=query)
        else:
            return self.qa_pipeline.answer(question=query)