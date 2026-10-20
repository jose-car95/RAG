"""Tests for the answer use case: one question, its sources, one answer.

The model is always a fake: loading Qwen would need 1.5 GB of weights and
seconds per test. The fake records what it receives, so the tests can check
both the prompt it got and whether it was loaded at all.
"""

import re
from pathlib import Path

import pytest

from src.adapters.outbound.corpus import FileCorpus
from src.adapters.outbound.sqlite_index import SqliteIndexStore
from src.application.use_cases.answer import (
    NO_SOURCES_ANSWER,
    PROMPT_BUDGET,
    answer_from_sources,
    run_answer,
)
from src.application.use_cases.index_corpus import run_index
from src.domain.models import MinimalSource
from src.domain.prompt import Prompt

CORPUS = FileCorpus()
STORE = SqliteIndexStore()
MD_FILE = "# Endpoints\nThe http endpoint loads a lora adapter.\n"


class FakeGenerator:
    """Stands in for Qwen: counts words and records every prompt."""

    def __init__(self) -> None:
        """Start with no prompts and no counts."""
        self.prompts: list[Prompt] = []
        self.counted = 0

    def count_tokens(self, text: str) -> int:
        """Count words as tokens.

        Args:
            text: Any text.

        Returns:
            Its number of words.
        """
        self.counted += 1
        return len(text.split())

    def generate(self, prompt: Prompt) -> str:
        """Record the prompt and give a fixed answer.

        Args:
            prompt: The system and user parts built by the use case.

        Returns:
            Always the same answer.
        """
        self.prompts.append(prompt)
        return "Use the load_lora_adapter endpoint."


class FakeLoader:
    """Hands out one ``FakeGenerator`` and counts how often it is loaded."""

    def __init__(self) -> None:
        """Create the generator, not loaded yet."""
        self.generator = FakeGenerator()
        self.loads = 0

    def __call__(self) -> FakeGenerator:
        """Load the fake model.

        Returns:
            The fake generator.
        """
        self.loads += 1
        return self.generator


def make_index(tmp_path: Path) -> Path:
    """Build a one-file index and return its path.

    Args:
        tmp_path: Temporary folder provided by pytest.

    Returns:
        The index file.
    """
    corpus = tmp_path / "corpus"
    corpus.mkdir()
    (corpus / "lora.md").write_text(MD_FILE, encoding="utf-8")
    index_path = tmp_path / "processed" / "index.db"
    run_index(str(corpus), 2000, str(index_path), CORPUS, STORE)
    return index_path


def test_answer_comes_from_the_model(tmp_path: Path) -> None:
    """The prompt holds the source text and the question; the model answers."""
    index_path = make_index(tmp_path)
    loader = FakeLoader()

    answer = run_answer(
        "lora endpoint", 5, str(index_path), STORE, CORPUS, loader
    )

    assert answer == "Use the load_lora_adapter endpoint."
    assert loader.loads == 1
    [prompt] = loader.generator.prompts
    assert "The http endpoint loads a lora adapter." in prompt.user
    assert "lora.md" in prompt.user
    assert prompt.user.endswith("Question: lora endpoint")


def test_prompt_is_measured_with_the_model_tokenizer(tmp_path: Path) -> None:
    """Tokens are counted by the loaded model, within the agreed budget."""
    index_path = make_index(tmp_path)
    loader = FakeLoader()

    run_answer("lora endpoint", 5, str(index_path), STORE, CORPUS, loader)

    assert loader.generator.counted > 0
    assert PROMPT_BUDGET == 2000


def test_no_sources_means_no_model(tmp_path: Path) -> None:
    """With nothing retrieved there is nothing to ground an answer on."""
    index_path = make_index(tmp_path)
    loader = FakeLoader()

    answer = run_answer("asdfghjkl", 5, str(index_path), STORE, CORPUS, loader)

    assert answer == NO_SOURCES_ANSWER
    assert loader.loads == 0


@pytest.mark.parametrize(
    ("query", "k", "message"),
    [
        ("", 5, "query must not be empty"),
        ("   ", 5, "query must not be empty"),
        ("What is vLLM?", 0, "k must be a positive integer"),
        ("What is vLLM?", -3, "k must be a positive integer"),
    ],
)
def test_bad_arguments_fail_before_loading_anything(
    tmp_path: Path, query: str, k: int, message: str
) -> None:
    """Rejected before the index or the model: the index does not exist."""
    loader = FakeLoader()

    with pytest.raises(ValueError, match=re.escape(message)):
        run_answer(
            query, k, str(tmp_path / "missing.db"), STORE, CORPUS, loader
        )
    assert loader.loads == 0


def test_missing_index_is_reported_without_the_model(tmp_path: Path) -> None:
    """A clear error about the index, and the model never loaded."""
    loader = FakeLoader()

    with pytest.raises(ValueError, match="index not found"):
        run_answer(
            "lora", 5, str(tmp_path / "missing.db"), STORE, CORPUS, loader
        )
    assert loader.loads == 0


def test_answer_from_sources_reads_them_and_asks_the_model(
    tmp_path: Path
) -> None:
    """Given sources, no search: their text goes into the prompt."""
    path = tmp_path / "lora.md"
    path.write_text(MD_FILE, encoding="utf-8")
    source = MinimalSource(
        file_path=str(path),
        first_character_index=12,
        last_character_index=51,
    )
    generator = FakeGenerator()

    answer = answer_from_sources("lora endpoint", [source], CORPUS, generator)

    assert answer == "Use the load_lora_adapter endpoint."
    [prompt] = generator.prompts
    assert "The http endpoint loads a lora adapter." in prompt.user
    assert f'path="{path}"' in prompt.user
    assert prompt.user.endswith("Question: lora endpoint")
