"""Tests for building the prompt from the retrieved sources.

The prompt has two parts, one per chat role: the rules go in ``system`` and
the tagged sources plus the question go in ``user``.
"""

from src.domain.prompt import SYSTEM_PROMPT, Prompt, build_prompt

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
# A real corpus file carries its own example question (the "John Doe" case
# of #55): the tags keep it inside its source.
WITH_QUESTION = (
    "data/raw/vllm-0.10.1/examples/offline_inference/"
    "automatic_prefix_caching.py",
    "Question: what is the age of John Doe? Your answer: The age of John "
    "Doe is",
)


def count_words(text: str) -> int:
    """Count tokens as words, so the tests never load the real tokenizer.

    Args:
        text: Any text.

    Returns:
        The number of words.
    """
    return len(text.split())


def size(prompt: Prompt) -> int:
    """Measure both parts of a prompt together, as the budget does.

    Args:
        prompt: A built prompt.

    Returns:
        Its size in words.
    """
    return count_words(prompt.system) + count_words(prompt.user)


def base_size() -> int:
    """Measure a prompt with no sources: rules and question only.

    Returns:
        Its size in words.
    """
    return size(build_prompt(QUESTION, [], count_words, 10_000))


def test_the_rules_go_alone_in_the_system_part() -> None:
    """System holds the rules and nothing that changes per question."""
    prompt = build_prompt(QUESTION, [SHORT, ALSO_SHORT], count_words, 1_000)

    assert prompt.system == SYSTEM_PROMPT
    assert QUESTION not in prompt.system
    assert SHORT[1] not in prompt.system


def test_each_source_is_wrapped_in_its_own_tags() -> None:
    """Numbered, with its path, its text inside, and closed."""
    prompt = build_prompt(QUESTION, [SHORT, ALSO_SHORT], count_words, 1_000)

    assert f'<source id="1" path="{SHORT[0]}">\n{SHORT[1]}\n</source>' in (
        prompt.user
    )
    assert (
        f'<source id="2" path="{ALSO_SHORT[0]}">\n{ALSO_SHORT[1]}\n</source>'
        in prompt.user
    )


def test_the_question_goes_last_in_the_user_part() -> None:
    """It is what the model continues from."""
    prompt = build_prompt(QUESTION, [SHORT, ALSO_SHORT], count_words, 1_000)

    assert prompt.user.endswith(f"Question: {QUESTION}")


def test_a_question_inside_a_source_stays_inside_its_tags() -> None:
    """The source's own "Question:" line comes before the real question."""
    prompt = build_prompt(QUESTION, [WITH_QUESTION], count_words, 1_000)

    closing = prompt.user.index("</source>")
    assert prompt.user.index("John Doe") < closing
    assert prompt.user.rindex("Question:") > closing
    assert prompt.user.endswith(f"Question: {QUESTION}")


def test_sources_keep_the_retrieval_order() -> None:
    """The best source (first in the list) comes first in the prompt."""
    prompt = build_prompt(QUESTION, [SHORT, ALSO_SHORT], count_words, 1_000)

    assert prompt.user.index(SHORT[1]) < prompt.user.index(ALSO_SHORT[1])


def test_the_instruction_asks_to_stay_on_the_sources() -> None:
    """The model must answer from the sources or say it cannot."""
    assert "only" in SYSTEM_PROMPT.lower()
    assert "sources" in SYSTEM_PROMPT.lower()


def test_adding_stops_at_the_first_source_that_does_not_fit() -> None:
    """Decision A: the long third source is left out, the first two stay."""
    budget = base_size() + 40

    prompt = build_prompt(
        QUESTION, [SHORT, ALSO_SHORT, LONG], count_words, budget
    )

    assert SHORT[1] in prompt.user
    assert ALSO_SHORT[1] in prompt.user
    assert LONG[0] not in prompt.user


def test_nothing_after_a_source_that_does_not_fit_is_added() -> None:
    """Decision A: once one does not fit, a smaller later one is not tried."""
    budget = base_size() + 40

    prompt = build_prompt(
        QUESTION, [SHORT, LONG, ALSO_SHORT], count_words, budget
    )

    assert SHORT[1] in prompt.user
    assert LONG[0] not in prompt.user
    assert ALSO_SHORT[1] not in prompt.user


def test_no_room_for_the_first_source_gives_a_prompt_without_sources() -> None:
    """The model then gets only the instruction and the question."""
    budget = base_size() + 5

    prompt = build_prompt(QUESTION, [LONG, SHORT], count_words, budget)

    assert prompt == build_prompt(QUESTION, [], count_words, budget)
    assert "<source" not in prompt.user


def test_no_sources_gives_rules_and_question() -> None:
    """An empty list is valid and does not fail."""
    prompt = build_prompt(QUESTION, [], count_words, 1_000)

    assert prompt == Prompt(system=SYSTEM_PROMPT, user=f"Question: {QUESTION}")


def test_the_prompt_never_exceeds_the_budget() -> None:
    """Both parts together, counted with the same counter, fit the budget."""
    for extra in (0, 5, 20, 40, 100, 600):
        budget = base_size() + extra

        prompt = build_prompt(
            QUESTION, [SHORT, ALSO_SHORT, LONG], count_words, budget
        )

        assert size(prompt) <= budget
