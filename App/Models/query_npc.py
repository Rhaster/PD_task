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
    profession: str = Field(..., min_length=1)
    faction: str = Field(..., min_length=1)
    personality_traits: List[str] = Field(default_factory=list, min_items=2, max_items=5)

    skip_unique_validation: bool = Field(default=False, exclude=True)
    bool_unique_validated: bool = Field(default=False, exclude=True)

    @field_validator("personality_traits", mode="before")
    @classmethod
    def _traits_to_list(cls, v):
        """Pozwala podać cechy jako string 'a, b, c' lub listę."""
        if v is None:
            return []
        if isinstance(v, str):
            return [s.strip() for s in v.split(",") if s.strip()]
        return v

    @model_validator(mode="after")
    def _unique_name_check(self):
        """Checks unique"""
        if self.skip_unique_validation:
            return self
        existing = set(existing_names())
        logging_function(f"Validating uniqueness of name: {self.name}", level="debug")
        if self.name in existing:
            logging_function(f"Name '{self.name}' already exists in the database", level="error")
            raise ValueError(f"Name '{self.name}' already exists in the database")
        self.bool_unique_validated = True
        return self


class NPCAmount(BaseModel):
    amount: int
    npcs: list[NPC]

    @model_validator(mode="after")
    def check_minimum_amount(self):
        if len(self.npcs) < self.amount:
            logging_function( "Not enought npc ")
            raise ValueError(f"At least {self.amount} NPCs required, got {len(self.npcs)}")
        return self