"""Schema for a Non-Player Character (NPC)."""

from pydantic import BaseModel, model_validator
from typing import Annotated, List
from pydantic import BaseModel, Field,field_validator
from typing import List
from App.Config.database import existing_names 
from App.Services.utility import logging_function
class NPC(BaseModel):
    """Schema for a Non-Player Character (NPC)."""
    name: str = Field(..., min_length=1)
    profession: str
    faction: str
    personality_traits: List[str] = Field(default_factory=list,min_items=2, max_items=5)
    skip_unique_validation: bool = Field(default=False, exclude=True)

    @field_validator("name")
    def unique_name(cls, v):
        """Ensure the NPC name is unique in the database."""
        existing = existing_names()
        logging_function(f"Validating uniqueness of name: {v}", level="debug")
        if v in existing:
            logging_function(f"Name '{v}' already exists in the database", level="error")
            raise ValueError(f"Name '{v}' already exists in the database")
        return v


class NPCAmount(BaseModel):
    amount: int
    npcs: list[NPC]

    @model_validator(mode="after")
    def check_minimum_amount(self):
        if len(self.npcs) < self.amount:
            raise ValueError(f"At least {self.amount} NPCs required, got {len(self.npcs)}")
        return self