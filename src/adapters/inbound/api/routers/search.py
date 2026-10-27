"""Search route: retrieves the sources of a query."""

from fastapi import APIRouter, Depends, HTTPException

from src.adapters.inbound.api.dependencies import ApiServices, get_services
from src.adapters.inbound.api.schemas import QueryRequest, SearchResponse


search_router = APIRouter(prefix="/search")


@search_router.post("", response_model=SearchResponse)
def handle_search(
    request: QueryRequest,
    services: ApiServices = Depends(get_services)
) -> SearchResponse:
    """Return the best sources for a query, as ``search`` does in the CLI.

    Args:
        request: The query and how many sources to return.
        services: The ports, injected by FastAPI.

    Returns:
        The query and its retrieved sources.

    Raises:
        HTTPException: 400 with the CLI message for any user error.
    """
    try:
        version = services.index_store.index_version(services.index_path)
        results = services.search(request.query, request.k, version)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error))
    return SearchResponse(
        question=request.query,
        retrieved_sources=[source for source, _ in results]
    )
