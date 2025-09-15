from pydantic import BaseModel, constr, conlist


from pydantic import BaseModel, constr, conlist
from typing import Annotated

class NPC(BaseModel):
    name: constr(strip_whitespace=True, min_length=2)
    faction: constr(strip_whitespace=True) | None = None
    profession: constr(strip_whitespace=True, min_length=2)
    personality_traits: Annotated[list[str], conlist(str, min_length=2, max_length=6)]
    notes: str | None = None


class NPCRequest(BaseModel):
    prompt: str | None = None
    count: int = 1
    constraints: dict | None = None # {"faction":"...","profession":"...","traits":[...]}


class NPCResponse(BaseModel):
    items: list[NPC]