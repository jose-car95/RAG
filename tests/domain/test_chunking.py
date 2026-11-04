"""Tests for splitting Markdown and plain text into chunks."""

import pytest

from src.domain.chunking import (
    chunk_python,
    chunk_text,
    context_for_offset,
    definition_spans,
    heading_breadcrumb,
)

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


PYTHON_SAMPLE = (
    "import os\n"
    "\n"
    "VALUE = 1\n"
    "\n"
    "\n"
    "def first() -> int:\n"
    "    return 1\n"
    "\n"
    "\n"
    "@staticmethod\n"
    "def second() -> int:\n"
    "    return 2\n"
)

BROKEN_PYTHON = "def broken(:\n\n# Title\nsome text\n"


CLASS_SAMPLE = (
    "import os\n"
    "\n"
    "\n"
    "class Engine:\n"
    "    def start(self) -> None:\n"
    "        return None\n"
    "\n"
    "\n"
    "def helper() -> int:\n"
    "    return 1\n"
)


def test_definition_spans_names_each_top_level_definition() -> None:
    """Each top-level class and def, with the range it covers."""
    spans = definition_spans(CLASS_SAMPLE)

    names = [name for _, _, name in spans]
    assert names == ["Engine", "helper"]


def test_context_for_offset_finds_the_enclosing_definition() -> None:
    """An offset inside a class gets its name; outside, the empty string."""
    spans = definition_spans(CLASS_SAMPLE)
    inside_engine = CLASS_SAMPLE.index("return None")
    inside_helper = CLASS_SAMPLE.index("return 1")
    at_import = CLASS_SAMPLE.index("import os")

    assert context_for_offset(spans, inside_engine) == "Engine"
    assert context_for_offset(spans, inside_helper) == "helper"
    assert context_for_offset(spans, at_import) == ""


def test_definition_spans_of_unparsable_source_is_empty() -> None:
    """Source that does not parse has no spans instead of raising."""
    assert definition_spans(BROKEN_PYTHON) == []


HEADING_SAMPLE = (
    "# Quantization\n"           # 0
    "intro\n\n"                  # 15
    "## Supported hardware\n"    # 22
    "amd and nvidia\n\n"         # 43
    "### Notes\n"                # 58
    "detail\n"                   # 68
)


def test_heading_breadcrumb_trails_the_enclosing_headings() -> None:
    """A chunk carries every heading open above it, outermost first."""
    at_intro = HEADING_SAMPLE.index("intro")
    at_amd = HEADING_SAMPLE.index("amd")
    at_detail = HEADING_SAMPLE.index("detail")

    assert heading_breadcrumb(HEADING_SAMPLE, at_intro) == "# Quantization"
    assert heading_breadcrumb(HEADING_SAMPLE, at_amd) == (
        "# Quantization ## Supported hardware"
    )
    assert heading_breadcrumb(HEADING_SAMPLE, at_detail) == (
        "# Quantization ## Supported hardware ### Notes"
    )


def test_heading_breadcrumb_excludes_a_heading_at_the_offset() -> None:
    """A chunk starting on a heading does not repeat it; it keeps ancestors."""
    at_subheading = HEADING_SAMPLE.index("## Supported")

    assert heading_breadcrumb(
        HEADING_SAMPLE, at_subheading
    ) == "# Quantization"


def test_heading_breadcrumb_is_empty_before_any_heading() -> None:
    """Text before the first heading has no breadcrumb."""
    assert heading_breadcrumb("plain text, no heading", 5) == ""


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


def test_top_level_definitions_start_new_chunks() -> None:
    """The header and each top-level definition become their own chunk."""
    assert chunk_python(PYTHON_SAMPLE, 2000) == [(0, 23), (23, 58), (58, 106)]


def test_decorator_stays_with_its_function() -> None:
    """A decorator belongs to the chunk of the function it decorates."""
    chunks = chunk_python(PYTHON_SAMPLE, 2000)

    first, last = chunks[-1]
    assert PYTHON_SAMPLE[first:last].startswith("@staticmethod\n")


def test_long_function_is_cut_after_blank_lines() -> None:
    """A function that does not fit is split between its blank lines."""
    source = "def big() -> None:\n" + "    value = 1\n\n" * 400

    chunks = chunk_python(source, 2000)

    assert len(chunks) > 1
    assert_valid_chunks(source, chunks, 2000)
    for first, _ in chunks[1:]:
        assert source[first - 2:first] == "\n\n"


def test_long_function_without_blank_lines_is_hard_cut() -> None:
    """Without blank lines the only way out is a hard cut."""
    source = "def big() -> None:\n" + "    value = 1\n" * 400

    chunks = chunk_python(source, 2000)

    assert_valid_chunks(source, chunks, 2000)
    assert max(last - first for first, last in chunks) == 2000


def test_invalid_python_falls_back_to_text_chunking() -> None:
    """Source that does not parse is chunked as plain text."""
    assert chunk_python(BROKEN_PYTHON, 2000) == chunk_text(BROKEN_PYTHON, 2000)


def test_null_byte_python_falls_back_to_text_chunking() -> None:
    """A null byte breaks parsing on every version without crashing."""
    source = "x = 1\x00\n"

    assert chunk_python(source, 2000) == chunk_text(source, 2000)


def test_empty_source_has_no_chunks() -> None:
    """There is nothing to chunk in an empty source file."""
    assert chunk_python("", 2000) == []


@pytest.mark.parametrize("max_chunk_size", [2000, 60, 1])
@pytest.mark.parametrize(
    "source",
    [PYTHON_SAMPLE, BROKEN_PYTHON, "x = 1\n"],
    ids=["sample", "broken", "one_line"],
)
def test_python_chunks_always_rebuild_the_source(
    source: str, max_chunk_size: int
) -> None:
    """The invariant holds for Python sources too."""
    assert_valid_chunks(
        source, chunk_python(source, max_chunk_size), max_chunk_size
    )
