from src.adapters.sqlite_index import load_chunks
from src.domain.tokenizer import tokenize
from src.domain.bm25 import build_index, rank
from src.domain.models import MinimalSource


def run_search(
    query: str, k: int, index_path: str
) -> list[tuple[MinimalSource, float]]:
    if not isinstance(k, int) or isinstance(k, bool) or k <= 0:
        raise ValueError("k must be a positive integer")
    clean_query = query.strip()
    if not clean_query:
        raise ValueError("query must not be empty")
    rows = load_chunks(index_path)
    index = build_index(
        (chunk_id, tokenize(text)) for chunk_id, _, _, _, text in rows
    )
    locations = {
        chunk_id: (file_path, first_index, last_index)
        for chunk_id, file_path, first_index, last_index, _ in rows
    }

    results = []
    for chunk_id, score in rank(index, tokenize(clean_query), k):
        file_path, first_index, last_index = locations[chunk_id]
        source = MinimalSource(
            file_path=file_path,
            first_character_index=first_index,
            last_character_index=last_index
        )
        results.append((source, score))

    return results
