"""Tests for the data models required by the subject (VI.4)."""

import json
import uuid
from pathlib import Path

import pytest
from pydantic import ValidationError

from src.domain.models import (
    AnsweredQuestion,
    MinimalAnswer,
    MinimalSearchResults,
    MinimalSource,
    RagDataset,
    StudentSearchResults,
    StudentSearchResultsAndAnswer,
    UnansweredQuestion,
)

DATASETS = Path(__file__).resolve().parents[2] / "data" / "datasets"


def load_dataset(relative_path: str) -> RagDataset:
    """Validate one of the public dataset files as a ``RagDataset``.

    Args:
        relative_path: Path of the file inside ``data/datasets/``.

    Returns:
        The validated dataset.
    """
    with open(DATASETS / relative_path, encoding="utf-8") as file:
        return RagDataset.model_validate(json.load(file))


def test_answered_dataset_loads_answered_questions() -> None:
    """Questions with sources and answer become ``AnsweredQuestion``."""
    dataset = load_dataset("AnsweredQuestions/dataset_docs_public.json")

    assert len(dataset.rag_questions) == 100
    assert all(
        type(question) is AnsweredQuestion
        for question in dataset.rag_questions
    )


def test_unanswered_dataset_loads_unanswered_questions() -> None:
    """Questions without sources or answer become ``UnansweredQuestion``."""
    dataset = load_dataset("UnansweredQuestions/dataset_code_public.json")

    assert len(dataset.rag_questions) == 99
    assert all(
        type(question) is UnansweredQuestion
        for question in dataset.rag_questions
    )


def test_extra_fields_are_ignored() -> None:
    """Fields the subject does not define are accepted and dropped."""
    question = AnsweredQuestion.model_validate(
        {
            "question_id": "q1",
            "question": "What is vLLM?",
            "answer": "A library for LLM inference.",
            "sources": [],
            "difficulty": "synthetic",
            "is_valid": True,
        }
    )

    assert set(question.model_dump()) == {
        "question_id",
        "question",
        "answer",
        "sources",
    }


def test_missing_question_id_gets_a_uuid() -> None:
    """A question without id receives a new, unique UUID string."""
    first = UnansweredQuestion(question="What is vLLM?")
    second = UnansweredQuestion(question="What is vLLM?")

    assert str(uuid.UUID(first.question_id)) == first.question_id
    assert first.question_id != second.question_id


def test_source_without_file_path_is_rejected() -> None:
    """``file_path`` is required."""
    with pytest.raises(ValidationError):
        MinimalSource.model_validate(
            {"first_character_index": 0, "last_character_index": 10}
        )


def test_valid_source_range_is_accepted() -> None:
    """A real range from the public dataset is accepted unchanged."""
    source = MinimalSource(
        file_path="data/raw/vllm-0.10.1/docs/features/lora.md",
        first_character_index=4695,
        last_character_index=6098,
    )

    assert source.last_character_index == 6098


def test_inverted_source_range_is_rejected() -> None:
    """A range cannot start after it ends (decision B)."""
    with pytest.raises(ValidationError):
        MinimalSource(
            file_path="data/raw/vllm-0.10.1/docs/features/lora.md",
            first_character_index=500,
            last_character_index=10,
        )


def test_negative_source_index_is_rejected() -> None:
    """A negative index would silently count from the end (decision B)."""
    with pytest.raises(ValidationError):
        MinimalSource(
            file_path="data/raw/vllm-0.10.1/docs/features/lora.md",
            first_character_index=-5,
            last_character_index=10,
        )


def test_search_results_keep_question_and_retrieved_sources() -> None:
    """One question's search output keeps its id, text and sources."""
    result = MinimalSearchResults(
        question_id="q1",
        question="What is vLLM?",
        retrieved_sources=[],
    )
    output = StudentSearchResults(search_results=[result], k=5)

    assert json.loads(output.model_dump_json()) == {
        "search_results": [
            {
                "question_id": "q1",
                "question": "What is vLLM?",
                "retrieved_sources": [],
            }
        ],
        "k": 5,
    }


def test_empty_search_results_serialise_to_subject_json() -> None:
    """The search output has exactly the subject's shape."""
    results = StudentSearchResults(search_results=[], k=10)

    assert json.loads(results.model_dump_json()) == {
        "search_results": [],
        "k": 10,
    }


def test_answers_output_nests_sources_and_answer() -> None:
    """The answer output keeps question, sources and answer together."""
    source = MinimalSource(
        file_path="data/raw/vllm-0.10.1/docs/features/lora.md",
        first_character_index=4695,
        last_character_index=6098,
    )
    answer = MinimalAnswer(
        question_id="q1",
        question="What HTTP endpoint loads a LoRA adapter?",
        retrieved_sources=[source],
        answer="POST /v1/load_lora_adapter",
    )
    output = StudentSearchResultsAndAnswer(search_results=[answer], k=1)

    dumped = json.loads(output.model_dump_json())
    assert dumped["k"] == 1
    assert dumped["search_results"][0]["answer"] == (
        "POST /v1/load_lora_adapter"
    )
    assert dumped["search_results"][0]["retrieved_sources"][0] == {
        "file_path": "data/raw/vllm-0.10.1/docs/features/lora.md",
        "first_character_index": 4695,
        "last_character_index": 6098,
    }
