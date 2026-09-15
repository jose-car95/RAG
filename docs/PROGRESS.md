# PROGRESS

Leer al empezar cada sesión (ver `CLAUDE.md`, "Al empezar cada sesión").

## Estado actual

- **Milestone:** M0 — Esqueleto ejecutable (en curso).
- **Último slice completado:** #1 "Expose CLI entry point with required
  commands". `uv run python -m src` es una CLI de Fire (`RagCli`) con los seis
  comandos del enunciado como stubs que imprimen
  `<comando>: not implemented yet`. Se borró `tests/test_scaffold.py`
  (OK de Jose): `tests/test_cli.py` ya ejecuta el programa entero.
- **Slice en curso:** #9 "Move CLI into the adapters layer" (refactor sin
  cambio de comportamiento): `src/interface/cli.py` → `src/adapters/cli.py`.
- **Verificado (2026-09-15):**
  - `make lint` → flake8 sin salida; mypy `Success: no issues found in 5 source files`.
  - `make test` → `7 passed` (`tests/test_cli.py`, CLI en subproceso).
  - `uv run python -m src search "What is vLLM?" --k 10` → `search: not implemented yet`, exit 0.
  - `grep -rnE "^[[:space:]]*(import|from)[[:space:]]+moulinette" src/ tests/` → sin resultados.
- **Siguiente paso propuesto:** slice #2 "Stop unexpected errors at the CLI
  boundary".

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
- **Volver a explicar (paso 8 del slice #1, 2026-09-15):** el flujo completo
  `uv run python -m src ...` → `src/__main__.py` → `main()` → `RagCli()` →
  Fire → método. Jose explicó bien Fire y el invariante de nombres; el
  recorrido completo queda para el primer `/ensayo`.

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
