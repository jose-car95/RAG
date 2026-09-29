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
  relativo a la raíz del proyecto (VI.2, VI.5). Verificado 2026-09-13: las 199
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
- **DECISIÓN (2026-09-18, Jose, opción 3A)** — VI.6 exige que todas las
  rutas de entrada y salida sean configurables, pero no da flags para el
  corpus ni para el índice. Añadimos flags opcionales propios con valor por
  defecto: `index --raw_directory` (`data/raw`) e `--index_path`
  (`data/processed/index.db`, un único fichero SQLite), también en `search`,
  `search_dataset` y `answer`. Con los valores por defecto, los comandos del
  enunciado funcionan sin cambios.
- **INTERPRETACIÓN** — Las rutas de los ficheros del corpus conservan el
  prefijo tal como se pasa `--raw_directory` (por defecto `data/raw/...`),
  porque la moulinette compara `file_path` literalmente con
  `data/raw/vllm-0.10.1/...`.

## Corpus

- **INTERPRETACIÓN** — Si `data/raw/` no existe o está vacío, `index` termina
  con un mensaje claro y código de salida distinto de 0, sin traceback. El
  README no explica de dónde descargar el corpus (decisión de Jose,
  2026-09-13).
- **DECISIÓN (2026-09-18, Jose, opción 1A)** — Se indexan `.py`, `.md` y
  `.txt` (1.969 ficheros: 1.763 + 178 + 28). Coincide con las dos estrategias
  de chunking que exige VI.1 (Python y Markdown/texto) y cubre el 100% de las
  199 fuentes públicas (99 `.py`, 97 `.md`, 3 `.txt`). El resto (~900
  ficheros `.json`, `.cu`, `.yaml`, `.png`...) sería ruido y tiempo de
  indexado. Riesgo aceptado: una pregunta privada que apunte a otro tipo.
- **FACT (medido 2026-09-18)** — `last_character_index` es EXCLUSIVO, como
  el slicing de Python `text[first:last]`: 6 de las 199 fuentes públicas
  terminan en `len(fichero)` (imposible si fuera inclusivo) y en 99 el
  carácter en `last` es el salto de línea que queda fuera. Consecuencia: la
  anchura de un chunk es `last - first` y debe ser `<= max_chunk_size`.

## Chunking

- **DECISIÓN (2026-09-18, Jose, opción B)** — Markdown y texto se trocean
  en cascada: primero por títulos (`#` al inicio de línea), después
  juntando párrafos seguidos (separados por línea en blanco) hasta llenar
  `max_chunk_size`, y solo como último recurso con corte a lo bruto. Motivo,
  medido en el corpus (206 `.md`/`.txt`, 2026-09-18, sin mirar las
  respuestas de los datasets): el 61% de los ficheros supera 2000
  caracteres, pero el 93% de las secciones y el 99,7% de los párrafos caben.
  Juntar secciones pequeñas (opción C) es un experimento de M4.
- **DECISIÓN (2026-09-22, Jose, opción A)** — Python se trocea con `ast` por
  las definiciones de primer nivel (`def`, `async def`, `class`, con sus
  decoradores) y lo que no cabe pasa por la misma cascada de texto (líneas en
  blanco → corte a lo bruto). Medido en el corpus (1.763 `.py`, 2026-09-22):
  0 errores de sintaxis, pero el 23,7% de las definiciones de primer nivel
  pasa de 2000 caracteres (1.302 clases) y el 12,4% de los métodos de esas
  clases también, así que el último recurso es inevitable. Bajar a los
  métodos con `ast` (opción B) es un experimento de M4; PEP 8 deja una línea
  en blanco entre métodos, así que el fallback ya corta de hecho entre ellos.
- **FACT (medido 2026-09-22)** — Un fichero que no es Python válido lanza
  `SyntaxError` al parsearlo; en ese caso se trocea como texto.

## Índice en SQLite

- **DECISIÓN (2026-09-23, Jose, opciones 1A y 2A)** — Una sola tabla plana
  `chunks(id, file_path, first_character_index, last_character_index, text)`,
  sin tabla `files` ni clave ajena: repetir la ruta cuesta ~1 MB de los ~25 MB
  del índice y evita un `JOIN` en la consulta más frecuente (M3). Se guarda
  el **texto** del chunk: así `search` puede mostrarlo y M5 construye el
  prompt sin releer disco.
- **FACT (medido 2026-09-23)** — Los 1.969 ficheros indexables son UTF-8
  válido y contienen 20,1 millones de caracteres, así que el texto se lee en
  UTF-8 estricto.
- **INTERPRETACIÓN** — El mensaje final de `index` es el literal del
  enunciado (VI.7.2), `Ingestion complete! Indices saved under
  data/processed/`, construido con la carpeta real de `--index_path` para que
  siga siendo cierto si se cambia la ruta.

## Validación de `max_chunk_size`

- **FACT (medido 2026-09-24)** — Fire ignora la anotación `int` y adivina el
  tipo: `abc` llega como `str`, `2.5` como `float`, `True` como `bool`. Y
  `bool` hereda de `int`, así que `isinstance(True, int)` es `True`.
- **FACT (medido 2026-09-24)** — `max_chunk_size` es el paso de `range` en
  `src/domain/chunking.py:30`. Con paso 0 lanza
  `range() arg 3 must not be zero`; con paso negativo el `range` queda vacío,
  así que no se produce ningún chunk y el programa imprimía
  `Ingestion complete!` con salida `0` y un índice vacío.
- **DECISIÓN (2026-09-25, Jose, opción A)** — La validación vive en
  `run_index`, en las primeras líneas y antes de leer el corpus, no en la
  CLI: la regla 1..2000 viene del enunciado y debe valer para cualquier
  adaptador de entrada. Además `save_chunks` borra el fichero para
  reconstruirlo, así que validar tarde destruiría un índice bueno.
- **DECISIÓN (2026-09-25, Jose, opción B1)** — Se rechaza el `bool` de forma
  explícita, aquí y en la validación de `k` de `run_search_dataset`.
- **INTERPRETACIÓN** — El mensaje es único para los seis casos inválidos:
  `max_chunk_size must be an integer between 1 and 2000`, construido con la
  constante `MAX_CHUNK_SIZE` para que nunca contradiga al límite real.

## Modelos de datos

- **FACT** — Los 8 modelos de VI.4 son obligatorios y se pueden ampliar con
  campos o modelos nuevos.
- **DECISIÓN (2026-09-16, Jose, opción B)** — `MinimalSource` exige índices
  `>= 0` y `first_character_index <= last_character_index`. Motivo: en Python
  un rango al revés da texto vacío y un índice negativo cuenta desde el final
  del fichero, ambos sin error; validarlo detecta fallos del chunking (M2) en
  el momento. Los datasets públicos lo cumplen (199 fuentes, 2026-09-13). El
  límite de 2000 caracteres de ancho NO es regla del modelo (el modelo también
  valida los datasets de referencia y `--max_chunk_size` es configurable):
  pertenece al chunking (M2).
- **FACT (medido 2026-09-16, pydantic 2.13.5)** — Con
  `List[AnsweredQuestion | UnansweredQuestion]`, pydantic asigna
  `AnsweredQuestion` a las preguntas con `sources` y `answer` y
  `UnansweredQuestion` al resto; los campos extra de los datasets
  (`difficulty`, `is_valid`) se ignoran; `"42"` se convierte a `42`.

## Entradas degeneradas

- **FACT** — Query vacía, query sin sentido, `k=0`, ficheros inexistentes y
  JSON malformado no pueden producir un traceback (VI.6).
- **DECISIÓN (2026-09-17, Jose, opción A)** — `k` tiene que ser un entero
  `>= 1` en `search_dataset` (y la misma regla se aplicará a `search` y
  `answer`). Si no: `k must be a positive integer`, exit 1 y no se escribe
  nada. Cubre también el texto que Fire pueda pasar (`--k abc`). Motivo: pedir
  0 fuentes no tiene sentido en un RAG (en `answer` dejaría a Qwen sin
  contexto); un error claro es mejor que adivinar o corregir en silencio.
- **FACT (medido 2026-09-17, moulinette local)** — Un `StudentSearchResults`
  con `retrieved_sources` vacíos es válido (`Student data is valid: True`,
  recall 0) tanto con `"k": 10` como con `"k": 0`: la moulinette no impone
  nada sobre `k`.
- **ABIERTO** — Semántica de la query vacía en `search`. Límite: M3.
- **FACT (medido 2026-09-15)** — Fire traduce pero NO valida: adivina tipos
  (`--k abc` llega como `'abc'`; `search 123` llega como el entero `123`) y
  los type hints no se comprueban al ejecutar. La validación es nuestra.
- **DECISIÓN (2026-09-15, Jose, opción 1)** — Se acepta y documenta el
  comportamiento de Fire medido ese día: (a) con un flag desconocido
  (`search "q" --kk 5`) EJECUTA el comando y después falla con exit 2;
  (b) una palabra sobrante (`search "q" extra_word`) se ignora y sale con
  exit 0. Ninguno da traceback y el enunciado no los menciona; evitarlos
  exigiría validar los argumentos contra la firma antes de llamar a Fire.
  Revisar en M2 si (a) hace que `index` trabaje minutos antes de fallar.
- **FACT (medido 2026-09-15)** — Los errores de uso de Fire son `FireExit`,
  subclase de `SystemExit` (no de `Exception`), y `KeyboardInterrupt` tampoco
  es `Exception`. Sin frontera, una excepción en un comando sale con
  traceback y exit 1, y Ctrl+C con traceback y exit 130.

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
