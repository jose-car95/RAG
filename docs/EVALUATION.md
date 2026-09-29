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
| Los 8 modelos pydantic | Modelos + validación de los datasets públicos | `src/domain/models.py` + `tests/test_models.py` (11 tests: datasets públicos, UUID, campos extra, rangos, JSON de salida), slice #3 | EVIDENCED |
| CLI con Python Fire y los seis comandos | `uv run python -m src --help` lista los comandos | `tests/test_cli.py` (7 tests, slice #1) | EVIDENCED |
| Excepciones gestionadas y recursos con context managers | Sin tracebacks; `with` en ficheros y SQLite | Frontera de errores en `run` (`tests/test_error_boundary.py`, slice #2); `with open(...)` y errores de fichero traducidos en `load_dataset` (`tests/test_json_dataset.py`, slice #4); SQLite con `closing` + transacción y errores traducidos en `save_chunks` (`tests/test_index_corpus.py`, slice #20); el modelo en M5 | IN_PROGRESS |
| tqdm en operaciones largas | Barra visible en `index`, `search_dataset`, `answer_dataset` | `index` muestra `Indexing: 100%|██████████| 1969/1969` sobre el corpus real (slice #20); `search_dataset` en M3 y `answer_dataset` en M5 | IN_PROGRESS |
| Salida `StudentSearchResults` válida | La moulinette dice `Student data is valid: True` | `search_dataset` sobre `dataset_docs_public.json` → moulinette local `Student data is valid: True` (2026-09-17, slice #5); tests en `tests/test_search_dataset.py` | EVIDENCED |
| Salida `StudentSearchResultsAndAnswer` válida | JSON validado por el modelo | Test + demo (M5) | NOT_STARTED |
| Dos estrategias de chunking | Código de Python y de Markdown/texto, explicable | `src/domain/chunking.py` (`chunk_text` por títulos, `chunk_python` por definiciones con `ast`) + `tests/test_chunking.py` (37 tests, invariante incluido); corpus real: 206 `.md`/`.txt` → 1.759 chunks y 1.763 `.py` → 17.183 chunks, 0 violaciones (slices #18 y #19) | EVIDENCED |
| `--max_chunk_size` con default 2000 | Ningún chunk > 2000 | Invariante testeado en `tests/test_chunking.py` y medido en el índice real de 18.942 chunks (máximo 2000, 0 por encima); el flag se valida en `run_index` con la constante `MAX_CHUNK_SIZE` y 6 casos inválidos cubiertos en `tests/test_index_corpus.py` (slice #21) | EVIDENCED |
| TF-IDF o BM25 | Implementación propia explicable | Tokenización propia en `src/domain/tokenizer.py` + `tests/test_tokenizer.py` (10 tests), slice #22; BM25 en el slice #23. Material de estudio con la aritmética real en `docs/conceptos/busqueda-lexica-bm25.html` | IN_PROGRESS |
| `search "How to configure OpenAI server?" --k 10` | Resultados ordenados y explicables | Demo (M3) | NOT_STARTED |
| Qwen/Qwen3-0.6B por defecto, contexto dentro del límite de tokens | `answer ... --k 10` funciona en CPU | Demo (M5) | NOT_STARTED |
| Indexado ≤ 300 s | Tiempo medido | 3,65 s para 1.969 ficheros y 18.942 chunks (2026-09-23, slice #20); fila en la tabla de métricas de `docs/PROGRESS.md`. Se vuelve a medir en M3 con el índice invertido | EVIDENCED |
| El índice se guarda en SQLite en `data/processed/` | Fichero de base de datos y esquema explicable | `src/adapters/sqlite_index.py` (tabla plana `chunks`, SQL propio con consultas parametrizadas, sin FTS5 ni `bm25()`) + `tests/test_index_corpus.py` (7 tests), slice #20 | EVIDENCED |
| 200 preguntas ≤ 90 s | Tiempo medido | Tabla de métricas (M3, M4) | NOT_STARTED |
| Recall@5 docs ≥ 0.80 | Valor de la moulinette | Tabla de métricas con datasets públicos (M4) | NOT_STARTED |
| Recall@5 code ≥ 0.50 | Valor de la moulinette | Tabla de métricas con datasets públicos (M4) | NOT_STARTED |
| Calidad de respuesta (2 de 3 satisfactorias) | Respuestas coherentes y fundamentadas | Muestra revisada a mano (M5) | NOT_STARTED |
| Entradas degeneradas sin traceback | Query vacía, gibberish, `answer --k 0`, dataset inexistente | `index --max_chunk_size` con `0`, `-5`, `abc`, `2.5`, `2001` y `True` → un solo mensaje claro y salida `1` (slice #21); `k <= 0` y datasets inexistentes o malformados ya cubiertos (slices #4 y #5); query vacía y gibberish en M3-M5 | IN_PROGRESS |
| Nunca importar la moulinette | `grep` de imports vacío | `grep -rnE "^[[:space:]]*(import\|from)[[:space:]]+moulinette" src/ tests/` en `/cierra` | IN_PROGRESS |
| README: primera línea en cursiva + secciones de VIII | Checklist completa | Revisión (M6) | NOT_STARTED |
| Comprensión: 5 preguntas (4 de 5) | Respuestas propias de Jose | Ensayo oral (M6) | NOT_STARTED |
| Recode en vivo | Jose modifica el código sin ayuda | Ensayo con 3 modificaciones propuestas (M6) | NOT_STARTED |
| Repo de entrega solo con lo pedido | Sin `docs/eval`, moulinette, datos ni salidas | Checklist del repo de entrega (M6) | NOT_STARTED |
