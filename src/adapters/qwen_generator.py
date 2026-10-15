"""Count tokens and generate answers with Qwen3-0.6B on the CPU."""

import os
from typing import Any

MODEL_NAME: str = "Qwen/Qwen3-0.6B"
# Real answers take 35-43 tokens (measured in #54): the cap only stops a
# runaway answer from running for minutes on the CPU.
MAX_NEW_TOKENS: int = 256
# Inside the repo, where the weights already are: the school home is tiny.
MODEL_CACHE_DIR: str = ".cache/huggingface"


class QwenGenerator:
    """A loaded tokenizer and model, shared by counting and generating.

    Both are typed ``Any`` because transformers' own type hints reject its
    ``generate`` and ``to`` methods under mypy (measured in #55).

    Attributes:
        tokenizer: Turns text into token ids and back.
        model: The Qwen weights, on the CPU.
    """

    def __init__(self, tokenizer: Any, model: Any) -> None:
        """Keep the tokenizer and the model already loaded.

        Args:
            tokenizer: Qwen's tokenizer.
            model: Qwen's model, on the CPU.
        """
        self.tokenizer = tokenizer
        self.model = model

    def count_tokens(self, text: str) -> int:
        """Count the tokens Qwen would read for a text.

        Args:
            text: Any text, usually a whole prompt.

        Returns:
            The number of tokens.
        """
        return len(self.tokenizer(text)["input_ids"])

    def generate(self, prompt: str) -> str:
        """Answer a prompt greedily and return only the new text.

        Args:
            prompt: The full prompt, sources included.

        Returns:
            The model's answer, without the prompt around it.
        """
        # Thinking off: on a CPU every hidden reasoning token costs time.
        chat = self.tokenizer.apply_chat_template(
            [{"role": "user", "content": prompt}],
            tokenize=False,
            add_generation_prompt=True,
            enable_thinking=False
        )
        inputs = self.tokenizer(chat, return_tensors="pt")
        output = self.model.generate(
            **inputs,
            max_new_tokens=MAX_NEW_TOKENS,
            do_sample=False
        )
        # generate returns the prompt followed by the answer.
        prompt_length = inputs["input_ids"].shape[1]
        answer = self.tokenizer.decode(
            output[0][prompt_length:],
            skip_special_tokens=True
        )
        return str(answer).strip()


def load_generator(cache_dir: str = MODEL_CACHE_DIR) -> QwenGenerator:
    """Load Qwen from the local cache, in float32, on the CPU.

    torch and transformers are imported here, not at the top of the module:
    importing them takes seconds, and only ``answer`` needs them.

    Args:
        cache_dir: Folder with the downloaded weights.

    Returns:
        The generator, ready to count and to answer.
    """
    # Before the import, which reads it: keeps huggingface_hub's own files
    # out of the home folder; setdefault respects a value the user chose.
    os.environ.setdefault("HF_HOME", cache_dir)
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer

    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME, cache_dir=cache_dir)
    # float32, not bfloat16: about 2.7 times faster on CPUs without native
    # bfloat16 support (measured in #54).
    model: Any = AutoModelForCausalLM.from_pretrained(
        MODEL_NAME,
        cache_dir=cache_dir,
        dtype=torch.float32
    )
    return QwenGenerator(tokenizer, model.to("cpu"))
