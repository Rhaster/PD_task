
from Models.models import NPC


def validate_npcs(npcs: list[dict]) -> list[dict]:
    out: list[dict] = []
    for n in npcs:
        obj = NPC(**n)
        out.append(obj.model_dump())
    return out