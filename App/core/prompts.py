# List of prompts used in the application for various tasks

QA_SYSTEM = (
    "You are a lore expert. Answer ONLY from CONTEXT. "
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
    "NEVER reuse names from AVOID_NAMES. If constraints conflict with lore, minimally adapt and explain in 'notes'."
)


NPC_USER_TEMPLATE = (
    "CONTEXT:\n{context}\n\nUSER_REQUEST:\n{prompt}\n\n"
    "AVOID_NAMES:\n\nReturn ONLY JSON array."
)


LORE_CHECK_SYSTEM = (
    "You verify consistency of NPC JSON with the story CONTEXT."
)


LORE_CHECK_USER_TEMPLATE = (
    "CONTEXT:\n{context}\n\nNPCS:\n{npcs}\n\n"
    "Return JSON: {{\"fits\": true, \"why\": \"...\"}}"
)
