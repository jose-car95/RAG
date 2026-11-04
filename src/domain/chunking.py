"""Split Markdown, plain text and Python source into chunk ranges.

A chunk is a ``(first, last)`` range with an exclusive end, so its text is
``text[first:last]`` and its width is ``last - first``. The public entry
points are ``chunk_text`` and ``chunk_python``; the rest is internal.
"""

import ast
from collections.abc import Callable


def _hard_split(
    start: int,
    end: int,
    max_chunk_size: int
) -> list[tuple[int, int]]:
    """Cut a range into consecutive pieces of at most ``max_chunk_size``.

    Last resort, used when a paragraph does not fit by itself.

    Args:
        start: First character of the range.
        end: First character after the range.
        max_chunk_size: Maximum width of a piece.

    Returns:
        The pieces, covering the whole range in order.
    """
    pieces: list[tuple[int, int]] = []
    for piece_start in range(start, end, max_chunk_size):
        piece_end = min(piece_start + max_chunk_size, end)
        pieces.append((piece_start, piece_end))
    return pieces


def _split_range(
    start: int,
    end: int,
    cuts: list[int]
) -> list[tuple[int, int]]:
    """Split a range at the cut positions that fall strictly inside it.

    Args:
        start: First character of the range.
        end: First character after the range.
        cuts: Candidate cut positions, in any order.

    Returns:
        The resulting ranges in order, or an empty list for an empty range.
    """
    if start >= end:
        return []
    inside_cuts: list[int] = []
    for cut in cuts:
        if start < cut < end:
            inside_cuts.append(cut)
    boundaries = [start] + inside_cuts + [end]
    ranges: list[tuple[int, int]] = []
    for range_start, range_end in zip(boundaries, boundaries[1:]):
        ranges.append((range_start, range_end))
    return ranges


def _heading_starts(text: str) -> list[int]:
    """Find the position where each Markdown heading line starts.

    A heading is a line starting with one to six ``#`` followed by a space,
    so a tag such as ``#nospace`` is not one.

    ponytail: a line like ``# comment`` inside a fenced code block also
    counts, which only adds one extra cut and keeps the invariant; detecting
    code fences would be more logic for a rare case. Revisit if M4 shows it
    hurts recall.

    Args:
        text: Text to inspect.

    Returns:
        The positions, in the order they appear.
    """
    positions: list[int] = []
    offset: int = 0
    for line in text.splitlines(keepends=True):
        hash_count = len(line) - len(line.lstrip("#"))
        if 1 <= hash_count <= 6 and line[hash_count:hash_count + 1] == " ":
            positions.append(offset)
        offset += len(line)
    return positions


def _paragraph_starts(text: str) -> list[int]:
    """Find the position where each paragraph starts, after a blank line.

    The blank line stays with the paragraph before it, so that chunks built
    from these positions leave no gaps.

    Args:
        text: Text to inspect.

    Returns:
        The positions, in the order they appear.
    """
    positions: list[int] = []
    offset: int = 0
    for line in text.splitlines(keepends=True):
        offset += len(line)
        if line.strip() == "":
            positions.append(offset)
    return positions


def _pack(
    pieces: list[tuple[int, int]],
    max_chunk_size: int
) -> list[tuple[int, int]]:
    """Join consecutive pieces while they fit in ``max_chunk_size``.

    Greedy: every piece extends the chunk that is still open when it fits,
    or opens a new one; a piece wider than the limit is hard split.

    Args:
        pieces: Consecutive ranges covering a section, in order.
        max_chunk_size: Maximum width of a chunk.

    Returns:
        The chunks, covering the same text in order.
    """
    chunks: list[tuple[int, int]] = []
    for first, last in pieces:
        if last - first > max_chunk_size:
            chunks.extend(_hard_split(first, last, max_chunk_size))
            continue
        if (
            chunks
            and chunks[-1][1] == first
            and last - chunks[-1][0] <= max_chunk_size
        ):
            chunks[-1] = (chunks[-1][0], last)
        else:
            chunks.append((first, last))
    return chunks


def _chunk_with_cuts(
    text: str, cuts: list[int], max_chunk_size: int
) -> list[tuple[int, int]]:
    """Split a text at the given cuts, keeping every chunk within the limit.

    Shared by both strategies: only the cuts change. A section that does not
    fit is split between paragraphs and, as a last resort, hard split.

    Args:
        text: Text to split.
        cuts: Positions where a new chunk should start.
        max_chunk_size: Maximum width of a chunk.

    Returns:
        The chunks in order, with no gaps and no overlap, so that joining
        ``text[first:last]`` gives the original text back.
    """
    chunks: list[tuple[int, int]] = []
    paragraph_cuts = _paragraph_starts(text)

    for first, last in _split_range(0, len(text), cuts):
        if last - first <= max_chunk_size:
            chunks.append((first, last))
        else:
            chunks.extend(
                _pack(
                    _split_range(first, last, paragraph_cuts), max_chunk_size
                )
            )
    return chunks


def _definition_starts(source: str) -> list[int]:
    """Find where each top-level definition of a Python source starts.

    Uses the abstract syntax tree, so ``async def``, ``class`` and decorated
    definitions are handled, and a ``def`` written inside a string is not
    mistaken for one. A decorator belongs to the definition it decorates, so
    the position is the first line of the two.

    Args:
        source: Python source code.

    Returns:
        The positions, in the order they appear.

    Raises:
        SyntaxError: If the source is not valid Python.
        ValueError: If the source holds a null byte (Python 3.10 and 3.11).
    """
    tree = ast.parse(source)
    line_starts: list[int] = [0]
    positions: list[int] = []

    for line in source.splitlines(keepends=True):
        line_starts.append(line_starts[-1] + len(line))

    for node in tree.body:
        if isinstance(
            node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)
        ):
            first_line = min(
                [node.lineno]
                + [decorator.lineno for decorator in node.decorator_list]
            )
            positions.append(line_starts[first_line - 1])

    return positions


def _line_starts(source: str) -> list[int]:
    """Return the character offset where each line of the source begins.

    Args:
        source: Any text.

    Returns:
        The offset of line 1 (always 0), line 2, and so on, with one extra
        entry for the position just past the last line.
    """
    offsets: list[int] = [0]
    for line in source.splitlines(keepends=True):
        offsets.append(offsets[-1] + len(line))
    return offsets


def definition_spans(source: str) -> list[tuple[int, int, str]]:
    """Locate every top-level class or function and the range it covers.

    The span runs from the ``def``/``class`` line to the end of its body, so
    a chunk that falls inside it can be labelled with its name. Source that
    does not parse yields no spans, the same fallback ``chunk_python`` uses.

    Args:
        source: Python source code.

    Returns:
        Tuples of start offset, end offset (exclusive) and name, in order;
        empty if the source is not valid Python.
    """
    try:
        tree = ast.parse(source)
    except (SyntaxError, ValueError):
        return []
    line_starts = _line_starts(source)
    last_line = len(line_starts) - 1
    spans: list[tuple[int, int, str]] = []
    for node in tree.body:
        if isinstance(
            node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)
        ):
            start = line_starts[node.lineno - 1]
            end_line = node.end_lineno if node.end_lineno else node.lineno
            end = line_starts[min(end_line, last_line)]
            spans.append((start, end, node.name))
    return spans


def context_for_offset(
    spans: list[tuple[int, int, str]], offset: int
) -> str:
    """Return the name of the definition that contains an offset.

    Args:
        spans: The spans from ``definition_spans``.
        offset: A character offset into the same source.

    Returns:
        The name of the enclosing definition, or the empty string when the
        offset lies between top-level definitions.
    """
    for start, end, name in spans:
        if start <= offset < end:
            return name
    return ""


def chunk_text(text: str, max_chunk_size: int) -> list[tuple[int, int]]:
    """Split Markdown or plain text into chunks, cutting at headings.

    Args:
        text: Text to split.
        max_chunk_size: Maximum width of a chunk.

    Returns:
        The chunks in order, with no gaps and no overlap.
    """
    return _chunk_with_cuts(text, _heading_starts(text), max_chunk_size)


def chunk_python(source: str, max_chunk_size: int) -> list[tuple[int, int]]:
    """Split Python source into chunks, cutting at top-level definitions.

    Source that does not parse is chunked as plain text instead of failing,
    because the corpus may hold templates or Python 2 files. A null byte
    raises ValueError instead of SyntaxError before Python 3.12.

    Args:
        source: Python source code.
        max_chunk_size: Maximum width of a chunk.

    Returns:
        The chunks in order, with no gaps and no overlap.
    """
    try:
        cuts = _definition_starts(source)
    except (SyntaxError, ValueError):
        return chunk_text(source, max_chunk_size)
    return _chunk_with_cuts(source, cuts, max_chunk_size)


# A chunking strategy: it reads a text and its width limit, and returns
# the ranges to cut it into.
Chunker = Callable[[str, int], list[tuple[int, int]]]

# Only the suffixes with a strategy of their own are listed here; every
# other file falls back to the Markdown and plain text one.
CHUNKERS: dict[str, Chunker] = {
    ".py": chunk_python
}


def chunker_for(suffix: str) -> Chunker:
    """Pick the chunking strategy for a file suffix.

    Args:
        suffix: File suffix including the dot, as ``Path.suffix`` gives it.

    Returns:
        The strategy registered for that suffix, or the text one.
    """
    return CHUNKERS.get(suffix, chunk_text)
