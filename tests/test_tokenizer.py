"""Tests for the tokenizer: text into the tokens the retriever compares."""

import re

import pytest

from src.domain.tokenizer import tokenize

# One real question per dataset, to keep the examples anchored to the corpus.
DOCS_QUESTION = (
    "What HTTP endpoint is used to dynamically load a LoRA adapter in vLLM?"
)
CODE_QUESTION = (
    "How do you evaluate accuracy of a quantized model using lm_eval in vLLM?"
)


@pytest.mark.parametrize(
    "text, expected",
    [
        ("What is vLLM?", ["what", "is", "vllm"]),
        (
            "How to configure OpenAI server?",
            ["how", "to", "configure", "openai", "server"],
        ),
        ("", []),
        ("?!.,;:", []),
        (
            "How to use lm_eval in vLLM?",
            ["how", "to", "use", "lm_eval", "in", "vllm"],
        ),
        ("Set FP8_MIN for int8", ["set", "fp8_min", "for", "int8"]),
        ("multi-modal input", ["multi", "modal", "input"]),
        ("vLLM VLLM vllm", ["vllm", "vllm", "vllm"]),
    ],
    ids=[
        "lowercase",
        "subject-example",
        "empty",
        "punctuation-only",
        "identifier",
        "digits",
        "hyphen-splits",
        "duplicates-kept",
    ],
)
def test_tokenize_examples(text: str, expected: list[str]) -> None:
    """Every acceptance example of the slice, in order.

    Args:
        text: Input text.
        expected: The tokens the retriever must compare.
    """
    assert tokenize(text) == expected


@pytest.mark.parametrize(
    "text",
    [DOCS_QUESTION, CODE_QUESTION],
    ids=["docs-question", "code-question"],
)
def test_every_token_is_a_lowercase_word(text: str) -> None:
    """Tokens are lowercase runs of letters, digits and underscores.

    BM25 counts repetitions, so duplicates are kept and the result is a list,
    never a set.

    Args:
        text: A real question from the public datasets.
    """
    tokens = tokenize(text)

    assert tokens, "a real question must produce tokens"
    assert isinstance(tokens, list)
    for token in tokens:
        assert re.fullmatch(r"[a-z0-9_]+", token), token
