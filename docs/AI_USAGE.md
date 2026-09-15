# Uso de IA

Una línea por slice. Registro contemporáneo para la sección "Resources" del
README (el enunciado exige declarar para qué tareas y qué partes se usó IA).

| Fecha | Slice / fase | Qué hizo la IA | Qué escribió o reescribió Jose |
|---|---|---|---|
| 2026-09-13 | Fase A-B: arranque | Lectura del enunciado, entrevista, andamiaje (`pyproject.toml`, `Makefile`, `.flake8`, `.gitignore`, CI, plantilla de PR, `CLAUDE.md`, `docs/`, `.claude/`), configuración de GitHub (etiquetas, milestones, issues, tablero) | Decisiones de alcance, arquitectura por capas, SQLite como almacén del índice, reglas del contrato de trabajo |
| 2026-09-13 | #6 revisión local y comandos | Redacción de las reglas de revisión y ramas en `CLAUDE.md`, `/cierra`, y de `/slice`, `/mide`, `/ensayo` | Definición del flujo (revisión en VS Code, borrado de ramas tras el merge) |
| 2026-09-15 | #1 CLI entry point | Explicación de Fire, `python -m` y `__main__.py`; diseño mínimo; test en rojo `tests/test_cli.py` (y su corrección del canal de `--help`); dependencia `fire` y override de mypy; docstrings de `src/__main__.py`, `src/interface/__init__.py` y `src/interface/cli.py` a petición de Jose; revisión | Código de `src/__main__.py` y `src/interface/cli.py` (clase `RagCli`, seis métodos, `main`), correcciones de import, nombres, sangría y longitud de línea |
