"""FastAPI application: builds the app and plugs in the API router."""

from functools import cache, lru_cache
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from src.adapters.inbound.api.dependencies import ApiServices
from src.adapters.inbound.api.router import api_v1_router
from src.application.ports.corpus_reader import CorpusReader
from src.application.ports.generator import GeneratorLoader
from src.application.ports.index_store import IndexStore
from src.application.use_cases.answer import run_answer
from src.application.use_cases.shared.retrieval import IndexCache
from src.application.use_cases.search import run_search
from src.domain.models import MinimalSource


# Results kept per route; the least recently used one goes first when full.
QUERY_CACHE_SIZE: int = 256

# The static chat client, at the repo root next to src/. Served by the API so
# the page and the API share one origin (no CORS) under a single `serve`.
FRONTEND_DIR = Path(__file__).resolve().parents[4] / "frontend"


def create_app(
    index_store: IndexStore,
    corpus: CorpusReader,
    load_generator: GeneratorLoader,
    index_path: str
) -> FastAPI:
    """Build the API with the given ports; used by bootstrap and the tests.

    Args:
        index_store: Where the index is read from.
        corpus: Where the source files are read from.
        load_generator: Loads the model on the first answer.
        index_path: The index file to search.

    Returns:
        The app, with every route under ``/api/v1``. It owns its caches: the
        model, the built index and the results of repeated queries.
    """
    app = FastAPI(title="RAG against the machine")
    index_cache = IndexCache()
    load_once = cache(load_generator)

    @lru_cache(maxsize=QUERY_CACHE_SIZE)
    def search(
        query: str, k: int, version: tuple[int, int]
    ) -> list[tuple[MinimalSource, float]]:
        """Search once per query, ``k`` and index version.

        ``version`` is unused in the body on purpose: it only makes a rebuilt
        index a new cache key. Errors are raised, never cached.
        """
        return run_search(
            query, k, index_path, index_store, load=index_cache.load
        )

    @lru_cache(maxsize=QUERY_CACHE_SIZE)
    def answer(query: str, k: int, version: tuple[int, int]) -> str:
        """Answer once per query, ``k`` and index version, like ``search``."""
        return run_answer(
            query, k, index_path, index_store, corpus, load_once,
            load=index_cache.load
        )

    app.state.services = ApiServices(
        index_store=index_store,
        index_path=index_path,
        search=search,
        answer=answer
    )
    app.include_router(api_v1_router)
    # Mounted last and at the root, so it only catches what the API routes and
    # /docs did not: the chat page at / and its assets. html=True serves
    # index.html for /. Guarded so the API still starts without the folder.
    if FRONTEND_DIR.is_dir():
        chat = StaticFiles(directory=FRONTEND_DIR, html=True)
        app.mount("/", chat, name="frontend")
    return app
