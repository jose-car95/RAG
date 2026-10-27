"""Answer route: answers a query with the model and its sources."""

from fastapi import APIRouter, Depends, HTTPException

from src.adapters.inbound.api.dependencies import ApiServices, get_services
from src.adapters.inbound.api.schemas import AnswerResponse, QueryRequest


answer_router = APIRouter(prefix="/answer")


@answer_router.post("", response_model=AnswerResponse)
def handle_answer(
    request: QueryRequest,
    services: ApiServices = Depends(get_services)
) -> AnswerResponse:
    """Answer a query from its sources, as ``answer`` does in the CLI.

    Args:
        request: The query and how many sources to use.
        services: The ports, injected by FastAPI.

    Returns:
        The query and the model answer.

    Raises:
        HTTPException: 400 with the CLI message for any user error.
    """
    try:
        version = services.index_store.index_version(services.index_path)
        text = services.answer(request.query, request.k, version)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error))
    return AnswerResponse(question=request.query, answer=text)
