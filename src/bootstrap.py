"""Composition root: the only place that picks the real adapters.

The use cases only know ports. Here each outbound adapter is plugged into its
port and the result is handed to an inbound adapter, the CLI or the API.
Swapping SQLite or Qwen for something else changes this file and nothing
else.
"""

import os

from fastapi import FastAPI

from src.adapters.outbound.corpus import FileCorpus
from src.adapters.outbound.json_files import JsonDatasetStore
from src.adapters.outbound.minilm_embedder import load_embedder
from src.adapters.outbound.qwen_generator import load_generator
from src.adapters.outbound.sqlite_index import SqliteIndexStore
from src.adapters.inbound.cli import DEFAULT_INDEX_PATH, RagCli, run
from src.adapters.inbound.api.app import DEFAULT_CORS_ORIGINS, create_app
from src.adapters.outbound.sqlite_vectors import SqliteVectorStore


def build_cli() -> RagCli:
    """Create the CLI with every real adapter plugged in.

    Returns:
        The CLI, ready for Fire.
    """
    return RagCli(
        index_store=SqliteIndexStore(),
        corpus=FileCorpus(),
        datasets=JsonDatasetStore(),
        load_generator=load_generator,
        vector_store=SqliteVectorStore(),
        load_embedder=load_embedder
    )


def read_cors_origins() -> list[str]:
    """Read the allowed browser origins from ``RAG_CORS_ORIGINS``.

    Returns:
        The comma-separated origins of the variable, or the local frontend
        defaults when it is unset or blank.
    """
    raw = os.environ.get("RAG_CORS_ORIGINS", "")
    origins = [origin.strip() for origin in raw.split(",") if origin.strip()]
    return origins or list(DEFAULT_CORS_ORIGINS)


def build_api() -> FastAPI:
    """Create the HTTP API with every real adapter plugged in.

    Returns:
        The app, ready for ``uvicorn --factory``.
    """
    return create_app(
        index_store=SqliteIndexStore(),
        corpus=FileCorpus(),
        load_generator=load_generator,
        index_path=DEFAULT_INDEX_PATH,
        cors_origins=read_cors_origins()
    )


def main() -> int:
    """Run the RAG command-line interface.

    Returns:
        The exit code, to be passed to ``sys.exit``.
    """
    return run(build_cli())
