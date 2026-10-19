"""The dependency rule of the hexagon, checked on every import of ``src``.

Dependencies point inwards: adapters may import the application and the
domain, the application only the domain, and the domain nothing of ours.
Only ``bootstrap`` may know the concrete adapters, because it plugs them in.
"""

import ast
from pathlib import Path

import pytest

SRC = Path(__file__).resolve().parents[1] / "src"

# What each layer must never import.
FORBIDDEN = {
    "domain": ("src.application", "src.adapters", "src.bootstrap"),
    "application": ("src.adapters", "src.bootstrap"),
    "adapters/inbound": ("src.adapters.outbound", "src.bootstrap"),
    "adapters/outbound": ("src.adapters.inbound", "src.bootstrap"),
}


def imported_modules(path: Path) -> list[str]:
    """List every module a file imports.

    Args:
        path: A Python file.

    Returns:
        The dotted names after ``import`` and ``from``.
    """
    tree = ast.parse(path.read_text(encoding="utf-8"))
    names: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.append(node.module)
    return names


@pytest.mark.parametrize("layer", sorted(FORBIDDEN))
def test_layer_only_depends_inwards(layer: str) -> None:
    """No file of the layer imports what lies outside it."""
    files = sorted((SRC / layer).rglob("*.py"))
    assert files, f"no files in {layer}"
    broken = [
        f"{path.relative_to(SRC)} imports {module}"
        for path in files
        for module in imported_modules(path)
        if module.startswith(FORBIDDEN[layer])
    ]
    assert broken == []
