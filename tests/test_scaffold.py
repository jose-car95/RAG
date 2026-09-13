"""Smoke test: the scaffolding exposes an importable ``src`` package."""

import importlib


def test_src_package_is_importable() -> None:
    """The project module can be imported from the repository root."""
    module = importlib.import_module("src")
    assert module.__doc__
