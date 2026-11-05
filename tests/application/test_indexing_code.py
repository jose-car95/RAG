"""Tests for the code version: the fingerprint of the indexing code."""

import string

import pytest

from src.application.use_cases.shared import indexing_code
from src.application.use_cases.shared.indexing_code import code_version
from src.domain import bm25, chunking, tokenizer


def test_the_code_version_is_a_sha256_digest() -> None:
    """64 hexadecimal characters, the same on every call."""
    version = code_version()

    assert len(version) == 64
    assert set(version) <= set(string.hexdigits)
    assert code_version() == version


def test_the_indexing_modules_are_the_ones_that_shape_the_index() -> None:
    """Chunking, tokenizing and BM25 decide what the caches hold."""
    assert indexing_code.INDEXING_MODULES == (chunking, tokenizer, bm25)


def test_the_code_version_changes_with_the_code(
    monkeypatch: pytest.MonkeyPatch
) -> None:
    """Different source code, different version."""
    before = code_version()

    monkeypatch.setattr(indexing_code, "INDEXING_MODULES", (chunking,))

    assert code_version() != before
