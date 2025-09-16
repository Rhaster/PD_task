# Models/models.py
# Pydantic models for NPC generation and responses.
# Defines the structure and validation for NPC data.
# Includes request and response models for API interactions.

from pydantic import BaseModel, constr, conlist
from typing import Annotated
from pydantic import BaseModel, field_validator, Field
from typing import List
from db.database import existing_names  # funkcja zwracająca listę istniejących nazw NPC
import logging
class NPC(BaseModel):
    name: str = Field(..., min_length=1)
    profession: str
    faction: str
    personality_traits: List[str] = Field(default_factory=list,min_items=2, max_items=5)


    @field_validator("name")
    def unique_name(cls, v):
        existing = existing_names()
        logging.info(f"Validating uniqueness of name: {v}")
        if v in existing:
            logging.error(f"Name '{v}' already exists in the database")
            raise ValueError(f"Name '{v}' already exists in the database")
        return v


class NPCRequest(BaseModel):
    prompt: str | None = None
    count: int = 1
    constraints: dict | None = None 
    notes : str | None = None
class NPCResponse(BaseModel):
    items: list[NPC]