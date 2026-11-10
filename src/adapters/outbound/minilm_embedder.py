"""Embed texts with all-MiniLM-L6-v2 on the CPU."""

import os
from typing import Any

from src.application.ports.embedder import Embedder, Vectors


MODEL_NAME: str = "sentence-transformers/all-MiniLM-L6-v2"
# The length the model was trained on; longer chunks lose their tail.
MAX_TOKENS: int = 256
# Inside the repo, next to Qwen: the school home is tiny.
MODEL_CACHE_DIR: str = ".cache/huggingface"


def logical_cpu_count() -> int:
    """Count the logical CPUs, never fewer than one.

    Returns:
        ``os.cpu_count()``, or 1 when the system cannot tell.
    """
    return os.cpu_count() or 1


class MiniLmEmbedder(Embedder):
    """A loaded tokenizer and model that turn texts into unit vectors.

    Both are typed ``Any``, as in ``QwenGenerator``: transformers' own type
    hints do not pass mypy.

    Attributes:
        tokenizer: Turns texts into token ids.
        model: The MiniLM weights, on the CPU.
    """

    def __init__(self, tokenizer: Any, model: Any) -> None:
        """Keep the tokenizer and the model already loaded.

        Args:
            tokenizer: MiniLM's tokenizer.
            model: MiniLM's model, on the CPU.
        """
        self.tokenizer = tokenizer
        self.model = model

    def embed(self, texts: list[str]) -> Vectors:
        """Average the token vectors of each text and scale it to length 1.

        Args:
            texts: The texts, in order; longer than ``MAX_TOKENS`` tokens
                they are cut.

        Returns:
            One float32 row of 384 numbers per text.
        """
        import torch

        # torch defaults to the physical cores; all logical CPUs are ~20%
        # faster here. The thread count is a process-wide torch setting, so
        # it is restored below: Qwen must keep running with torch's default.
        previous_threads = torch.get_num_threads()
        torch.set_num_threads(logical_cpu_count())
        try:
            return self._embed_batch(texts)
        finally:
            torch.set_num_threads(previous_threads)

    def _embed_batch(self, texts: list[str]) -> Vectors:
        """Run the model on one batch of texts.

        Args:
            texts: The texts, in order.

        Returns:
            One float32 row of 384 numbers per text.
        """
        import torch

        inputs = self.tokenizer(
            texts,
            padding=True,
            truncation=True,
            max_length=MAX_TOKENS,
            return_tensors="pt"
        )
        with torch.inference_mode():
            # The mask keeps the padding of short texts out of the mean.
            tokens = self.model(**inputs).last_hidden_state
            mask = inputs["attention_mask"].unsqueeze(-1)
            mean = (tokens * mask).sum(dim=1) / mask.sum(dim=1)
            unit = torch.nn.functional.normalize(mean, dim=1)
            vectors: Vectors = unit.numpy()
            return vectors


def load_embedder(cache_dir: str = MODEL_CACHE_DIR) -> MiniLmEmbedder:
    """Load MiniLM on the CPU, downloading it the first time.

    transformers is imported here so that ``index`` without
    ``--embeddings`` never pays for it.

    Args:
        cache_dir: Where the model is downloaded and looked for.

    Returns:
        The embedder, ready to use.
    """
    os.environ.setdefault("HF_HOME", cache_dir)
    from transformers import AutoModel, AutoTokenizer

    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME, cache_dir=cache_dir)
    model: Any = AutoModel.from_pretrained(MODEL_NAME, cache_dir=cache_dir)
    return MiniLmEmbedder(tokenizer, model.to("cpu").eval())
