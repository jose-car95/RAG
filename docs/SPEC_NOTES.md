# SPEC NOTES

Zonas grises de la especificación y cómo las interpretamos. Fuente de verdad:
`docs/en.subject.pdf` (versión 2.0). Toda ambigüedad nueva se registra aquí
ANTES de implementarla, y su issue lleva la etiqueta `spec-question`.

Etiquetas: **FACT** (lo dice la fuente), **INTERPRETACIÓN** (lectura razonada
de un hueco), **DECISIÓN** (elección de ingeniería que hay que saber
justificar), **ABIERTO** (pendiente, con límite).

---

## Rutas y salidas

- **FACT** — `file_path` se compara literalmente: `data/raw/vllm-0.10.1/...`,
  relativo a la raíz del proyecto (VI.2, VI.5). Verificado 2026-09-13: las 398
  fuentes de los datasets públicos apuntan a ficheros existentes con ese
  prefijo.
- **FACT** — Ninguna fuente devuelta puede superar 2000 caracteres; una sola
  invalida toda la salida (VI.1).
- **INTERPRETACIÓN** — El fichero que escriben `search_dataset` y
  `answer_dataset` se llama igual que el dataset de entrada
  (`<save_directory>/<basename>`). El enunciado lo muestra así en VI.7.2 y
  mantener "docs"/"code" en el nombre distingue los resultados.
- **INTERPRETACIÓN** — `--save_directory` tiene valor por defecto:
  `data/output/search_results` para `search_dataset` y
  `data/output/search_results_and_answer` para `answer_dataset`. VI.6 lista
  las opciones "como mínimo" pero un comando sin ellas no debe romper.
- **INTERPRETACIÓN** — Todas las rutas pueden ser absolutas y estar fuera del
  repo; el directorio de salida se crea si no existe.

## Corpus

- **INTERPRETACIÓN** — Si `data/raw/` no existe o está vacío, `index` termina
  con un mensaje claro y código de salida distinto de 0, sin traceback. El
  README no explica de dónde descargar el corpus (decisión de Jose,
  2026-09-13).
- **ABIERTO** — Qué ficheros se indexan: ¿solo `.py` y `.md`, o también
  `.rst`, `.txt`, `.yaml`...? El enunciado dice "the files you judge useful"
  (VI.1). Límite: antes de empezar M2.
- **ABIERTO** — ¿`last_character_index` es exclusivo (como el slicing de
  Python, `text[first:last]`) o inclusivo? Hay que comprobarlo contra los
  datasets públicos. Límite: antes de empezar M2.

## Modelos de datos

- **FACT** — Los 8 modelos de VI.4 son obligatorios y se pueden ampliar con
  campos o modelos nuevos.
- **ABIERTO** — ¿Validamos `first_character_index <= last_character_index` en
  `MinimalSource`? El enunciado no lo pide; los datasets públicos lo cumplen
  siempre (comprobado 2026-09-13). Límite: slice "Define the pydantic data
  models".

## Entradas degeneradas

- **FACT** — Query vacía, query sin sentido, `k=0`, ficheros inexistentes y
  JSON malformado no pueden producir un traceback (VI.6).
- **ABIERTO** — Semántica de `k <= 0` y de la query vacía: ¿resultado vacío
  válido o mensaje de error con código distinto de 0? Límite: M1 (dataset) y
  M3 (search).

## Recuperación y calidad

- **DECISIÓN (provisional)** — Método léxico principal: BM25, implementado por
  Jose. Se confirma con `/decide` al empezar M3.
- **DECISIÓN** — El índice se guarda en SQLite con `sqlite3` de la librería
  estándar, sin ORM. La extensión FTS5 y su función `bm25()` no se usan en la
  parte obligatoria: la base de datos guarda, el ranking lo calcula nuestro
  código. Motivo: aprender los conceptos de bases de datos y poder explicar el
  método en la defensa (2026-09-13).
- **FACT** — Recall@k: una fuente correcta cuenta como encontrada si un
  resultado está en el mismo fichero y solapa su rango con IoU > 0.05 (VII.1).
  Nuestro `evaluate` reimplementa ese criterio; nunca importa ni llama a la
  moulinette (VI.6).
- **DECISIÓN** — Los datasets privados (`docs/eval/datasets_private.zip`) y
  la moulinette no se usan jamás desde el código, ni para medir ni para
  ajustar. Los datasets públicos sirven para medir; los parámetros (p. ej.
  `k1` y `b` de BM25, tamaño de chunk) se eligen con un motivo explicable, no
  por búsqueda ciega contra los públicos, y el motivo queda en el README.

## Entorno

- **DECISIÓN** — Solo CPU. `torch` se instalará desde el índice de wheels de
  CPU y la inferencia usa `device="cpu"` (Jose, 2026-09-13: las máquinas de la
  escuela no tienen GPU).
- **DECISIÓN** — flake8 y mypy excluyen `data/` y `docs/`: el corpus de vLLM
  contiene ficheros `.py` que no son nuestros y el corrector ejecuta
  `make lint` con el corpus descomprimido. No es silenciar el linter: todo
  nuestro código se sigue revisando.
