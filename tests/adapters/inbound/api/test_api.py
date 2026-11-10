"""Tests for the local HTTP API (bonus).

``TestClient`` sends requests to the app in memory, without opening a port.
The model is the fake of ``test_answer.py``, so no test needs Qwen.
"""

from pathlib import Path

from fastapi.testclient import TestClient

from src.adapters.inbound.api.app import create_app
from src.application.ports.index_store import IndexStore
from src.application.use_cases.index_corpus import run_index
from tests.application.test_answer import (
    CORPUS,
    STORE,
    FakeLoader,
    make_index,
)
from tests.application.test_search_dataset import CountingStore


def make_client(
    index_path: Path, loader: FakeLoader, store: IndexStore = STORE
) -> TestClient:
    """Build the app on a test index and wrap it in a client.

    Args:
        index_path: Index the app searches.
        loader: Fake model loader.
        store: Where the index is read from.

    Returns:
        A client that calls the app directly.
    """
    return TestClient(create_app(store, CORPUS, loader, str(index_path)))


def test_the_api_does_not_serve_the_frontend(tmp_path: Path) -> None:
    """Frontend and API are separate servers: the API only has its routes."""
    client = make_client(tmp_path / "index.db", FakeLoader())

    assert client.get("/").status_code == 404
    assert client.get("/app.js").status_code == 404
    assert client.get("/api/v1/health").status_code == 200


def test_cors_allows_the_frontend_origin(tmp_path: Path) -> None:
    """A preflight and a real call from the default frontend origin pass."""
    client = make_client(tmp_path / "index.db", FakeLoader())
    origin = "http://127.0.0.1:8080"

    preflight = client.options(
        "/api/v1/search",
        headers={
            "Origin": origin,
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        },
    )
    assert preflight.status_code == 200
    assert preflight.headers["access-control-allow-origin"] == origin

    health = client.get("/api/v1/health", headers={"Origin": origin})
    assert health.headers["access-control-allow-origin"] == origin


def test_cors_rejects_other_origins(tmp_path: Path) -> None:
    """An origin that is not in the list gets no allow header."""
    client = make_client(tmp_path / "index.db", FakeLoader())
    evil = "http://evil.example"

    preflight = client.options(
        "/api/v1/search",
        headers={"Origin": evil, "Access-Control-Request-Method": "POST"},
    )
    assert preflight.status_code == 400
    assert "access-control-allow-origin" not in preflight.headers

    health = client.get("/api/v1/health", headers={"Origin": evil})
    assert "access-control-allow-origin" not in health.headers


def test_cors_origins_are_configurable(tmp_path: Path) -> None:
    """The origins come from create_app, so a deployment can change them."""
    app = create_app(
        STORE, CORPUS, FakeLoader(), str(tmp_path / "index.db"),
        cors_origins=["http://frontend.test"],
    )
    client = TestClient(app)

    allowed = client.get(
        "/api/v1/health", headers={"Origin": "http://frontend.test"}
    )
    default = client.get(
        "/api/v1/health", headers={"Origin": "http://127.0.0.1:3000"}
    )

    assert allowed.headers["access-control-allow-origin"] == (
        "http://frontend.test"
    )
    assert "access-control-allow-origin" not in default.headers


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


def test_the_index_is_read_once_for_every_request(tmp_path: Path) -> None:
    """Building the index takes seconds: the server keeps it in memory."""
    store = CountingStore()
    client = make_client(make_index(tmp_path), FakeLoader(), store)

    client.post("/api/v1/search", json={"query": "lora adapter"})
    client.post("/api/v1/search", json={"query": "lora adapter"})
    client.post("/api/v1/answer", json={"query": "lora adapter"})

    assert store.loads == 1


def test_a_repeated_question_reaches_the_model_once(tmp_path: Path) -> None:
    """The second answer to the same question comes from the cache."""
    loader = FakeLoader()
    client = make_client(make_index(tmp_path), loader)

    first = client.post("/api/v1/answer", json={"query": "lora adapter"})
    second = client.post("/api/v1/answer", json={"query": "lora adapter"})

    assert second.json() == first.json()
    assert len(loader.generator.prompts) == 1


def test_a_rebuilt_index_is_answered_again(tmp_path: Path) -> None:
    """Cached results belong to one version of the index."""
    index_path = make_index(tmp_path)
    loader = FakeLoader()
    client = make_client(index_path, loader)
    client.post("/api/v1/answer", json={"query": "lora adapter"})
    corpus = tmp_path / "corpus"
    (corpus / "kv.md").write_text("# Cache\nThe kv cache blocks.\n")
    run_index(str(corpus), 2000, str(index_path), CORPUS, STORE)

    client.post("/api/v1/answer", json={"query": "lora adapter"})

    assert len(loader.generator.prompts) == 2


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
