"""FastAPI application: builds the app and plugs in the API router."""

from functools import cache

from fastapi import FastAPI

from src.adapters.inbound.api.dependencies import ApiServices
from src.adapters.inbound.api.router import api_v1_router
from src.application.ports.corpus_reader import CorpusReader
from src.application.ports.generator import GeneratorLoader
from src.application.ports.index_store import IndexStore
from src.application.use_cases.retrieval import IndexCache


def create_app(
    index_store: IndexStore,
    corpus: CorpusReader,
    load_generator: GeneratorLoader,
    index_path: str = "data/processed/index.db"
) -> FastAPI:
    """Build the API with the given ports; used by bootstrap and the tests.

    Args:
        index_store: Where the index is read from.
        corpus: Where the source files are read from.
        load_generator: Loads the model on the first answer.
        index_path: The index file to search.

    Returns:
        The app, with every route under ``/api/v1``.
    """
    app = FastAPI(title="RAG against the machine")
    app.state.services = ApiServices(
        index_store=index_store,
        corpus=corpus,
        load_generator=cache(load_generator),
        index_path=index_path,
        load_index=IndexCache().load
    )
    app.include_router(api_v1_router)
    return app
