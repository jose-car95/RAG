"""End-to-end tests for the command-line entry point.

The CLI is run in a subprocess, exactly as the subject invokes it
(``python -m src <command>``), so these tests see the real exit code and the
real stdout/stderr instead of calling Python functions directly.
"""

import json
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

from src.adapters.inbound.cli import RagCli, run, usage_error, vectors_summary
from src.application.use_cases.embed_index import EmbedReport
from src.adapters.outbound.corpus import FileCorpus
from src.adapters.outbound.json_files import JsonDatasetStore
from src.adapters.outbound.sqlite_index import SqliteIndexStore
from src.adapters.outbound.sqlite_vectors import SqliteVectorStore
from tests.application.test_answer import FakeLoader
from tests.application.test_answer_dataset import write_results
from tests.application.test_embed_index import FakeEmbedderLoader

REPO_ROOT = Path(__file__).resolve().parents[3]

REQUIRED_COMMANDS = (
    "index",
    "search",
    "search_dataset",
    "answer",
    "answer_dataset",
    "evaluate",
)


def make_cli(load_embedder: FakeEmbedderLoader) -> RagCli:
    """Build the CLI in-process with real stores and fake models.

    Args:
        load_embedder: The fake embedding model loader.

    Returns:
        A CLI that never loads Qwen or MiniLM.
    """
    return RagCli(
        SqliteIndexStore(),
        FileCorpus(),
        JsonDatasetStore(),
        FakeLoader(),
        SqliteVectorStore(),
        load_embedder
    )


def run_cli(
    *args: str, cwd: Path = REPO_ROOT
) -> subprocess.CompletedProcess[str]:
    """Run ``python -m src`` with the given arguments.

    Args:
        *args: Command-line arguments passed after ``python -m src``.
        cwd: Directory to run from; the repo root by default. A test that
            relies on a default output path passes a temporary folder so it
            never writes into the real ``data/`` tree.

    Returns:
        The finished process, with decoded stdout and stderr.
    """
    # ``-m src`` needs the repo on the import path even when the command runs
    # from another folder, so that a default output path lands under ``cwd``.
    env = {**os.environ, "PYTHONPATH": str(REPO_ROOT)}
    return subprocess.run(
        [sys.executable, "-m", "src", *args],
        cwd=cwd,
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
    )


def test_help_lists_required_commands() -> None:
    """``--help`` lists every command required by the subject."""
    result = run_cli("--help")
    # Fire writes its help to stderr when the output is not a terminal.
    output = result.stdout + result.stderr

    assert result.returncode == 0, result.stderr
    for command in REQUIRED_COMMANDS:
        # One command per line, so "search" is not matched by "search_dataset".
        assert re.search(rf"^\s+{command}$", output, re.MULTILINE), output


def test_usage_error_names_the_program() -> None:
    """Fire's usage messages name the program ``src``, not ``__main__.py``."""
    result = run_cli("nonexistent_command")

    assert result.returncode == 2
    assert "unknown command 'nonexistent_command'" in result.stderr
    assert "Valid commands:" in result.stderr
    assert "Traceback" not in result.stderr


def make_tiny_index(tmp_path: Path) -> Path:
    """Build an index of its own, so the test needs no local state.

    The real ``data/processed/index.db`` is generated and never committed, so
    a test that relied on it passed here and failed in CI.

    Args:
        tmp_path: Temporary folder provided by pytest.

    Returns:
        Path of the index.
    """
    corpus = tmp_path / "corpus"
    corpus.mkdir()
    (corpus / "notes.md").write_text(
        "# Endpoints\nThe http endpoint loads a lora adapter.\n",
        encoding="utf-8",
    )
    index_path = tmp_path / "index.db"
    run_cli(
        "index", "--raw_directory", str(corpus),
        "--index_path", str(index_path),
    )
    return index_path


def test_search_dataset_writes_results_file(tmp_path: Path) -> None:
    """The results file is written and its path is reported."""
    index_path = make_tiny_index(tmp_path)

    result = run_cli(
        "search_dataset",
        "--dataset_path",
        "data/datasets/UnansweredQuestions/dataset_docs_public.json",
        "--k",
        "10",
        "--save_directory",
        str(tmp_path),
        "--index_path",
        str(index_path),
    )

    output_path = tmp_path / "dataset_docs_public.json"
    assert result.returncode == 0, result.stderr
    assert result.stdout == (
        f"Saved student_search_results to {output_path}\n"
    )
    assert output_path.is_file()


def test_search_dataset_uses_default_save_directory(tmp_path: Path) -> None:
    """Without ``--save_directory`` the file goes to the default folder.

    Run from ``tmp_path`` so the default relative path resolves there and the
    real ``data/output`` tree is never touched.
    """
    dataset = (
        REPO_ROOT
        / "data/datasets/UnansweredQuestions/dataset_code_public.json"
    )

    result = run_cli(
        "search_dataset",
        "--dataset_path",
        str(dataset),
        "--k",
        "10",
        "--index_path",
        str(make_tiny_index(tmp_path)),
        cwd=tmp_path,
    )

    output_path = (
        tmp_path / "data/output/search_results/dataset_code_public.json"
    )
    assert result.returncode == 0, result.stderr
    assert output_path.is_file()


def test_index_reports_missing_corpus_folder() -> None:
    """A missing corpus folder ends in a one-line error and exit code 1."""
    result = run_cli("index", "--raw_directory", "/nonexistent")

    assert result.returncode == 1
    assert result.stderr == "ERROR: corpus folder not found: /nonexistent\n"


def test_search_prints_the_ranked_sources(tmp_path: Path) -> None:
    """``search`` prints one numbered line per source, best first."""
    corpus = tmp_path / "corpus"
    corpus.mkdir(exist_ok=True)
    (corpus / "b.md").write_text(
        "# Endpoints\nThe http endpoint loads a lora adapter.\n",
        encoding="utf-8",
    )
    index_path = tmp_path / "index.db"
    run_cli(
        "index", "--raw_directory", str(corpus),
        "--index_path", str(index_path),
    )

    result = run_cli(
        "search", "http endpoint", "--k", "5",
        "--index_path", str(index_path),
    )

    assert result.returncode == 0, result.stderr
    first_line = result.stdout.splitlines()[0]
    assert first_line.startswith("1. ")
    assert str(corpus / "b.md") in first_line
    assert "[0:" in first_line


def test_search_says_when_nothing_is_found(tmp_path: Path) -> None:
    """A query with no match prints a message instead of nothing."""
    corpus = tmp_path / "corpus"
    corpus.mkdir()
    (corpus / "b.md").write_text("# Endpoints\n", encoding="utf-8")
    index_path = tmp_path / "index.db"
    run_cli(
        "index", "--raw_directory", str(corpus),
        "--index_path", str(index_path),
    )

    result = run_cli(
        "search", "kubernetes", "--index_path", str(index_path)
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout == "No sources found.\n"


def build_semantic_index(
    tmp_path: Path, cli: RagCli
) -> tuple[Path, Path]:
    """Index a one-chunk corpus with embeddings, through the given CLI.

    Args:
        tmp_path: Temporary folder provided by pytest.
        cli: The in-process CLI with a fake embedder.

    Returns:
        The index file and the vectors file.
    """
    corpus = tmp_path / "corpus"
    corpus.mkdir(exist_ok=True)
    (corpus / "b.md").write_text(
        "# Endpoints\nThe http endpoint loads a lora adapter.\n",
        encoding="utf-8",
    )
    index_path = tmp_path / "index.db"
    vectors_path = tmp_path / "embeddings.db"
    run(
        cli,
        [
            "index",
            "--raw_directory", str(corpus),
            "--index_path", str(index_path),
            "--semantic",
            "--vectors_path", str(vectors_path),
        ],
    )
    return index_path, vectors_path


def test_search_semantic_ranks_with_the_embedding_model(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """``--retriever semantic`` prints a ranked source using the vectors."""
    cli = make_cli(FakeEmbedderLoader())
    index_path, vectors_path = build_semantic_index(tmp_path, cli)
    capsys.readouterr()

    exit_code = run(
        cli,
        [
            "search", "how do I load it",
            "--index_path", str(index_path),
            "--retriever", "semantic",
            "--vectors_path", str(vectors_path),
        ],
    )

    assert exit_code == 0
    first_line = capsys.readouterr().out.splitlines()[0]
    assert first_line.startswith("1. ")
    assert str(tmp_path / "corpus" / "b.md") in first_line


def test_an_unknown_retriever_is_rejected(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """A retriever that is neither bm25 nor semantic fails with exit 1."""
    cli = make_cli(FakeEmbedderLoader())
    index_path, _ = build_semantic_index(tmp_path, cli)
    capsys.readouterr()

    exit_code = run(
        cli,
        [
            "search", "http endpoint",
            "--index_path", str(index_path),
            "--retriever", "lexical",
        ],
    )

    assert exit_code == 1
    assert capsys.readouterr().err == (
        "ERROR: retriever must be 'bm25', 'semantic' or 'hybrid'\n"
    )


def test_search_hybrid_fuses_both_retrievers(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """``--retriever hybrid`` prints a ranked source from the fused lists."""
    cli = make_cli(FakeEmbedderLoader())
    index_path, vectors_path = build_semantic_index(tmp_path, cli)
    capsys.readouterr()

    exit_code = run(
        cli,
        [
            "search", "http endpoint",
            "--index_path", str(index_path),
            "--retriever", "hybrid",
            "--vectors_path", str(vectors_path),
        ],
    )

    assert exit_code == 0
    first_line = capsys.readouterr().out.splitlines()[0]
    assert first_line.startswith("1. ")
    assert str(tmp_path / "corpus" / "b.md") in first_line


def test_semantic_search_without_embeddings_says_to_index(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Asking for meaning before embedding says what to run, exit 1."""
    cli = make_cli(FakeEmbedderLoader())
    index_path = make_tiny_index(tmp_path)
    capsys.readouterr()

    exit_code = run(
        cli,
        [
            "search", "http endpoint",
            "--index_path", str(index_path),
            "--retriever", "semantic",
            "--vectors_path", str(tmp_path / "embeddings.db"),
        ],
    )

    assert exit_code == 1
    assert capsys.readouterr().err == (
        f"ERROR: embeddings not found: {tmp_path / 'embeddings.db'}; "
        f"run index --semantic first\n"
    )


def test_index_writes_the_index_file(tmp_path: Path) -> None:
    """``index`` reports how many chunks it stored and where (VI.1 capture)."""
    corpus = tmp_path / "corpus"
    corpus.mkdir()
    source = "def first() -> int:\n    return 1\n"
    (corpus / "a.py").write_text(source, encoding="utf-8")
    index_path = tmp_path / "processed" / "index.db"

    result = run_cli(
        "index",
        "--raw_directory",
        str(corpus),
        "--index_path",
        str(index_path),
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout == (
        f"Ingestion complete! Indexed 1 chunks under {index_path.parent}/\n"
    )
    assert index_path.is_file()


def test_index_with_embeddings_stores_the_vectors(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """``--semantic`` adds one line after the subject's one."""
    corpus = tmp_path / "corpus"
    corpus.mkdir()
    (corpus / "a.py").write_text("def first() -> int:\n    return 1\n")
    index_path = tmp_path / "processed" / "index.db"
    vectors_path = tmp_path / "processed" / "embeddings.db"
    loader = FakeEmbedderLoader()

    exit_code = run(
        make_cli(loader),
        [
            "index",
            "--raw_directory", str(corpus),
            "--index_path", str(index_path),
            "--semantic",
            "--vectors_path", str(vectors_path),
        ],
    )

    assert exit_code == 0
    assert capsys.readouterr().out.splitlines()[-1] == (
        f"Embeddings ready! 1 new of 1 chunk texts under "
        f"{vectors_path.parent}/"
    )
    assert vectors_path.is_file()


def test_index_without_embeddings_loads_no_model(tmp_path: Path) -> None:
    """The subject's ``index`` stays as it was: no vectors, no model."""
    corpus = tmp_path / "corpus"
    corpus.mkdir()
    (corpus / "a.py").write_text("def first() -> int:\n    return 1\n")
    index_path = tmp_path / "processed" / "index.db"
    loader = FakeEmbedderLoader()

    exit_code = run(
        make_cli(loader),
        ["index", "--raw_directory", str(corpus), "--index_path",
         str(index_path)],
    )

    assert exit_code == 0
    assert loader.loads == 0
    assert not (index_path.parent / "embeddings.db").exists()


def test_evaluate_prints_recall_in_the_subject_format(tmp_path: Path) -> None:
    """One line with Recall@1/3/5/10 and three decimals, as in the subject."""
    correct = {
        "file_path": "data/raw/vllm-0.10.1/docs/features/lora.md",
        "first_character_index": 4695,
        "last_character_index": 6098,
    }
    wrong = dict(correct, first_character_index=0, last_character_index=10)
    dataset = tmp_path / "dataset.json"
    dataset.write_text(
        json.dumps({
            "rag_questions": [
                {
                    "question_id": question_id,
                    "question": "How to load a lora adapter?",
                    "sources": [correct],
                    "answer": "With the endpoint.",
                }
                for question_id in ("q1", "q2")
            ]
        }),
        encoding="utf-8",
    )
    results = tmp_path / "results.json"
    results.write_text(
        json.dumps({
            "search_results": [
                {
                    "question_id": "q1",
                    "question": "How to load a lora adapter?",
                    "retrieved_sources": [correct],
                },
                {
                    "question_id": "q2",
                    "question": "How to load a lora adapter?",
                    "retrieved_sources": [wrong, wrong, wrong, correct],
                },
            ],
            "k": 10,
        }),
        encoding="utf-8",
    )

    result = run_cli(
        "evaluate",
        "--student_search_results_path",
        str(results),
        "--dataset_path",
        str(dataset),
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout == (
        "Recall@1: 0.500 Recall@3: 0.500 Recall@5: 1.000 Recall@10: 1.000\n"
        "MRR: 0.625\n"
    )


def test_cli_import_does_not_load_torch() -> None:
    """``--help``, ``index`` and ``search`` must not pay for torch's import.

    Only ``answer`` needs the model, so torch is imported inside
    ``load_generator``; importing the whole wiring, which plugs in the Qwen
    adapter, must leave it out.
    """
    code = (
        "import sys\n"
        "import src.bootstrap\n"
        "print('torch' in sys.modules, 'transformers' in sys.modules)\n"
    )
    result = subprocess.run(
        [sys.executable, "-c", code],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=60,
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "False False"


def test_answer_without_sources_says_so(tmp_path: Path) -> None:
    """Nothing retrieved: the user is told, and it is not an error."""
    index_path = make_tiny_index(tmp_path)

    result = run_cli(
        "answer", "asdfghjkl", "--k", "10", "--index_path", str(index_path)
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout == (
        "No sources found, so the question cannot be answered.\n"
    )


@pytest.mark.slow
@pytest.mark.skipif(
    not (REPO_ROOT / ".cache/huggingface/models--Qwen--Qwen3-0.6B").is_dir()
    or not (REPO_ROOT / "data/processed/index.db").is_file(),
    reason="needs the Qwen weights and the real index",
)
def test_answer_uses_the_real_sources_and_model() -> None:
    """End to end, with Qwen on CPU: the answer names the real endpoint."""
    result = run_cli(
        "answer", "How do I dynamically load a LoRA adapter in vLLM?",
        "--k", "10",
    )

    assert result.returncode == 0, result.stderr
    assert "load_lora_adapter" in result.stdout


def test_answer_dataset_prints_the_subject_lines(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Loaded, processed and saved, as in VI.7.2 step 4 of the subject.

    Run in-process with the fake model plugged into the port, so the output
    is checked without loading Qwen.
    """
    input_path = write_results(tmp_path)
    save_directory = tmp_path / "answers"
    cli = make_cli(FakeEmbedderLoader())

    exit_code = run(
        cli,
        [
            "answer_dataset",
            "--student_search_results_path",
            str(input_path),
            "--save_directory",
            str(save_directory),
        ],
    )

    output = save_directory / "dataset_docs_public.json"
    assert exit_code == 0
    assert capsys.readouterr().out == (
        "Loaded 3 questions ... Processed 3 of 3 questions\n"
        f"Saved student_search_results_and_answer to {output}\n"
    )


def test_embeddings_second_run_does_nothing(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """With ``--semantic`` an unchanged corpus is not chunked or embedded."""
    cli = make_cli(FakeEmbedderLoader())
    build_semantic_index(tmp_path, cli)
    capsys.readouterr()

    build_semantic_index(tmp_path, cli)

    captured = capsys.readouterr()
    assert "Index up to date" in captured.err
    assert "Chunking" not in captured.err
    assert "1 vectors already stored, 0 to embed" in captured.err
    assert "Index: up to date" in captured.err
    assert "0 new of 1 chunk texts" in captured.out


def test_embeddings_reindex_a_changed_corpus(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """A change in the corpus is chunked and embedded again."""
    cli = make_cli(FakeEmbedderLoader())
    index_path, vectors_path = build_semantic_index(tmp_path, cli)
    (tmp_path / "corpus" / "b.md").write_text("# New\nfresh words\n")
    capsys.readouterr()

    run(
        cli,
        [
            "index",
            "--raw_directory", str(tmp_path / "corpus"),
            "--index_path", str(index_path),
            "--semantic",
            "--vectors_path", str(vectors_path),
        ],
    )

    captured = capsys.readouterr()
    assert "Chunking" in captured.err
    assert "Index: updated" in captured.err
    assert "1 new of 1 chunk texts" in captured.out


SECTIONS = "# One\nfirst words\n\n# Two\nsecond words\n\n# Three\nthird\n"


def reindex_semantic(
    cli: RagCli, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> str:
    """Run ``index --semantic`` on the corpus of the test and read stderr.

    Args:
        cli: The in-process CLI with a fake embedder.
        tmp_path: Temporary folder provided by pytest.
        capsys: Captures what the command prints.

    Returns:
        What the command wrote to stderr.
    """
    capsys.readouterr()
    run(
        cli,
        [
            "index",
            "--max_chunk_size", "30",
            "--raw_directory", str(tmp_path / "corpus"),
            "--index_path", str(tmp_path / "index.db"),
            "--semantic",
            "--vectors_path", str(tmp_path / "embeddings.db"),
        ],
    )
    return capsys.readouterr().err


def test_semantic_summary_counts_added_and_removed_text(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Adding text writes chunks; deleting it removes chunks and orphans."""
    corpus = tmp_path / "corpus"
    corpus.mkdir()
    document = corpus / "a.md"
    document.write_text(SECTIONS, encoding="utf-8")
    cli = make_cli(FakeEmbedderLoader())
    reindex_semantic(cli, tmp_path, capsys)

    document.write_text(SECTIONS + "\n# Four\nfourth\n", encoding="utf-8")
    added = reindex_semantic(cli, tmp_path, capsys)
    assert "0 removed" not in added
    assert "Orphaned" not in added or "Orphaned: 0" not in added

    document.write_text("# One\nfirst words\n", encoding="utf-8")
    deleted = reindex_semantic(cli, tmp_path, capsys)
    assert "removed)" in deleted and "0 removed" not in deleted
    assert "Orphaned:" in deleted
    assert "(kept, not deleted)" in deleted


def test_semantic_summary_is_zero_when_nothing_changed(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """A second run with the same corpus removes and orphans nothing."""
    corpus = tmp_path / "corpus"
    corpus.mkdir()
    (corpus / "a.md").write_text(SECTIONS, encoding="utf-8")
    cli = make_cli(FakeEmbedderLoader())
    reindex_semantic(cli, tmp_path, capsys)

    again = reindex_semantic(cli, tmp_path, capsys)

    assert "0 written, 0 removed" in again
    assert "Orphaned" not in again


class SpyStore:
    """Stand-in for any adapter that records every call made to it."""

    def __init__(self) -> None:
        """Start with no recorded calls."""
        self.calls: list[str] = []

    def __getattr__(self, name: str) -> object:
        """Record the call and refuse to work.

        Args:
            name: Attribute the code under test asked for.

        Raises:
            AssertionError: Always; nothing should be touched.
        """
        self.calls.append(name)
        raise AssertionError(f"adapter used: {name}")


def make_spy_cli() -> tuple[RagCli, SpyStore]:
    """Build a CLI whose adapters fail the test if they are used.

    Returns:
        The CLI and the spy shared by its adapters.
    """
    spy = SpyStore()
    cli = RagCli(spy, spy, spy, spy, spy, spy)  # type: ignore[arg-type]
    return cli, spy


@pytest.mark.parametrize("words", [
    ["index", "--flagmalo"],
    ["index", "--embeddings"],
    ["index", "--max_chunk_size", "500", "--flagmalo"],
    ["index", "--flagmalo=3"],
    ["search", "hello", "--kk", "3"],
])
def test_unknown_flag_runs_nothing(
    words: list[str], capsys: pytest.CaptureFixture[str]
) -> None:
    """An unknown flag stops everything before any adapter is touched."""
    cli, spy = make_spy_cli()

    exit_code = run(cli, words)

    assert exit_code == 2
    assert spy.calls == []
    err = capsys.readouterr().err
    assert "unknown flag" in err and "Valid flags:" in err
    assert "--index_path" in err
    assert "Traceback" not in err


def test_unknown_command_runs_nothing(
    capsys: pytest.CaptureFixture[str]
) -> None:
    """An unknown command lists the valid ones and exits with 2."""
    cli, spy = make_spy_cli()

    assert run(cli, ["bogus"]) == 2
    assert spy.calls == []
    assert "Valid commands:" in capsys.readouterr().err


@pytest.mark.parametrize("words", [
    ["index", "--max_chunk_size", "500"],
    ["index", "--max-chunk-size=500", "--semantic", "--noincremental"],
    ["search", "--query=-x", "--k", "3"],
    ["search", "hello world", "--k", "-1"],
    ["search", "hello", "--k=-1"],
    ["search", "--query=-foo bar", "--k", "0"],
    ["search", "x", "--index_path=/ruta con espacios/i.db"],
    ["index", "--help"],
    [],
])
def test_valid_words_pass_the_prevalidation(words: list[str]) -> None:
    """Valid commands, flags, negatives and help are left to Fire."""
    cli, _ = make_spy_cli()

    assert usage_error(cli, words) is None


def test_valid_flags_still_run(tmp_path: Path) -> None:
    """A real index run with valid flags still succeeds."""
    corpus = tmp_path / "corpus"
    corpus.mkdir()
    (corpus / "a.md").write_text(SECTIONS, encoding="utf-8")
    cli = make_cli(FakeEmbedderLoader())

    exit_code = run(cli, [
        "index", "--raw_directory", str(corpus),
        "--index_path", str(tmp_path / "i.db"),
    ])

    assert exit_code == 0
    assert (tmp_path / "i.db").exists()


@pytest.mark.parametrize("count, expected", [
    (1, "1 stored vector no longer matches any chunk text"),
    (9, "9 stored vectors no longer match any chunk text"),
])
def test_orphan_line_agrees_in_number(count: int, expected: str) -> None:
    """The orphan line is singular for 1 and plural otherwise."""
    report = EmbedReport(
        total_count=5, new_count=1, orphaned_count=count
    )

    assert expected in vectors_summary(report, 1.0)


def test_one_token_with_several_flags_is_rejected(
    capsys: pytest.CaptureFixture[str]
) -> None:
    """The accident: one quoted token holding flags must run nothing."""
    cli, spy = make_spy_cli()

    exit_code = run(
        cli, ["index", "--raw_directory /x --index_path /y --vectors_path /z"]
    )

    assert exit_code == 2
    assert spy.calls == []
    err = capsys.readouterr().err
    assert "unknown flag" in err and "Valid flags:" in err


def test_self_is_not_a_valid_flag() -> None:
    """``--self`` is rejected and never listed among the valid flags."""
    message = usage_error(RagCli, ["index", "--self"])

    assert message is not None and "unknown flag '--self'" in message
    valid_part = message.split("Valid flags:")[1]
    assert "self" not in valid_part
