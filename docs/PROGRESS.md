# PROGRESS

Leer al empezar cada sesión (ver `CLAUDE.md`, "Al empezar cada sesión").

## Estado actual

- **Milestone:** M1 — Modelos de datos y E/S de datasets (último slice en
  revisión). M0 cerrado el 2026-09-16.
- **Slices cerrados en M1:** #3 modelos pydantic; #4 `load_dataset` con
  errores traducidos.
- **Slice en revisión:** #5 "Write empty search results from search_dataset".
  Nace `src/application/` con el caso de uso `run_search_dataset`: valida
  `k` (entero `>= 1`), carga el dataset, crea un `MinimalSearchResults` con
  `retrieved_sources=[]` por pregunta y escribe un `StudentSearchResults` en
  `<save_directory>/<nombre del dataset>` con el adaptador nuevo
  `write_search_results` (`src/adapters/json_results.py`). La CLI solo llama
  al caso de uso e imprime `Saved student_search_results to <ruta>`.
- **Verificado (2026-09-17):**
  - `make lint` → flake8 sin salida; mypy `Success: no issues found in 15 source files`.
  - `make test` → `42 passed` (11 CLI, 5 frontera, 8 cargador, 11 modelos, 7 caso de uso).
  - `uv run python -m src search_dataset --dataset_path data/datasets/UnansweredQuestions/dataset_docs_public.json --k 10 --save_directory data/output/search_results/UnansweredQuestions` → `Saved student_search_results to data/output/search_results/UnansweredQuestions/dataset_docs_public.json`, exit 0.
  - **Salida de M1:** `./moulinette-ubuntu evaluate_student_search_results data/output/search_results/UnansweredQuestions/dataset_docs_public.json data/datasets/AnsweredQuestions/dataset_docs_public.json --k 10 --max_context_length 2000` → `Student data is valid: True`, 100 preguntas, Recall@5 0.000.
  - `... --k 0` → `ERROR: k must be a positive integer`, exit 1.
  - `make run ARGS="search_dataset --dataset_path ... --k 2 --save_directory ..."` → funciona (los argumentos del programa van dentro de `ARGS`, no sueltos tras `make run`).
- **Siguiente paso propuesto:** tras el merge, cerrar M1 y planificar M2
  (indexado): crear los issues de M2 y M3 y resolver con `/decide` los
  ABIERTOS de M2 (tipos de fichero a indexar, `last_character_index`
  inclusivo o exclusivo, flags de ruta de `index`).

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
| 2026-09-17 | `k` debe ser un entero `>= 1` (opción A); si no, `k must be a positive integer` y no se escribe nada | Detalle en `docs/SPEC_NOTES.md` |
| 2026-09-17 | Nace `src/application/` con `run_search_dataset`; la CLI llama al caso de uso y ya no al adaptador | Primer caso que coordina varias piezas (validar, cargar, construir, escribir) |
| 2026-09-17 | Adaptador nuevo `src/adapters/json_results.py` para escribir resultados (no dentro de `json_dataset.py`) | Son otros datos; en M5 `answer_dataset` leerá estos ficheros desde el mismo módulo |
| 2026-09-17 | El caso de uso importa los adaptadores directamente, sin puertos | Solo hay una implementación de cada uno; un puerto sería una abstracción por si acaso |
| 2026-09-17 | La moulinette queda descomprimida en `./moulinette-ubuntu` (10,3 MB, ignorada por git) para comprobaciones locales y `/mide` | Nunca se usa desde `src/` ni `tests/` |
| 2026-09-17 | Los comandos largos del pipeline van paso a paso en el README (M6), no como reglas del `Makefile` | Las rutas y nombres de los datasets cambian en la corrección; en el README se ajustan a mano sin tocar código |
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
- **Ensayar en el primer `/ensayo` (paso 8 del slice #5, 2026-09-17):** por
  qué `run_search_dataset` vive en `application/` y no en la CLI; por qué se
  valida `k` antes de cargar; por qué pydantic rechazaba
  `StudentSearchResults(search_results, k)` (argumentos por posición) y qué
  fallaba en `search_results: list = [MinimalSearchResults]` (tipo frente a
  valor). Jose confirma haberlo entendido y pidió seguir.
- **Pulido M6:** rechazar un `--save_directory` que parezca un fichero
  (p. ej. termina en `.json`); hoy crea una carpeta con ese nombre.

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
