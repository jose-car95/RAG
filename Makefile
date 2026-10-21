.PHONY: install run debug clean lint lint-strict test test-all \
	index search search_dataset evaluate answer answer_dataset serve

# Extra arguments for the CLI, e.g. make run ARGS="search 'What is vLLM?' --k 5"
ARGS ?=

# Shortcuts for each command; override any of them on the command line, e.g.
# make search_dataset DATASET=code K=5
DATASET ?= docs
SCOPE ?= UnansweredQuestions
K ?= 10
MAX_CHUNK_SIZE ?= 2000
Q ?= How to configure OpenAI server?

DATASET_FILE = data/datasets/$(SCOPE)/dataset_$(DATASET)_public.json
ANSWERED_FILE = data/datasets/AnsweredQuestions/dataset_$(DATASET)_public.json
SEARCH_DIR ?= data/output/search_results
ANSWER_DIR ?= data/output/search_results_and_answer
RESULTS_FILE = $(SEARCH_DIR)/$(notdir $(DATASET_FILE))

MYPY_FLAGS = --warn-return-any --warn-unused-ignores --ignore-missing-imports \
	--disallow-untyped-defs --check-untyped-defs

install:
	uv sync

run:
	uv run python -m src $(ARGS)

debug:
	uv run python -m pdb -m src $(ARGS)

# Only our code: .cache/ holds uv's packages and data/ the untouched corpus.
clean:
	find src tests -type d -name __pycache__ -exec rm -rf {} +
	rm -rf .mypy_cache .pytest_cache

lint:
	uv run flake8 .
	uv run mypy . $(MYPY_FLAGS)

lint-strict:
	uv run flake8 .
	uv run mypy . --strict

# Skips the tests that load the real Qwen model (about 40 s).
test:
	uv run pytest -m "not slow"

test-all:
	uv run pytest

index:
	uv run python -m src index --max_chunk_size $(MAX_CHUNK_SIZE)

search:
	uv run python -m src search "$(Q)" --k $(K)

search_dataset:
	uv run python -m src search_dataset --dataset_path $(DATASET_FILE) \
		--k $(K) --save_directory $(SEARCH_DIR)

evaluate:
	uv run python -m src evaluate --student_search_results_path \
		$(RESULTS_FILE) --dataset_path $(ANSWERED_FILE)

answer:
	uv run python -m src answer "$(Q)" --k $(K)

answer_dataset:
	uv run python -m src answer_dataset --student_search_results_path \
		$(RESULTS_FILE) --save_directory $(ANSWER_DIR)

# Local HTTP API (bonus); open http://127.0.0.1:8000/docs to try it.
serve:
	uv run uvicorn --factory src.bootstrap:build_api --host 127.0.0.1 --port 8000
