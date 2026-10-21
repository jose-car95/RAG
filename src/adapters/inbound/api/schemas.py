"""Pydantic schemas: the shape of the JSON the API receives and sends."""

from typing import Literal

from pydantic import BaseModel

from src.domain.models import MinimalSource


class QueryRequest(BaseModel):
    """Body of ``POST /search`` and ``POST /answer``.

    Attributes:
        query: The question, with the same rules as in the CLI.
        k: How many sources to retrieve.
    """

    query: str
    k: int = 10


class SearchResponse(BaseModel):
    """Body returned by ``POST /search``.

    Attributes:
        question: The query, echoed back.
        retrieved_sources: The best sources, best first.
    """

    question: str
    retrieved_sources: list[MinimalSource]


class AnswerResponse(BaseModel):
    """Body returned by ``POST /answer``.

    Attributes:
        question: The query, echoed back.
        answer: The model answer, grounded in the retrieved sources.
    """

    question: str
    answer: str


class HealthResponse(BaseModel):
    """Body of ``GET /health``: a fixed liveness flag.

    Attributes:
        status: Always ``"ok"`` while the server can answer.
    """

    status: Literal["ok"]
