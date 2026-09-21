"""Split Markdown and plain text into chunk ranges.

A chunk is a ``(first, last)`` range with an exclusive end, so its text is
``text[first:last]`` and its width is ``last - first``.
"""


def hard_split(
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


def split_range(
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


def heading_starts(text: str) -> list[int]:
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


def paragraph_starts(text: str) -> list[int]:
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


def pack(
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
            chunks.extend(hard_split(first, last, max_chunk_size))
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


def chunk_text(text: str, max_chunk_size: int) -> list[tuple[int, int]]:
    """Split a text into chunks of at most ``max_chunk_size`` characters.

    Cascade: Markdown headings first, then the blank lines between
    paragraphs, and a hard cut only as a last resort.

    Args:
        text: Text to split.
        max_chunk_size: Maximum width of a chunk.

    Returns:
        The chunks in order, with no gaps and no overlap, so that joining
        ``text[first:last]`` gives the original text back.
    """
    chunks: list[tuple[int, int]] = []
    paragraph_cuts = paragraph_starts(text)

    for first, last in split_range(0, len(text), heading_starts(text)):
        if last - first <= max_chunk_size:
            chunks.append((first, last))
        else:
            chunks.extend(
                pack(split_range(first, last, paragraph_cuts), max_chunk_size)
            )
    return chunks
