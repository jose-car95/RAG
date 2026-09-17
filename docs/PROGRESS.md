# PROGRESS

Leer al empezar cada sesión (ver `CLAUDE.md`, "Al empezar cada sesión").

## Estado actual

- **Milestone:** M1 — Modelos de datos y E/S de datasets (en curso). M0
  cerrado el 2026-09-16.
- **Slices cerrados en M1:** #3 los 8 modelos pydantic en
  `src/domain/models.py` (rangos validados, decisión B).
- **Slice en revisión:** #4 "Load question datasets from JSON files".
  `load_dataset(path)` en `src/adapters/json_dataset.py` (primer adaptador de
  salida) abre el fichero con `with` y UTF-8, lo lee con `json.load` y lo
  valida con `RagDataset.model_validate`. Traduce cada fallo a un
  `ValueError` de una línea con `raise ... from error`: no existe / no se
  puede leer / no es JSON / no tiene forma de dataset. `search_dataset`
  lo usa e imprime cuántas preguntas cargó.
- **Verificado (2026-09-17):**
  - `make lint` → flake8 sin salida; mypy `Success: no issues found in 11 source files`.
  - `make test` → `33 passed` (9 CLI, 5 frontera, 8 cargador, 11 modelos).
  - `uv run python -m src search_dataset --dataset_path /nonexistent/dataset.json --k 10` → `ERROR: dataset not found: /nonexistent/dataset.json`, exit 1.
  - `uv run python -m src search_dataset --dataset_path data/datasets/UnansweredQuestions/dataset_docs_public.json --k 10` → `search_dataset: loaded 100 questions (search not implemented yet)`, exit 0.
  - `grep` de imports de la moulinette y de otras capas en `src/domain/` → sin resultados.
- **Siguiente paso propuesto:** slice #5 "Write empty search results from
  search_dataset": nace `src/application/` (primer caso de uso) y se decide
  la semántica de `k <= 0`.

## Decisiones

| Fecha | Decisión | Motivo |
|---|---|---|
| 2026-09-13 | Solo CPU; `torch` desde wheels de CPU cuando llegue M5 | Las máquinas de la escuela no tienen GPU |
| 2026-09-13 | Cachés en su ruta por defecto mientras desarrollamos; se revisan en la máquina de la escuela al final | Disco local sobrado; la escuela tiene menos espacio |
| 2026-09-13 | `docs/` completa sube al repo de trabajo; el repo de entrega es otro y lo prepara Jose | Este repo es el taller personal |
| 2026-09-13 | No suben `data/raw/`, `data/processed/`, `data/output/`; sí los datasets públicos (44 KB) | El corpus ya viaja como zip en `docs/`; lo demás es generado |
| 2026-09-13 | El README no documenta la descarga del corpus ni cita la escala de evaluación | Oficialmente Jose no tiene la escala |
| 2026-09-13 | Milestones sin fechas; horizonte de 4 semanas | Avanzar lo más rápido posible |
| 2026-09-13 | Mandatory-first estricto; bonus solo tras M6 | El bonus no puntúa sin el obligatorio completo |
| 2026-09-13 | Arquitectura por capas (hexagonal pragmática): domain ← application ← adapters/interface | Mantenible y extensible a los bonus sin sobreingeniería |
| 2026-09-13 | Índice persistido en SQLite con `sqlite3`, sin ORM y sin FTS5 `bm25()` en lo obligatorio | Aprender bases de datos y poder explicar el ranking propio |
| 2026-09-13 | BM25 como método léxico (provisional, se confirma en M3) | Mejor recall esperado que TF-IDF y explicable |
| 2026-09-13 | pytest como framework de tests | Lo sugiere el enunciado y es el estándar |
| 2026-09-13 | flake8 y mypy excluyen `data/` y `docs/` | El corpus de vLLM contiene `.py` ajenos y el corrector lo tiene descomprimido |
| 2026-09-13 | Cero atribución a la IA en commits y PRs; uso declarado en `docs/AI_USAGE.md` y README | Regla personal de Jose |
| 2026-09-13 | Jose revisa en VS Code los cambios sin stage antes de cada `git add` | Ver los cambios resaltados antes de commitear |
| 2026-09-13 | Una rama por slice; se borra (local y remota) tras el merge | No acumular ramas muertas |
| 2026-09-13 | Comandos propios `/slice`, `/mide`, `/ensayo` | Aprobados por Jose; tareas repetidas con pasos fáciles de olvidar |
| 2026-09-15 | Fire recibe una instancia (`RagCli()`), no la clase | Con la clase, `--help` no lista los comandos |
| 2026-09-15 | Los tests de la CLI ejecutan `python -m src` en un subproceso | Fire escribe en stderr y termina el proceso; así se ve lo mismo que el corrector |
| 2026-09-15 | Docstrings de `src/` escritos por la IA a petición de Jose | Apoyo con el inglés; declarado en `docs/AI_USAGE.md` |
| 2026-09-15 | Se acepta y documenta el comportamiento de Fire con flags desconocidos y palabras sobrantes (opción 1) | Sin traceback y fuera del enunciado; detalle en `docs/SPEC_NOTES.md` |
| 2026-09-16 | La frontera de errores es `run(component, argv) -> int` en `src/adapters/cli.py`; devuelve el código y solo `__main__.py` llama a `sys.exit` | Testeable con un doble de test sin subproceso: es la razón presente para recibir el componente |
| 2026-09-16 | Códigos de salida como constantes `EXIT_SUCCESS` (0), `EXIT_ERROR` (1), `EXIT_INTERRUPTED` (130); el 2 de Fire no se captura | Convención Unix (130 = 128 + SIGINT); un solo sitio que tocar en un recode |
| 2026-09-16 | La frontera deja pasar el `SystemExit` de Fire | Medido: `--help` es `SystemExit(0)` y los errores de uso `SystemExit(2)`; capturarlo rompería la ayuda y mezclaría «me llamaste mal» (2) con «fallé» (1) |
| 2026-09-16 | Prefijo `ERROR:` en los mensajes de la frontera (antes `Error:`) | Decisión de Jose: mismo formato que Fire. Cambio de requisito del issue #2, registrado en el issue #12; los tests se actualizaron por eso, no para que pasaran |
| 2026-09-16 | `fire.Fire(..., name="src")` | Los mensajes de uso mostraban `__main__.py` |
| 2026-09-16 | Rangos de `MinimalSource`: índices `>= 0` y `first <= last` (opción B); el ancho de 2000 no es regla del modelo | Detectar fallos del chunking en el momento; detalle en `docs/SPEC_NOTES.md` |
| 2026-09-16 | Modelos en `src/domain/models.py` con `list[...]` (no `List` del enunciado) | Sintaxis estándar desde Python 3.9; mismo significado |
| 2026-09-16 | Mensaje del `ValueError` y docstrings de `models.py` escritos por la IA a petición de Jose | Apoyo con el inglés; declarado en `docs/AI_USAGE.md` |
| 2026-09-17 | `load_dataset` traduce los errores de `open`, `json` y pydantic a `ValueError` de una línea con `raise ... from error`; el prefijo `ERROR:` solo lo pone la frontera `run` | Los originales no nombran el fichero (JSON), usan jerga (`[Errno 2]`) o ocupan 4 líneas (pydantic); el error original queda como `__cause__`. Fire no se solapa: valida la llamada, no el contenido de los datos |
| 2026-09-17 | Los mensajes con detalle (línea y columna del JSON, campo que falla en pydantic) se dejan para M6 | Decisión de Jose: pulir mensajes al final |
| 2026-09-17 | Provisional: `RagCli.search_dataset` llama directamente al adaptador `load_dataset` | La capa `application/` nace en el slice #5 con el primer caso de uso real; crearla para una línea sería especulativo |
| 2026-09-17 | Se mantiene `.flake8` en vez de pasar las exclusiones al `Makefile` | El enunciado da el comando literal `flake8 .`; el fichero aplica a quien ejecute flake8 (corrector, VS Code, CI). Sin él: 49.694 errores ajenos (40.788 de `.venv`, 8.906 de `data/`) |
| 2026-09-17 | Se desarrolla con Python 3.12 (`.python-version`); en la escuela (Python 3.10) `uv sync` descargará 3.12 automáticamente | Misma versión en casa, CI y escuela. Plan B si la descarga falla: `.python-version` = `3.10` (el código pasa `mypy --python-version 3.10`) |
| 2026-09-15 | La CLI vive en `src/adapters/` (carpeta plana, opción B); desaparece `src/interface/` | En hexagonal la CLI es un adaptador de entrada; `interface` chocaba con "interfaz" = puerto. Se descartó separar `inbound/`/`outbound/` (opción C) por simplicidad |

## Métricas

Gates de métrica locales (necesitan corpus y modelo). La línea base se mide en
M3 antes de optimizar nada.

| Fecha | Métrica | Valor | Umbral | Comando que lo reproduce |
|---|---|---|---|---|
| — | Tiempo de indexado | — | ≤ 300 s | pendiente (M2) |
| — | 200 preguntas (docs + code) | — | ≤ 90 s | pendiente (M3) |
| — | Recall@5 docs (públicos) | — | ≥ 0.80 | pendiente (M3) |
| — | Recall@5 code (públicos) | — | ≥ 0.50 | pendiente (M3) |

## Preguntas abiertas

- Ver los puntos **ABIERTO** de `docs/SPEC_NOTES.md` (tipos de fichero a
  indexar, `last_character_index` inclusivo o exclusivo, validación de
  rangos en `MinimalSource`, semántica de `k <= 0` y query vacía).
- **Ensayar en el primer `/ensayo`:** el recorrido completo
  `python -m src` → `__main__.py` → `main()` → `run(RagCli())` → Fire →
  método, y el viaje del código de salida (`run` decide el número, `main` y
  `__main__.py` lo pasan, `sys.exit` lo entrega). Pendiente desde el paso 8
  del slice #1; se volvió a explicar en el slice #2 (2026-09-16) y Jose
  confirma haberlo entendido.

## Notas de GitHub

- **Tablero:** proyecto **#5** "RAG against the machine",
  https://github.com/users/jose-car95/projects/5, enlazado a `jose-car95/RAG`.
- **Columnas (campo Status):** `Todo`, `In progress`, `In review`, `Done`.
- **Workflows verificados por API (2026-09-14):** los 11 activos. Pero al
  cerrarse #6 su tarjeta pasó de `In review` a `Todo` en vez de a `Done`:
  probablemente `Item closed` o `Pull request merged` apuntan a `Todo`
  (la API no deja leer su valor). Jose debe revisarlos. Hasta confirmarlo,
  el agente comprueba la tarjeta tras cada merge y la corrige a mano.
  Más síntomas (2026-09-15): #1 volvió de `In progress` a `Todo` al abrir su
  PR, otra vez a `Todo` estando en `In review`, y se quedó en `In review`
  tras cerrarse. Sospechosos: `Pull request linked to issue`,
  `Item added to project`, `Item closed`, `Pull request merged` y
  `Auto-add to project`.
  Jose corrigió los workflows el 2026-09-15 tras el merge de #9 (cuya
  tarjeta hubo que mover a `Done` a mano).
  **Verificado 2026-09-16: funcionan.** La tarjeta #2 pasó sola a
  `In review` al abrir la PR #11 y a `Done` 3 s después del merge. El agente
  solo mueve a mano `In progress` al empezar un slice (no hay workflow para
  eso) y comprueba el resto.
  Excepción (2026-09-16): la tarjeta #12 no pasó sola a `Done` tras el merge
  de la PR #13 y se movió a mano. Causa desconocida; seguir comprobando.
- **Vistas (2026-09-13):** solo existe `View 1` (tabla, sin agrupar). Faltan
  "Board por Status" y "Tabla por milestone"; no se pueden crear por API.
- **Mueve el agente:** la tarjeta a `In progress` al empezar cada slice, y a
  `In review` en `/cierra` si la automatización no lo hizo.
- **Mueve Jose:** el merge de la PR.
- **Ramas:** una por slice; tras el merge el agente borra la local y la remota
  y actualiza `main` (ver `CLAUDE.md`, "Tras el merge").
- **Etiquetas:** `feat`, `fix`, `docs`, `test`, `chore`, `blocked`,
  `spec-question`. Las 10 por defecto de GitHub se borraron el 2026-09-13
  con OK de Jose.
- **Milestones:** M0-M7, idénticos a `docs/PLAN.md`.

## Checklist del repo de entrega (para M6)

- [ ] Sin `docs/eval/`, moulinette ni datasets privados.
- [ ] Sin `data/raw/`, `data/processed/`, `data/output/`.
- [ ] `pyproject.toml`, `uv.lock`, `.python-version`, `Makefile`, `README.md`, `src/`.
- [ ] Primera línea del README en cursiva con el login.
- [ ] `uv sync` y `make lint` en un clon limpio en la máquina de la escuela.
- [ ] En la escuela (solo Python 3.10): comprobar que `uv sync` descarga
  Python 3.12 (red), dónde lo guarda (`uv python dir`) y cuánto ocupa; si
  falta cuota, usar `UV_PYTHON_INSTALL_DIR`. Plan B: `.python-version` =
  `3.10`.
