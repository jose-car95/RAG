"""Composition root: the only place that picks the real adapters.

The use cases only know ports. Here each outbound adapter is plugged into its
port and the result is handed to the inbound adapter, the CLI. Swapping
SQLite or Qwen for something else changes this file and nothing else.
"""

from src.adapters.outbound.corpus import FileCorpus
from src.adapters.outbound.json_files import JsonDatasetStore
from src.adapters.outbound.qwen_generator import load_generator
from src.adapters.outbound.sqlite_index import SqliteIndexStore
from src.adapters.inbound.cli import RagCli, run


def build_cli() -> RagCli:
    """Create the CLI with every real adapter plugged in.

    Returns:
        The CLI, ready for Fire.
    """
    return RagCli(
        index_store=SqliteIndexStore(),
        corpus=FileCorpus(),
        datasets=JsonDatasetStore(),
        load_generator=load_generator
    )


def main() -> int:
    """Run the RAG command-line interface.

    Returns:
        The exit code, to be passed to ``sys.exit``.
    """
    return run(build_cli())
