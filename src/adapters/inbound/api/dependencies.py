"""Route dependencies: how each route reaches the ports.

The inbound layer may not import outbound adapters, so ``create_app`` stores
the ports it receives on ``app.state`` and routes ask for them with
``Depends(get_services)``.
"""

from collections.abc import Callable
from dataclasses import dataclass

from fastapi import Request

from src.application.ports.index_store import IndexStore
from src.domain.models import MinimalSource


@dataclass(frozen=True)
class ApiServices:
    """What every route needs, fixed when the app is built.

    Attributes:
        index_store: Tells the version of the index, part of every cache key.
        index_path: The index file to search.
        search: ``run_search`` behind a result cache keyed by query, ``k``
            and index version.
        answer: ``run_answer`` behind the same kind of cache.
    """

    index_store: IndexStore
    index_path: str
    search: Callable[
        [str, int, tuple[int, int]], list[tuple[MinimalSource, float]]
    ]
    answer: Callable[[str, int, tuple[int, int]], str]


def get_services(request: Request) -> ApiServices:
    """Hand a route the services stored on its app.

    Args:
        request: The incoming request, which knows its app.

    Returns:
        The services ``create_app`` stored on ``app.state``.
    """
    # app.state is untyped; the annotation keeps --warn-return-any quiet.
    services: ApiServices = request.app.state.services
    return services
