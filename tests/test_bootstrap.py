"""Tests for the composition root's environment settings."""

import pytest

from src.adapters.inbound.api.app import DEFAULT_CORS_ORIGINS
from src.bootstrap import read_cors_origins


def test_cors_origins_default_to_the_local_frontend(
    monkeypatch: pytest.MonkeyPatch
) -> None:
    """Without the variable, the local frontend origins are allowed."""
    monkeypatch.delenv("RAG_CORS_ORIGINS", raising=False)

    assert read_cors_origins() == list(DEFAULT_CORS_ORIGINS)


def test_cors_origins_come_from_the_environment(
    monkeypatch: pytest.MonkeyPatch
) -> None:
    """A comma-separated list is split and stripped; blanks are dropped."""
    monkeypatch.setenv("RAG_CORS_ORIGINS", "http://a.test, http://b.test,")

    assert read_cors_origins() == ["http://a.test", "http://b.test"]
