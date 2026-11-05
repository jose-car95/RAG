.PHONY: install run debug lint lint-strict test clean fclean serve

install:
	uv sync

run:
	uv run python -m src $(ARGS)

debug:
	uv run python -m pdb -m src $(ARGS)

lint:
	uv run flake8 .
	uv run mypy . --warn-return-any --warn-unused-ignores --ignore-missing-imports --disallow-untyped-defs --check-untyped-defs

lint-strict:
	uv run flake8 .
	uv run mypy . --strict

test:
	uv run pytest -m "not slow"

clean:
	find . -type d -name __pycache__ \
		-not -path './.venv/*' -not -path './.cache/*' -not -path './data/*' \
		-exec rm -rf {} +
	find . -type f \( -name '*.pyc' -o -name '*.pyo' \) \
		-not -path './.venv/*' -not -path './.cache/*' -not -path './data/*' \
		-delete
	find . -type d -name '*.egg-info' \
		-not -path './.venv/*' -not -path './.cache/*' -not -path './data/*' \
		-exec rm -rf {} +
	rm -rf .pytest_cache .mypy_cache .ruff_cache .coverage htmlcov

fclean: clean
	rm -rf .venv
	rm -rf data/processed data/output
	rm -rf .cache

serve:
	uv run uvicorn --factory src.bootstrap:build_api --host 127.0.0.1 --port 8000
