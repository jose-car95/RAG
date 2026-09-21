"""Tests for splitting Markdown and plain text into chunks."""

import pytest

from src.domain.chunking import chunk_text

MARKDOWN_SAMPLE = (
    "Intro line before any heading.\n\n"
    "# Title\n"
    "First paragraph of the title section.\n\n"
    "Second paragraph, a bit longer than the first one.\n\n"
    "## Subsection\n"
    "Text of the subsection.\n"
    "```python\n"
    "print('code block')\n"
    "```\n\n"
    "# Another title\n"
    "Last words.\n"
)


def assert_valid_chunks(
    text: str, chunks: list[tuple[int, int]], max_chunk_size: int
) -> None:
    """Check the chunk invariant: ordered, contiguous, bounded and exact.

    Args:
        text: The text that was chunked.
        chunks: The ``(first, last)`` ranges returned for it.
        max_chunk_size: The maximum width that was requested.
    """
    position = 0
    for first, last in chunks:
        assert first == position, "chunks must not leave gaps or overlap"
        assert first < last, "chunks must not be empty"
        assert last - first <= max_chunk_size, "chunk wider than the limit"
        position = last
    assert position == len(text), "chunks must reach the end of the text"
    assert "".join(text[first:last] for first, last in chunks) == text


def test_headings_start_new_chunks() -> None:
    """Each Markdown section becomes its own chunk."""
    text = "# A\nuno\n\n# B\ndos\n"

    assert chunk_text(text, 2000) == [(0, 9), (9, 17)]


def test_text_before_the_first_heading_is_kept() -> None:
    """An introduction before the first heading is its own chunk."""
    text = "intro\n\n# A\nuno\n"

    assert chunk_text(text, 2000) == [(0, 7), (7, 15)]


def test_small_text_without_headings_is_one_chunk() -> None:
    """A text that fits and has no headings stays whole."""
    text = "hola\nmundo\n"

    assert chunk_text(text, 2000) == [(0, 11)]


def test_empty_text_has_no_chunks() -> None:
    """There is nothing to chunk in an empty text."""
    assert chunk_text("", 2000) == []


def test_long_section_is_cut_after_blank_lines() -> None:
    """A section that does not fit is split between paragraphs."""
    text = "# Big\n" + ("word " * 20 + "\n\n") * 60

    chunks = chunk_text(text, 2000)

    assert len(chunks) > 1
    assert_valid_chunks(text, chunks, 2000)
    for first, _ in chunks[1:]:
        assert text[first - 2:first] == "\n\n"


def test_long_paragraph_is_hard_cut() -> None:
    """A single paragraph wider than the limit is cut as a last resort."""
    text = "x" * 5000

    assert chunk_text(text, 2000) == [(0, 2000), (2000, 4000), (4000, 5000)]


@pytest.mark.parametrize("max_chunk_size", [2000, 60, 25, 1])
@pytest.mark.parametrize(
    "text",
    [MARKDOWN_SAMPLE, "no headings\n\nat all\n", "# Only a title", "\n\n\n"],
    ids=["markdown", "plain", "title_only", "blank_lines"],
)
def test_chunks_always_rebuild_the_text(
    text: str, max_chunk_size: int
) -> None:
    """The invariant holds for any text and any limit."""
    assert_valid_chunks(text, chunk_text(text, max_chunk_size), max_chunk_size)
