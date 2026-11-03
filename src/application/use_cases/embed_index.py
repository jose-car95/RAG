"""Use case: store one embedding per chunk text, next to the lexical index."""

from tqdm import tqdm

from src.application.ports.embedder import EmbedderLoader
from src.application.ports.index_store import IndexStore
from src.application.ports.vector_store import VectorStore
from src.domain.semantic import text_hash


BATCH_SIZE: int = 32


def run_embed_index(
    index_path: str,
    vectors_path: str,
    index_store: IndexStore,
    vector_store: VectorStore,
    load_embedder: EmbedderLoader
) -> tuple[int, int]:
    """Embed every chunk text of the index that has no vector yet.

    Equal texts share one vector, and the shortest texts go first so each
    batch pads little.

    Args:
        index_path: The lexical index to read the chunks from.
        vectors_path: Where the vectors are stored.
        index_store: Reads the chunks of the index.
        vector_store: Knows and saves the vectors.
        load_embedder: Loads the model, only if some text needs it.

    Returns:
        How many texts were embedded now, and how many distinct texts the
        index has.
    """
    texts = {
        text_hash(text): text
        for *_, text in index_store.load_chunks(index_path)
    }
    # ponytail: vectors of texts that left the index stay in the store;
    # they are small, never searched and reused if the text comes back.
    # A cleanup pass (known minus current hashes) would bound its size.
    known = vector_store.known_hashes(vectors_path)
    missing = sorted(
        (key for key in texts if key not in known),
        key=lambda key: len(texts[key])
    )
    if not missing:
        return 0, len(texts)
    embedder = load_embedder()
    for start in tqdm(
        range(0, len(missing), BATCH_SIZE), desc="Embedding", unit="batch"
    ):
        batch = missing[start:start + BATCH_SIZE]
        vectors = embedder.embed([texts[key] for key in batch])
        vector_store.save_vectors(vectors_path, batch, vectors)
    return len(missing), len(texts)
