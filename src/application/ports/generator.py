"""Port: the language model that writes the answers."""

from collections.abc import Callable
from typing import Protocol


class Generator(Protocol):
    """What the use case needs from a model: count tokens and answer.

    Qwen in production and a fake in the tests, so no test has to load
    1.5 GB of weights.
    """

    def count_tokens(self, text: str) -> int:
        """Count the tokens of a text.

        Args:
            text: Any text.

        Returns:
            The number of tokens.
        """
        ...

    def generate(self, prompt: str) -> str:
        """Answer a prompt.

        Args:
            prompt: The full prompt.

        Returns:
            The answer.
        """
        ...


# Loading the model costs seconds and gigabytes, so use cases receive the
# loader and decide when, or whether, to call it.
GeneratorLoader = Callable[[], Generator]
