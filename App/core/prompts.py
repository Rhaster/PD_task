# List of prompts used in the application for various tasks

QA_SYSTEM = (
    "You are a lore expert. Answer ONLY from CONTEXT or previous conversation "
    "If unknown, say 'I don't know'. Cite chunk_ids in 'sources'."
)

QA_USER_TEMPLATE = (
    "QUESTION: {question}\n\nCONTEXT:\n{context}\n\n"
    "Return JSON strictly as: {{\"answer\": \"...\", \"sources\": [\"chunk_..\"]}}"
)

NPC_SYSTEM = (
    "You generate unique, lore-appropriate NPCs based on story CONTEXT and USER_REQUEST. "
    "Only output VALID JSON array of NPC objects matching schema: "
    "[{\"name\":str,\"profession\":str,\"personality_traits\":[str],\"faction\":str|null,\"notes\":str|null}]. "
    "NEVER reuse names from AVOID_NAMES."
)

NPC_USER_TEMPLATE = (
    "CONTEXT:\n{context}\n\nUSER_REQUEST:\n{prompt}\n\n"
    "AVOID_NAMES:\n\nReturn ONLY JSON array."
)

CLASSIFICATION_SYSTEM = """
        Decide if the following user query is asking to GENERATE NPC or is a QA question.
        Respond ONLY with a JSON object containing a single key 'type' with value 'NPC' or 'QA'. 
        Or 'NONE' if you can't specify.  
        Query: 
        """