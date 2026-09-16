# EVALUATION

Matriz interna de evidencias. Fuentes: `docs/en.subject.pdf` y, como guía
interna, la escala de `docs/eval/`. Este fichero **no va al repo de entrega**
y el README nunca cita la escala.

Estados: `NOT_STARTED` / `IN_PROGRESS` / `EVIDENCED` / `BLOCKED`. Solo se marca
`EVIDENCED` con un test, comando, fichero o demo concreta.

| Ítem | Evidencia requerida | Evidencia planeada | Estado |
|---|---|---|---|
| Python 3.10+, uv, `pyproject.toml` + `uv.lock` en la raíz | `uv sync` limpio desde la raíz | `uv sync` en un clon limpio; job de CI `uv sync --locked` | IN_PROGRESS |
| Makefile: install, run, debug, clean, lint | Cada regla ejecuta | `make <regla>` con salida pegada | IN_PROGRESS |
| flake8 + mypy con los flags del enunciado | `make lint` sin errores | CI `lint` y `types` en verde | IN_PROGRESS |
| Los 8 modelos pydantic | Modelos + validación de los datasets públicos | Tests del slice de modelos (M1) | NOT_STARTED |
| CLI con Python Fire y los seis comandos | `uv run python -m src --help` lista los comandos | `tests/test_cli.py` (7 tests, slice #1) | EVIDENCED |
| Excepciones gestionadas y recursos con context managers | Sin tracebacks; `with` en ficheros y SQLite | Frontera de errores en `run` (`tests/test_error_boundary.py`, 5 tests, slice #2); context managers en M1-M2 | IN_PROGRESS |
| tqdm en operaciones largas | Barra visible en `index`, `search_dataset`, `answer_dataset` | Demo en terminal (M2, M3, M5) | NOT_STARTED |
| Salida `StudentSearchResults` válida | La moulinette dice `Student data is valid: True` | Comprobación local (M1) | NOT_STARTED |
| Salida `StudentSearchResultsAndAnswer` válida | JSON validado por el modelo | Test + demo (M5) | NOT_STARTED |
| Dos estrategias de chunking | Código de Python y de Markdown/texto, explicable | Tests del invariante de chunks (M2) | NOT_STARTED |
| `--max_chunk_size` con default 2000 | Ningún chunk > 2000 | Test del invariante (M2) | NOT_STARTED |
| TF-IDF o BM25 | Implementación propia explicable | Tests + demo `search` (M3) | NOT_STARTED |
| `search "How to configure OpenAI server?" --k 10` | Resultados ordenados y explicables | Demo (M3) | NOT_STARTED |
| Qwen/Qwen3-0.6B por defecto, contexto dentro del límite de tokens | `answer ... --k 10` funciona en CPU | Demo (M5) | NOT_STARTED |
| Indexado ≤ 300 s | Tiempo medido | Tabla de métricas (M2, M3) | NOT_STARTED |
| 200 preguntas ≤ 90 s | Tiempo medido | Tabla de métricas (M3, M4) | NOT_STARTED |
| Recall@5 docs ≥ 0.80 | Valor de la moulinette | Tabla de métricas con datasets públicos (M4) | NOT_STARTED |
| Recall@5 code ≥ 0.50 | Valor de la moulinette | Tabla de métricas con datasets públicos (M4) | NOT_STARTED |
| Calidad de respuesta (2 de 3 satisfactorias) | Respuestas coherentes y fundamentadas | Muestra revisada a mano (M5) | NOT_STARTED |
| Entradas degeneradas sin traceback | Query vacía, gibberish, `answer --k 0`, dataset inexistente | Tests + ejecución local de los cuatro casos (M6) | NOT_STARTED |
| Nunca importar la moulinette | `grep` de imports vacío | `grep -rnE "^[[:space:]]*(import\|from)[[:space:]]+moulinette" src/ tests/` en `/cierra` | IN_PROGRESS |
| README: primera línea en cursiva + secciones de VIII | Checklist completa | Revisión (M6) | NOT_STARTED |
| Comprensión: 5 preguntas (4 de 5) | Respuestas propias de Jose | Ensayo oral (M6) | NOT_STARTED |
| Recode en vivo | Jose modifica el código sin ayuda | Ensayo con 3 modificaciones propuestas (M6) | NOT_STARTED |
| Repo de entrega solo con lo pedido | Sin `docs/eval`, moulinette, datos ni salidas | Checklist del repo de entrega (M6) | NOT_STARTED |
