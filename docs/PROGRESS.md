# PROGRESS

Leer al empezar cada sesión (ver `CLAUDE.md`, "Al empezar cada sesión").

## Estado actual

- **Milestone:** M0 — Esqueleto ejecutable (sin empezar).
- **Último paso completado:** Fase B, andamiaje. Repo, configuración, CI,
  documentos vivos, comandos de `.claude/`, milestones M0-M7, issues #1-#5 y
  tablero #5. Cero código de producción.
- **Verificado (2026-09-13), con el corpus descomprimido en `data/raw/`:**
  - `uv sync` → entorno creado, `uv.lock` generado.
  - `make lint` → flake8 sin salida; mypy `Success: no issues found in 2 source files`.
  - `make test` → `1 passed` (smoke test del paquete `src`).
  - `make lint-strict` → `Success: no issues found in 2 source files`.
- **Siguiente paso propuesto:** explicar RAG y la arquitectura por capas, y
  arrancar el slice #1 "Expose CLI entry point with required commands".

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
- Comandos propios del proyecto propuestos en Fase B, pendientes de OK de Jose.

## Notas de GitHub

- **Tablero:** proyecto **#5** "RAG against the machine",
  https://github.com/users/jose-car95/projects/5, enlazado a `jose-car95/RAG`.
- **Columnas (campo Status):** `Todo`, `In progress`, `In review`, `Done`.
- **Se mueve solo:** NADA todavía. Verificado por API (2026-09-13): los
  workflows `Item added to project`, `Pull request linked to issue`,
  `Item closed` y `Pull request merged` están desactivados y GitHub no permite
  activarlos por API. Jose los activa desde la web (Project → `...` →
  Workflows); actualizar esta línea cuando estén activos.
- **Vistas:** GitHub no permite crearlas por API; Jose crea "Board por Status"
  y "Tabla por milestone" desde la web.
- **Mueve el agente:** la tarjeta a `In progress` al empezar cada slice, y a
  `In review` en `/cierra` si la automatización no lo hizo.
- **Mueve Jose:** el merge de la PR (que dispara `Done`).
- **Etiquetas:** `feat`, `fix`, `docs`, `test`, `chore`, `blocked`,
  `spec-question`.
- **Milestones:** M0-M7, idénticos a `docs/PLAN.md`.

## Checklist del repo de entrega (para M6)

- [ ] Sin `docs/eval/`, moulinette ni datasets privados.
- [ ] Sin `data/raw/`, `data/processed/`, `data/output/`.
- [ ] `pyproject.toml`, `uv.lock`, `.python-version`, `Makefile`, `README.md`, `src/`.
- [ ] Primera línea del README en cursiva con el login.
- [ ] `uv sync` y `make lint` en un clon limpio en la máquina de la escuela.
