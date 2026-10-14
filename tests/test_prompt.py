"""Tests for building the prompt from the retrieved sources."""

from src.domain.prompt import INSTRUCTION, build_prompt

QUESTION = "How do I load a LoRA adapter?"
SHORT = (
    "data/raw/vllm-0.10.1/docs/features/lora.md",
    "Send a POST request to the load_lora_adapter endpoint.",
)
ALSO_SHORT = (
    "data/raw/vllm-0.10.1/vllm/entrypoints/openai/api_server.py",
    "def load_lora_adapter(request): register the adapter.",
)
LONG = (
    "data/raw/vllm-0.10.1/docs/serving/long.md",
    " ".join(["filler"] * 500),
)


def count_words(text: str) -> int:
    """Count tokens as words, so the tests never load the real tokenizer.

    Args:
        text: Any text.

    Returns:
        The number of words.
    """
    return len(text.split())


def base_size() -> int:
    """Measure a prompt with no sources: instruction and question only.

    Returns:
        Its size in words.
    """
    return count_words(build_prompt(QUESTION, [], count_words, 10_000))


def test_the_prompt_holds_instruction_sources_and_question() -> None:
    """Both sources are numbered with their path and the question goes last."""
    prompt = build_prompt(QUESTION, [SHORT, ALSO_SHORT], count_words, 1_000)

    assert prompt.startswith(INSTRUCTION)
    assert f"[1] {SHORT[0]}" in prompt
    assert SHORT[1] in prompt
    assert f"[2] {ALSO_SHORT[0]}" in prompt
    assert ALSO_SHORT[1] in prompt
    assert prompt.endswith(f"Question: {QUESTION}")


def test_sources_keep_the_retrieval_order() -> None:
    """The best source (first in the list) comes first in the prompt."""
    prompt = build_prompt(QUESTION, [SHORT, ALSO_SHORT], count_words, 1_000)

    assert prompt.index(SHORT[1]) < prompt.index(ALSO_SHORT[1])


def test_the_instruction_asks_to_stay_on_the_sources() -> None:
    """The model must answer from the sources or say it cannot."""
    assert "only" in INSTRUCTION.lower()
    assert "sources" in INSTRUCTION.lower()


def test_adding_stops_at_the_first_source_that_does_not_fit() -> None:
    """Decision A: the long third source is left out, the first two stay."""
    budget = base_size() + 40

    prompt = build_prompt(
        QUESTION, [SHORT, ALSO_SHORT, LONG], count_words, budget
    )

    assert SHORT[1] in prompt
    assert ALSO_SHORT[1] in prompt
    assert LONG[0] not in prompt


def test_nothing_after_a_source_that_does_not_fit_is_added() -> None:
    """Decision A: once one does not fit, a smaller later one is not tried."""
    budget = base_size() + 40

    prompt = build_prompt(
        QUESTION, [SHORT, LONG, ALSO_SHORT], count_words, budget
    )

    assert SHORT[1] in prompt
    assert LONG[0] not in prompt
    assert ALSO_SHORT[1] not in prompt


def test_no_room_for_the_first_source_gives_a_prompt_without_sources() -> None:
    """The model then gets only the instruction and the question."""
    budget = base_size() + 5

    prompt = build_prompt(QUESTION, [LONG, SHORT], count_words, budget)

    assert prompt == build_prompt(QUESTION, [], count_words, budget)
    assert "[1]" not in prompt


def test_no_sources_gives_instruction_and_question() -> None:
    """An empty list is valid and does not fail."""
    prompt = build_prompt(QUESTION, [], count_words, 1_000)

    assert prompt.startswith(INSTRUCTION)
    assert prompt.endswith(f"Question: {QUESTION}")


def test_the_prompt_never_exceeds_the_budget() -> None:
    """Counted with the same counter, the prompt stays within the budget."""
    for extra in (0, 5, 20, 40, 100, 600):
        budget = base_size() + extra

        prompt = build_prompt(
            QUESTION, [SHORT, ALSO_SHORT, LONG], count_words, budget
        )

        assert count_words(prompt) <= budget
