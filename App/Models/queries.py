from pydantic import BaseModel


class QARequest(BaseModel):
    question: str


class QAResponse(BaseModel):
    answer: str
    sources: list[str]