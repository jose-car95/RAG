"""Tests for the Qwen adapter that counts tokens and generates answers.

The import test runs everywhere. The model tests need the weights in
``.cache/huggingface/`` (1.5 GB, not in the repo), so they are skipped in CI
and run locally, where they load Qwen once for the whole module.
"""

import subprocess
import sys
from collections.abc import Iterator
from pathlib import Path

import pytest

from src.adapters.qwen_generator import (
    MAX_NEW_TOKENS,
    MODEL_NAME,
    QwenGenerator,
    load_generator,
)

MODEL_FILES = Path(".cache/huggingface/models--Qwen--Qwen3-0.6B")

needs_model = pytest.mark.skipif(
    not MODEL_FILES.is_dir(),
    reason="Qwen3-0.6B weights not downloaded",
)


def test_import_does_not_load_torch() -> None:
    """Importing the adapter must stay cheap: torch costs seconds to import.

    Run in a fresh interpreter, because this test process may already have
    torch loaded by the model tests.
    """
    code = (
        "import sys\n"
        "import src.adapters.qwen_generator\n"
        "print('torch' in sys.modules, 'transformers' in sys.modules)\n"
    )
    completed = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    assert completed.stdout.strip() == "False False"


@pytest.fixture(scope="module")
def generator() -> Iterator[QwenGenerator]:
    """Load the real model once for every model test in this module.

    Yields:
        A loaded ``QwenGenerator``.
    """
    yield load_generator()


@needs_model
def test_count_tokens_uses_the_qwen_tokenizer(
    generator: QwenGenerator,
) -> None:
    """Two words, two Qwen tokens (measured with the real tokenizer)."""
    assert generator.count_tokens("Hello world") == 2


@needs_model
def test_generate_returns_only_the_new_text(generator: QwenGenerator) -> None:
    """The answer holds no prompt and no thinking tags, just the reply.

    Decoding the whole output would return the question too, plus empty
    ``<think>`` tags: only the tokens after the prompt are the answer.
    """
    prompt = "What colour is the sky on a clear day? Answer with one word."
    answer = generator.generate(prompt)
    assert answer.strip().lower().rstrip(".") == "blue"
    assert "colour" not in answer
    assert "think" not in answer


def test_model_constants() -> None:
    """The subject's model, and a cap so no answer can run for minutes."""
    assert MODEL_NAME == "Qwen/Qwen3-0.6B"
    assert MAX_NEW_TOKENS == 256
