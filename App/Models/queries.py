""" Pydantic models for query requests and responses. """
from pydantic import BaseModel


class QARequest(BaseModel):
    """Schema for question-answering requests."""
    question: str


class QAResponse(BaseModel):
    """Schema for question-answering responses."""
    answer: str
    sources: list[str]