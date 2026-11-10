"""Use case: store one embedding per chunk text, next to the lexical index."""

from dataclasses import dataclass

from tqdm import tqdm

from src.application.ports.embedder import EmbedderLoader
from src.application.ports.index_store import IndexStore
from src.application.ports.vector_store import VectorStore
from src.application.use_cases.shared.progress import status
from src.domain.semantic import text_hash


BATCH_SIZE: int = 16


@dataclass(frozen=True)
class EmbedReport:
    """What one ``run_embed_index`` call did, for the CLI to summarise.

    Attributes:
        new_count: Texts embedded now.
        total_count: Distinct chunk texts in the index.
        orphaned_count: Stored vectors whose text is no longer in any chunk.
    """

    new_count: int
    total_count: int
    orphaned_count: int


def run_embed_index(
    index_path: str,
    vectors_path: str,
    index_store: IndexStore,
    vector_store: VectorStore,
    load_embedder: EmbedderLoader
) -> EmbedReport:
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
        An ``EmbedReport`` with the texts embedded now, the distinct texts of
        the index and the stored vectors left without a chunk.
    """
    status("Reading chunk texts from the index...")
    texts = {
        text_hash(text): text
        for _, _, _, _, text, _ in index_store.load_chunks(index_path)
    }
    # ponytail: vectors of texts that left the index stay in the store;
    # they are small, never searched and reused if the text comes back.
    # They are only counted; a cleanup pass would bound the file's size.
    known = vector_store.known_hashes(vectors_path)
    orphaned = len(known - texts.keys())
    missing = sorted(
        (key for key in texts if key not in known),
        key=lambda key: len(texts[key])
    )
    status(
        f"{len(texts)} distinct texts: {len(texts) - len(missing)} vectors "
        f"already stored, {len(missing)} to embed"
    )
    if not missing:
        return EmbedReport(0, len(texts), orphaned)
    status("Loading the embedding model...")
    embedder = load_embedder()
    with tqdm(total=len(missing), desc="Embedding", unit="text") as bar:
        for start in range(0, len(missing), BATCH_SIZE):
            batch = missing[start:start + BATCH_SIZE]
            vectors = embedder.embed([texts[key] for key in batch])
            vector_store.save_vectors(vectors_path, batch, vectors)
            bar.update(len(batch))
    return EmbedReport(len(missing), len(texts), orphaned)
