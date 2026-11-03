"""Port: the model that turns texts into vectors of meaning."""

from collections.abc import Callable
from typing import Protocol

import numpy as np
from numpy.typing import NDArray

# One row per text, all of the same length.
Vectors = NDArray[np.float32]


class Embedder(Protocol):
    """What the use case needs from a model of meaning: texts to vectors.

    MiniLM in production and a fake in the tests, so no test has to load
    the model.
    """

    def embed(self, texts: list[str]) -> Vectors:
        """Turn a batch of texts into one unit vector each.

        Args:
            texts: The texts, in order.

        Returns:
            One row per text, in the same order.
        """
        ...


# Loading the model costs a second, so the use case calls the loader only
# when some text still needs a vector.
EmbedderLoader = Callable[[], Embedder]
