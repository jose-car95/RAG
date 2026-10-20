"""Tests for the Qwen generator that counts tokens and generates answers.

The constants test runs everywhere. The model tests need the weights in
``.cache/huggingface/`` (1.5 GB, not in the repo), so they are skipped in CI
and run locally, where they load Qwen once for the whole module.
"""

from collections.abc import Iterator
from pathlib import Path

import pytest

from src.adapters.outbound.qwen_generator import (
    MAX_NEW_TOKENS,
    MODEL_NAME,
    QwenGenerator,
    load_generator,
)
from src.domain.prompt import Prompt

MODEL_FILES = Path(".cache/huggingface/models--Qwen--Qwen3-0.6B")

needs_model = pytest.mark.skipif(
    not MODEL_FILES.is_dir(),
    reason="Qwen3-0.6B weights not downloaded",
)


@pytest.fixture(scope="module")
def generator() -> Iterator[QwenGenerator]:
    """Load the real model once for every model test in this module.

    Yields:
        A loaded ``QwenGenerator``.
    """
    yield load_generator()


@pytest.mark.slow
@needs_model
def test_count_tokens_uses_the_qwen_tokenizer(
    generator: QwenGenerator,
) -> None:
    """Two words, two Qwen tokens (measured with the real tokenizer)."""
    assert generator.count_tokens("Hello world") == 2


@pytest.mark.slow
@needs_model
def test_generate_returns_only_the_new_text(generator: QwenGenerator) -> None:
    """The answer holds no prompt and no thinking tags, just the reply.

    The one-word rule travels in the system message, so the model must
    read it there.

    Decoding the whole output would return the question too, plus empty
    ``<think>`` tags: only the tokens after the prompt are the answer.
    """
    prompt = Prompt(
        system="Answer with one word.",
        user="What colour is the sky on a clear day?"
    )
    answer = generator.generate(prompt)
    assert answer.strip().lower().rstrip(".") == "blue"
    assert "colour" not in answer
    assert "think" not in answer


def test_model_constants() -> None:
    """The subject's model, and a cap so no answer can run for minutes."""
    assert MODEL_NAME == "Qwen/Qwen3-0.6B"
    assert MAX_NEW_TOKENS == 256
