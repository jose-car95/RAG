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
- **DECISIÓN (2026-10-27, Jose, issue #91)** — El bonus de embeddings
  necesita calcular un vector por chunk, y en CPU eso son ~625 s para los
  18.941 chunks, por encima de los 300 s del indexado. Por eso es opcional,
  con flags propios como `--raw_directory`: `index --embeddings` (apagado
  por defecto) y `--vectors_path` (`data/processed/embeddings.db`). `index`
  sin el flag no cambia.
- **DECISIÓN (2026-11-03, Jose, issue #93)** — `search` gana dos flags
  opcionales: `--retriever` (`bm25` por defecto, o `semantic`) y
  `--vectors_path` (`data/processed/embeddings.db`). Con los valores por
  defecto, `search <query> --k` del enunciado no cambia. Un retriever
  desconocido termina con `ERROR: retriever must be 'bm25' or 'semantic'`.
  `search_dataset` y la API siguen solo con BM25 (slices aparte).
- **NOTA, mejora pendiente (2026-11-03, issue #93)** — Los ~8 min del
  cálculo de embeddings se pueden recortar, pero se decide DESPUÉS de medir
  el recall semántico (no se optimiza algo que quizá no sirva). Candidatos a
  analizar entonces: cuantización int8 (`torch.quantize_dynamic`, ~1,5-2x,
  sin dependencia nueva, a costa de precisión), bajar `MAX_TOKENS`, ONNX
  Runtime (dependencia pesada). Ya aplicadas y gratis: dedup por huella y
  ordenar por longitud. El coste se paga una sola vez (segunda pasada 0,8 s).
- **DECISIÓN (2026-11-03, Jose, issue #93)** — Los vectores se guardan en
  SQLite (`embeddings.db`), no en un `.pt`/`.npy` ni en FAISS: la clave por
  huella da el dedup incremental casi gratis y es coherente con `index.db`.
  El formato no afecta al tiempo de cálculo (se va en el modelo, no en
  guardar). A escala de millones sí convendría una base vectorial (FAISS);
  para 18.941 vectores un producto escalar de numpy sobra.
- **DECISIÓN (2026-11-04, Jose, issue #95)** — `search --retriever` gana el
  valor `hybrid`, que fusiona BM25 y el semántico con **Reciprocal Rank
  Fusion** (RRF). Se elige RRF frente a la suma ponderada de puntuaciones
  (opción A frente a B): RRF fusiona por el puesto, así que no hay que
  normalizar las dos escalas (BM25 de 0 a +∞, coseno de −1 a 1) y usa una sola
  constante `c=60`, valor de la literatura (Cormack 2009) que no se ajusta,
  igual que `k1`/`b`. La suma ponderada exigiría un `alpha` que solo se fija
  mirando las respuestas conocidas, lo que prohíbe el contrato. `FUSION_DEPTH`
  = 100 candidatos por buscador, elegido por principio (10× el mayor `k` que
  reportamos, suficiente para que el top-k sea estable), nunca maximizando el
  recall. `search_dataset` y la API siguen BM25-only (slices aparte).
- **NOTA, resultado (2026-11-04, issue #95)** — La híbrida 50/50 NO supera a
  BM25 en los públicos (R@5 docs 0,780 vs 0,830; code 0,626 vs 0,636): la
  fusión a peso igual deja que el semántico (débil en este corpus) arrastre a
  BM25. Se deja como feature implementada y experimento negativo, como el
  semántico del #93. Un retriever desconocido termina con `ERROR: retriever
  must be 'bm25', 'semantic' or 'hybrid'`.
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
- **EXPERIMENTO DESCARTADO (2026-10-13, Jose, slice #43)** — Se probó
  cortar las clases de primer nivel que no caben en el inicio de cada método
  directo (decorador incluido) y empaquetar métodos seguidos mientras cupieran
  (opción A; la B, un chunk por método, se descartó antes por los 34% de
  métodos de menos de 300 caracteres). Motivo: 9 de los 12 fallos de code
  «fichero correcto, zona equivocada» de la línea base M3 están dentro de
  clases de más de 2000. **Resultado medido** con los dos índices construidos
  en la misma sesión: docs sin cambios; code Recall@1 0,263 → 0,283, Recall@5
  **0,485 → 0,465** y Recall@10 0,576 → 0,556 (18.942 → 19.169 chunks).
  Cambian 14 preguntas de code: 5 suben y 9 bajan, y en el top 5 se pierden
  2 sin ganar ninguna. El efecto es mixto y el saldo en la métrica del umbral
  es negativo, así que **se revierte**; el código queda en la rama local
  `experiment/43-method-chunks` como referencia. No se prueban variantes para
  no ajustar contra los datasets públicos.
- **FACT (medido 2026-10-13, por curiosidad, fuera de `src/`)** — Con los
  mismos 18.942 chunks de nuestro índice copiados a una tabla FTS5 temporal,
  la misma pregunta tokenizada con nuestro `tokenize` (términos unidos por
  `OR`) y top 10 por `bm25()` de SQLite: con identificadores enteros (como
  nosotros, `tokenchars '_'`) code Recall@5 = 0,535 y docs 0,830; con el
  tokenizador por defecto, que parte los identificadores por `_`, code
  Recall@5 = **0,596** y docs 0,830 (nuestra línea base: 0,485 y 0,840). Dos
  efectos: partir identificadores (+6 preguntas con el mismo ranking, apoya
  el #44) y la variante de BM25 de FTS5 (`k1` 1,2 e IDF clásica de Robertson
  sin el `1 +`, +5 preguntas con los mismos tokens). `bm25()` devuelve la
  puntuación en negativo y se ordena de menor a mayor. **No se adopta nada
  por estos números**: FTS5 no cuenta como implementar BM25 (VI.1 y contrato)
  y elegir parámetros porque puntúan mejor en los públicos sería ajustar
  contra ellos. Cada cambio irá en su slice con un motivo previo.
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

## ¿Hace falta orientación a objetos?

- **FACT (verificado 2026-10-06 sobre `docs/en.subject.pdf`, 26 páginas)** —
  **No.** Se buscaron todas las frases con «must» y «mandatory» y todas las
  menciones de `class`, `object-oriented`, `OOP`, `inherit`, `polymorph` y
  `encapsulat`. Ningún requisito duro menciona clases ni orientación a
  objetos: los 23 «must» hablan de Python 3.10+, flake8, mypy, type hints,
  context managers, `uv`, Fire, tqdm, rutas configurables, la estructura de
  carpetas, los umbrales y el README.
- **FACT (verificado 2026-10-06)** — Las dos únicas menciones de clases son
  permisivas, no prescriptivas: *«Include docstrings in functions **and
  classes** following PEP 257»* (condicional: documenta las que tengas) y
  *«Your data models must use pydantic... **Service or orchestration classes
  (indexer, retriever, pipeline, etc.) do not have to be pydantic**»* (una
  exención para las clases de servicio, no una obligación de tenerlas).
- **FACT (verificado 2026-10-06)** — La escala de evaluación interna de
  `docs/eval/` no menciona objetos en absoluto.
- **INTERPRETACIÓN** — El proyecto ya tiene clases donde el enunciado las
  exige o donde se ganan el sueldo: los 8 modelos pydantic, `Bm25Index` (un
  `NamedTuple`) y `RagCli`. Lo que no hay son clases de servicio con estado
  mutable: el dominio son funciones puras sobre datos inmutables, más fáciles
  de testear y de razonar. Una clase se crea cuando haya estado compartido que
  lo justifique, y la discusión del slice #25 (`load_index` + `search_index`
  frente a una clase `Retriever`) es exactamente ese debate.
- **FACT (leído 2026-10-08 en `exams/scripts/exam_retrieval.sh`, líneas
  81-92, 183-200 y 228)** — `data/output/search_results/<DatasetScope>/`: el
  `<DatasetScope>` lo elige el evaluador. El script crea su propia carpeta
  (`evaluations/retrieval/<fecha>/search_results`), nos la pasa con
  `--save_directory` y después busca el fichero por nombre
  (`find ... -name "*docs*"`). Escribir `<save_directory>/<nombre del
  dataset>.json` sin añadir niveles es lo correcto; añadirlo nosotros lo
  duplicaría. Lo fija `tests/test_search_dataset.py`. Cierra el ABIERTO.
- **FACT (mismo script)** — El examen cronometra con `date +%s` alrededor de
  `uv run python -m src ...` (tiempo de pared, arranque incluido) y usa
  `--k 10` tanto para buscar como para evaluar.

## El comando `search`

- **DECISIÓN (2026-10-06, Jose, opción B1)** — Cada línea imprime posición,
  puntuación con dos decimales, `file_path` tal como está en el corpus y el
  rango de caracteres entre corchetes. Sin fragmento del texto: añadiría ruido
  y decisiones nuevas, y lo que compara el corrector es la ruta y el rango.
- **DECISIÓN (2026-10-06, Jose, opción C1)** — Capas separadas: `load_chunks`
  (adaptador) lee SQLite, `run_search` (aplicación) valida y coordina, la CLI
  solo imprime. `search_dataset` reutilizará el mismo caso de uso.
- **FACT (medido 2026-10-06)** — `sqlite3.connect` **crea** el fichero que no
  encuentra: sin comprobarlo antes, un `search` sin índice dejaría un
  `index.db` de 0 bytes y fallaría con `no such table: chunks`. La guarda con
  `is_file()` va antes de conectar.
- **FACT (medido 2026-10-06)** — Devolver el cursor de SQLite en vez de
  `list(...)` falla con `ProgrammingError: Cannot operate on a closed
  database`, porque el cursor es perezoso y la conexión ya se cerró.
- **INTERPRETACIÓN** — La ruta del índice la valida el adaptador y no el caso
  de uso: `k` y la query son reglas del problema, pero que el índice exista es
  un hecho del mundo exterior y la aplicación no toca disco.
- **FACT (medido 2026-10-06)** — Un `search` suelto tarda 1,12 s sobre el
  corpus real (1,10-1,15 s en tres consultas), y el 90% de ese tiempo es
  construir el índice invertido en memoria, no buscar.

## Recuperación con BM25

- **DECISIÓN (2026-10-01, Jose)** — Se usa **BM25**, no TF-IDF, con los valores
  habituales `k1=1.5` y `b=0.75`, que **no se ajustan** contra los datasets de
  referencia.
- **FACT (medido 2026-10-01)** — En los dos chunks reales de la pregunta
  pública sobre cargar un adaptador LoRA, la ventaja del chunk correcto sobre
  el señuelo pasa de ×1,78 con TF-IDF a ×4,79 con BM25. TF-IDF no normaliza
  por longitud, y nuestros chunks van de 0 a 404 tokens.
- **FACT (medido 2026-10-01)** — Con `k1=0, b=0` esa ventaja subiría a ×8,63
  **en esa única pregunta**. Es el ejemplo de por qué no se calibra contra
  respuestas conocidas.
- **DECISIÓN (2026-10-01, Jose, opción A)** — El índice invertido se
  construye **en memoria** al arrancar el proceso, no se persiste en SQLite.
  Medido: 0,88-1,22 s construirlo y 1,75 s las 199 preguntas, unos 3 s de los
  90 permitidos. Persistirlo añadiría 957.148 filas y dos tablas.
- **FACT (medido 2026-10-01)** — La unión de las listas de apariciones de una
  pregunta **no es un filtro fuerte**: mediana de 13.731 candidatos de 18.942
  (72% del corpus), mínimo 5.014 y máximo 17.014. El índice invertido se gana
  su sitio porque da `df` ya contado y evita retokenizar el corpus en cada
  consulta.
- **INTERPRETACIÓN** — La consulta se recorre sin términos repetidos: se usa
  la variante simple de BM25, sin ponderar la frecuencia del término *en la
  consulta*. Los empates se rompen por `chunk_id` ascendente, para que el
  orden no dependa del recorrido del diccionario.
- **INTERPRETACIÓN** — Un término ausente del corpus tiene `df` 0 y un IDF
  alto e inofensivo, porque ningún chunk lo suma. Se resuelve con
  `postings.get(term, {})`, sin lanzar.

## Tokenización

- **DECISIÓN (2026-09-29, Jose, opción A)** — Un token es `[a-z0-9_]+` sobre
  el texto en minúsculas. Dígitos y guion bajo se quedan **dentro** del token.
- **FACT (medido 2026-09-29)** — `\w+` solo añadiría 40 palabras de las 55.397
  del vocabulario (0,07%), todas CJK o acentuadas y procedentes de ficheros de
  prueba de vLLM. La única pregunta de referencia con caracteres no ASCII usa
  emojis, que ambos patrones descartan.
- **FACT (medido 2026-09-29)** — 79 de las 199 preguntas de referencia
  contienen identificadores con guion bajo (`lm_eval`, `mm_kwargs`,
  `_call_hf_processor`, `qk_max`, `cutlass_scaled_mm`). Partirlos destruiría
  el término de mayor IDF de esas preguntas.
- **INTERPRETACIÓN** — No se quitan stop words: IDF ya las reduce a casi cero.
  Partir `snake_case` y hacer stemming quedan como experimentos medibles de M4,
  con recall antes y después.
- **DECISIÓN (2026-10-13, Jose, opción B, slice #44)** — Cada token con
  guion bajo se emite **entero y seguido de sus partes** (`lm_eval` →
  `lm_eval`, `lm`, `eval`); las partes vacías se descartan (`__init__` →
  `__init__`, `init`). Motivo, decidido antes de medir: el enunciado (VI.1)
  dice que una pregunta puede citar un identificador o parafrasearlo y que lo
  que se guarda al indexar decide cuál de los dos se puede encontrar; con las
  dos formas no se pierde el identificador entero (el término más raro de 79
  preguntas, ver arriba). Descartada la opción A (solo partes), aunque fuera
  la variante medida con FTS5. `CamelCase` queda fuera: la prueba de FTS5 no
  lo partía y exige tratar siglas; si hace falta, irá en su propio slice.
- **FACT (medido 2026-10-13, slice #44)** — Con la opción B, medido contra un
  índice de `main` en la misma sesión (`--k 10`): code Recall@5 0,535 →
  **0,636** (R@1 0,303 → 0,354, R@10 0,576 → 0,697; entran 13 en el top 5 y
  salen 3); docs Recall@5 se queda en **0,830** (entra 1 y sale 1), pero R@1
  baja de 0,650 a 0,610 y R@10 de 0,880 a 0,860. El índice pasa de 1.827.646 a
  2.803.792 tokens (media 148 por chunk) y el vocabulario de 55.397 a 56.938.
  Se queda: se decidió antes de medir y no empeora la métrica del umbral.
- **FACT (medido 2026-09-29)** — El corpus indexado da 1.827.646 tokens y un
  vocabulario de 55.397 palabras; las 199 preguntas dan 2.714 tokens, con una
  media de 13,6 por pregunta y ninguna vacía.

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
- **DECISIÓN (2026-10-06, Jose, opción A1)** — Una query vacía o con solo
  espacios es un **error**: `ERROR: query must not be empty`, salida 1. Se
  distingue de una búsqueda legítima sin resultados (`search "asdfghjkl"`),
  que imprime `No sources found.` y sale con 0. Cierra el ABIERTO que vencía
  en M3.
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
- **FACT (medido 2026-10-06, moulinette local)** — El umbral es
  **estrictamente mayor**: un IoU de exactamente 0,05 (28/560) no cuenta y
  29/560 sí. Una pregunta del dataset que falta en los resultados cuenta como
  0: la media es sobre las preguntas de referencia.
- **FACT (medido 2026-10-06, moulinette local)** — Con dos rangos de ancho 0
  (`[5, 5)` frente a `[5, 5)`) la moulinette se rompe con
  `ZeroDivisionError`. Con una fuente de referencia de ancho 0 frente a un
  resultado normal la acepta (`valid: True`, recall 0). Los datasets
  públicos y nuestro índice tienen 0 rangos de ancho 0.
- **DECISIÓN (2026-10-07, Jose, opción A)** — El rango de ancho 0 se trata
  con una guarda en `iou` (si la unión es 0, devuelve un valor fijo), no
  endureciendo `MinimalSource` a `first < last`. Motivo: el modelo también
  carga los datasets del evaluador, y la moulinette acepta una fuente de
  referencia vacía; un molde más estricto rechazaría el dataset entero por
  una sola fuente. `iou` es el único sitio que divide por una longitud.
- **DECISIÓN (2026-10-13, Jose, slice #48)** — BM25 pasa a la definición
  original de Okapi BM25: `k1 = 1.2`, `b = 0.75` e IDF de Robertson/Spärck
  Jones `log((N - df + 0.5) / (df + 0.5))`, sin el `1 +` de Lucene. Motivo:
  es la definición de referencia y la más fácil de explicar; la versión
  anterior mezclaba la IDF de Lucene con un `k1 = 1.5` sin justificar. Se
  decide por la definición, no por un número; la prueba con FTS5 ya se había
  visto y se dice en el README.
- **DECISIÓN (2026-10-13, Jose, opción C, slice #48)** — Cuando la IDF
  original sale `<= 0` (un término en la mitad o más de los chunks), se usa
  un suelo diminuto positivo (`1e-6`, el mismo que SQLite FTS5) en vez del
  valor negativo (A) o de 0 (B). Medido: en nuestro índice solo `def` (df
  11.369 de 18.942) daría negativo, y ninguna pregunta pública la contiene.
  Con el negativo, un chunk relevante bajaba por contener una palabra de la
  pregunta y una pregunta con solo esa palabra salía al revés; con el suelo
  la palabra casi no cuenta pero sigue desempatando por frecuencia.
- **EXPERIMENTO DESCARTADO (2026-10-14, Jose, opción B, slice #45)** — Se
  probó que la ruta del fichero entrase en el ranking como tokens del chunk
  (`tokenize(file_path)` + `tokenize(text)` al construir el índice; opción A
  de diseño, sin parámetros nuevos, frente a una puntuación aparte con un
  peso que habría que ajustar). Motivo: 25 de 36 fallos de code y 13 de 17 de
  docs compartían alguna palabra con la ruta correcta. **Resultado medido**
  contra un índice de `main`: code R@5 0,636 → 0,727 (entran 9 en el top 5,
  no sale ninguna; MRR 0,480 → 0,568), pero docs R@5 **0,830 → 0,820** (entran
  2 y salen 3; MRR 0,704 → 0,725). Salen preguntas genéricas cuya respuesta
  está en ficheros de nombre genérico (`v1_guide.md`, `SECURITY.md`,
  `quickstart.md`): la ruta empuja a todos los chunks de un fichero. Se
  descarta por el criterio de M4 (un cambio no puede empeorar la métrica del
  umbral en ningún dataset) y porque reduce el margen más débil, el de docs,
  de 3 a 2 preguntas. Aplicarlo solo a `.py` se descartó por ser una variante
  elegida tras ver los números. El código queda en la rama local
  `experiment/45-path-tokens`.
- **DECISIÓN** — Los datasets privados (`docs/eval/datasets_private.zip`) y
  la moulinette no se usan jamás desde el código, ni para medir ni para
  ajustar. Los datasets públicos sirven para medir; los parámetros (p. ej.
  `k1` y `b` de BM25, tamaño de chunk) se eligen con un motivo explicable, no
  por búsqueda ciega contra los públicos, y el motivo queda en el README.

## Generación (M5)

- **FACT (medido 2026-10-14)** — Ventana de contexto de Qwen3-0.6B: la ficha
  oficial (`README.md` en Hugging Face) documenta **32.768 tokens**; el
  `config.json` descargado permite técnicamente 40.960
  (`max_position_embeddings`). Un chunk largo ocupa unos 385 tokens (`.py`) o
  464 (`.md`), máximo 971; un prompt con 10 fuentes ronda los 5.000. La
  ventana no es el límite: lo es el tiempo de CPU.
- **FACT (medido 2026-10-14, 6 hilos, 60 tokens nuevos)** — Qwen se carga por
  defecto en `bfloat16`, que en CPU es unas 2,7 veces más lento que `float32`:
  1 fuente (544 tokens) 23,7 s frente a 13,4 s; 5 fuentes (2.322 tokens) 85,0
  s frente a 31,1 s; 10 fuentes (5.079 tokens) 205,7 s en `bfloat16`. El
  adaptador del #55 decide el tipo y el presupuesto de tokens, por tiempo y
  nunca por la calidad de las respuestas de los públicos.
- **DECISIÓN (2026-10-14, Jose, opción A, slice #54)** — El prompt se monta
  añadiendo fuentes en el orden de BM25 hasta que la siguiente se pasaría del
  presupuesto; ahí se deja de añadir. Descartadas: B (saltar la que no cabe y
  probar otras más pequeñas, que podría meter una peor y dejar fuera una
  mejor) y C (recortar la última, que deja fragmentos cortados y exige el
  tokenizador dentro del dominio). El prompt pide responder solo con las
  fuentes y decir que no se puede si no contienen la respuesta (idea de
  Jose).
- **DECISIÓN (2026-10-19, Jose, opción A, issue #62)** — El prompt va por
  roles de chat: las reglas en `system`; las fuentes, cada una entre
  `<source id="N" path="...">` y `</source>`, y la pregunta al final, en
  `user`. El presupuesto de 2.000 tokens cuenta las dos partes juntas. El
  corpus tiene 0 ficheros con `</source>`, así que ninguna fuente puede
  cerrar su etiqueta por accidente. Motivo: más limpio y la información le
  llega mejor al modelo, no subir una nota.

## Entorno

- **DECISIÓN (2026-10-14, Jose, slice #53)** — Todas las descargas quedan
  dentro del repo: `[tool.uv] cache-dir = ".cache/uv"` en `pyproject.toml` y
  los pesos del modelo en `.cache/huggingface/`. Motivo: en la escuela el
  home tiene 5 GB casi llenos y el repo se clona en `sgoinfree` (~30 GB, se
  limpia cada ~15 días). `.cache/` está en `.gitignore` y fuera de `flake8`.
  Los comandos se ejecutan desde la raíz del repo (la ruta es relativa).
- **FACT (medido 2026-10-14, uv 0.11.2)** — `cache-dir` se acepta en
  `[tool.uv]`; `python-install-dir` **no** (ni en `pyproject.toml` ni en
  `uv.toml`): el intérprete solo se redirige con `UV_PYTHON_INSTALL_DIR`.
- **FACT (medido 2026-10-14)** — `torch 2.14.1+cpu` desde el índice de CPU
  (wheel de 187 MB, 693 MB instalado, 0 paquetes NVIDIA/CUDA en el lock) y
  `transformers 5.19.0`. Qwen3-0.6B ocupa 1.449 MB (1.434 de
  `model.safetensors`). `cache_dir` en `from_pretrained` redirige los pesos,
  pero `huggingface_hub` escribe ficheros auxiliares pequeños en `HF_HOME`
  (por defecto `~/.cache/huggingface`): `.agent_harnesses.json` y logs de
  `xet`. **Resuelto en el #55 (2026-10-15):** `load_generator` hace
  `os.environ.setdefault("HF_HOME", cache_dir)` antes de importar
  transformers; medido: 0 ficheros nuevos en `~/.cache/huggingface` tras un
  `answer` real.

- **DECISIÓN** — Solo CPU. `torch` se instalará desde el índice de wheels de
  CPU y la inferencia usa `device="cpu"` (Jose, 2026-09-13: las máquinas de la
  escuela no tienen GPU).
- **DECISIÓN** — flake8 y mypy excluyen `data/` y `docs/`: el corpus de vLLM
  contiene ficheros `.py` que no son nuestros y el corrector ejecuta
  `make lint` con el corpus descomprimido. No es silenciar el linter: todo
  nuestro código se sigue revisando.

- **FACT (medido 2026-11-04, Fase 3 de limpieza)** — 4 ficheros del corpus
  tienen saltos de línea CRLF (`\r\n`): `vllm/model_executor/layers/`
  `quantization/utils/__init__.py`, `tests/quantization/test_cpu_offload.py`,
  `tests/test_embedded_commit.py` y `tests/test_seed_behavior.py`.
  `Path.read_text(encoding="utf-8")` traduce `\r\n` a `\n` (modo texto
  universal de Python), así que los offsets de carácter que indexamos cuentan
  un carácter por salto de línea, no dos. La moulinette compara con el mismo
  `read_text`, así que coinciden; el riesgo sería si el corrector leyera los
  bytes en crudo (`\r\n` = 2), pero no lo hace. Se deja documentado; no se
  normaliza nada (no tocar el corpus, que es intocable).
