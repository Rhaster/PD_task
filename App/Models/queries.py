# Models/queries.py
# Pydantic models for QA system requests and responses.
# Defines the structure and validation for QA data.
# Includes request and response models for API interactions.

from pydantic import BaseModel


class QARequest(BaseModel):
    question: str


class QAResponse(BaseModel):
    answer: str
    sources: list[str]