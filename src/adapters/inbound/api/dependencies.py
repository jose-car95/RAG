"""Route dependencies: how each route reaches the ports.

The inbound layer may not import outbound adapters, so ``create_app`` stores
the ports it receives on ``app.state`` and routes ask for them with
``Depends(get_services)``.
"""

from dataclasses import dataclass

from fastapi import Request

from src.application.ports.corpus_reader import CorpusReader
from src.application.ports.generator import GeneratorLoader
from src.application.ports.index_store import IndexStore
from src.application.use_cases.retrieval import IndexLoader


@dataclass(frozen=True)
class ApiServices:
    """The ports and settings every route needs, fixed when the app is built.

    Attributes:
        index_store: Where the index is read from.
        corpus: Where the source files are read from.
        load_generator: Model loader, cached so Qwen loads once per app.
        index_path: The index file to search.
        load_index: Index loader, cached so the index is built once per app
            and again only when the file changes.
    """

    index_store: IndexStore
    corpus: CorpusReader
    load_generator: GeneratorLoader
    index_path: str
    load_index: IndexLoader


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
