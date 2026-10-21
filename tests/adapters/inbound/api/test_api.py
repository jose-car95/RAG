"""Tests for the local HTTP API (bonus).

``TestClient`` sends requests to the app in memory, without opening a port.
The model is the fake of ``test_answer.py``, so no test needs Qwen.
"""

from pathlib import Path

from fastapi.testclient import TestClient

from src.adapters.inbound.api.app import create_app
from tests.application.test_answer import (
    CORPUS,
    STORE,
    FakeLoader,
    make_index,
)


def make_client(index_path: Path, loader: FakeLoader) -> TestClient:
    """Build the app on a test index and wrap it in a client.

    Args:
        index_path: Index the app searches.
        loader: Fake model loader.

    Returns:
        A client that calls the app directly.
    """
    return TestClient(create_app(STORE, CORPUS, loader, str(index_path)))


def test_health_says_the_api_is_up(tmp_path: Path) -> None:
    """A cheap check that the server answers, without touching the index."""
    client = make_client(tmp_path / "index.db", FakeLoader())

    response = client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_search_returns_the_sources_of_the_question(tmp_path: Path) -> None:
    """Same sources as the CLI, with the question echoed back."""
    client = make_client(make_index(tmp_path), FakeLoader())

    response = client.post(
        "/api/v1/search", json={"query": "lora adapter", "k": 3}
    )

    assert response.status_code == 200
    body = response.json()
    assert body["question"] == "lora adapter"
    assert [source["file_path"] for source in body["retrieved_sources"]] == [
        str(tmp_path / "corpus" / "lora.md")
    ]


def test_answer_returns_the_model_answer(tmp_path: Path) -> None:
    """The answer comes from the model, grounded in the retrieved source."""
    client = make_client(make_index(tmp_path), FakeLoader())

    response = client.post("/api/v1/answer", json={"query": "lora adapter"})

    assert response.status_code == 200
    assert response.json() == {
        "question": "lora adapter",
        "answer": "Use the load_lora_adapter endpoint.",
    }


def test_the_model_is_loaded_once_for_every_request(tmp_path: Path) -> None:
    """Loading Qwen takes seconds: the server pays it a single time."""
    loader = FakeLoader()
    client = make_client(make_index(tmp_path), loader)

    for _ in range(3):
        client.post("/api/v1/answer", json={"query": "lora adapter"})

    assert loader.loads == 1


def test_a_user_error_is_a_400_with_the_cli_message(tmp_path: Path) -> None:
    """The same rule and message as ``search ""`` in the CLI."""
    client = make_client(make_index(tmp_path), FakeLoader())

    response = client.post("/api/v1/search", json={"query": "", "k": 3})

    assert response.status_code == 400
    assert response.json() == {"detail": "query must not be empty"}


def test_a_missing_index_is_a_400(tmp_path: Path) -> None:
    """Asking before indexing says what to run, and the model never loads."""
    index_path = tmp_path / "index.db"
    loader = FakeLoader()
    client = make_client(index_path, loader)

    response = client.post("/api/v1/answer", json={"query": "lora adapter"})

    assert response.status_code == 400
    assert response.json() == {
        "detail": f"index not found: {index_path}; run index first"
    }
    assert loader.loads == 0


def test_a_malformed_body_is_a_422(tmp_path: Path) -> None:
    """pydantic rejects the body before any use case runs."""
    client = make_client(make_index(tmp_path), FakeLoader())

    response = client.post("/api/v1/search", json={"k": "many"})

    assert response.status_code == 422
