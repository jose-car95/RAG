# PROGRESS

Leer al empezar cada sesión (ver `CLAUDE.md`, "Al empezar cada sesión").

## Estado actual

- **Milestone:** M3 — Recuperación BM25 y línea base (en curso). M0 cerrado
  el 2026-09-16; M1 el 2026-09-18; **M2 el 2026-09-29**.
- **M2 cerrado (5 slices):** #17 descubrir los 1.969 ficheros indexables;
  #18 chunking de Markdown y texto en cascada; #19 chunking de Python con
  `ast`; #20 índice en SQLite; #21 validación de `max_chunk_size`. Fuera de
  milestone: #35 página de conceptos de BM25.
- **Slices cerrados en M3:** #22 tokenización.
- **Slice en revisión:** #23 "Rank chunks with BM25". Nace
  `src/domain/bm25.py` con tres piezas: `Bm25Index` (un `NamedTuple` con
  `postings`, `lengths`, `average_length` y `document_count`), `build_index`
  (recorre el corpus una sola vez, porque puede llegar como generador) e
  `idf` y `rank` (la fórmula con `K1=1.5` y `B=0.75`, orden descendente y
  desempate por `chunk_id` ascendente). El índice invertido vive en memoria,
  no en SQLite.
- **Verificado (2026-10-01, slice #23):**
  - `make lint` → flake8 sin salida; mypy `Success: no issues found in 26 source files`.
  - `make test` → `131 passed` (18 de BM25).
  - **Primera búsqueda real del proyecto.** Pregunta de `dataset_docs_public.json` («What HTTP endpoint is used to dynamically load a LoRA adapter in vLLM?»): el chunk correcto sale **en posición 1** con 41,27 puntos e **IoU 0,9986** contra la fuente de referencia; los puestos 3 y 5 son sus chunks vecinos del mismo fichero. Índice construido en 0,88 s y búsqueda en **22 ms**, así que 200 preguntas serían unos 5 s de los 90 permitidos.
  - **Reparto de la puntuación del chunk ganador:** `adapter` 11,23 (df 79, tf 13), `lora` 6,67, `endpoint` 5,35, `http` 4,30, `dynamically` 4,11 (el término más raro, pero con tf 1), `a` 2,77 (tf 12 y df 4.818). Prueba medida de que hacen falta las dos cosas, y de por qué no se mantiene una lista de stop words.
- **Verificado (2026-09-29, slice #22):**
  - `make test` → `113 passed` (10 de tokenización).
  - **Sobre datos reales:** las 199 preguntas de referencia dan 2.714 tokens (media 13,6 por pregunta, mínimo 6, máximo 35, ninguna con 0 tokens); los 18.942 chunks dan 1.827.646 tokens y un vocabulario de 55.397 palabras. Los identificadores `lm_eval`, `mm_kwargs`, `qk_max`, `int8` y `fp8_min` sobreviven enteros.
  - **Coincide con la página de conceptos:** los mismos 55.397 y 1.827.646 que se midieron antes de existir el tokenizador.
- **Verificado (2026-09-29, slice #21):**
  - `make test` → `103 passed` (10 de indexado).
  - **Los seis valores inválidos por la CLI** (`0`, `-5`, `abc`, `2.5`, `2001`, `True`) dan `ERROR: max_chunk_size must be an integer between 1 and 2000` y salida `1`; `500` indexa con salida `0`. Un índice ya guardado sobrevive intacto a una llamada rechazada (mismas filas y mismos bytes).
  - **Antes de este slice** (medido el 2026-09-24): `0` daba `ERROR: range() arg 3 must not be zero` (jerga interna) y `-5` decía `Ingestion complete!` con salida `0` y **cero chunks**, borrando el índice bueno. Causa: `max_chunk_size` es el paso de `range` en `src/domain/chunking.py:30`.
  - **Recode probado:** poniendo `MAX_CHUNK_SIZE = 1000`, el mensaje pasa solo a `between 1 and 1000` y `--max_chunk_size 1500` se rechaza, sin tocar nada más.
- **Verificado (2026-09-23, slice #20):**
  - `make test` → `93 passed` (7 de indexado).
  - `uv run python -m src index` → `Ingestion complete! Indices saved under data/processed/`, salida `0`; `--raw_directory /nonexistent` → `ERROR: corpus folder not found: /nonexistent`, salida `1`; `--index_path /proc/nope/index.db` → `ERROR: cannot write index: /proc/nope/index.db`, salida `1`.
  - **Corpus real:** 1.969 ficheros → 18.942 chunks de 1.847 ficheros distintos en **3,65 s** (límite 300 s), 81 MB de memoria máxima, índice de 25 MB con 0 páginas libres. Comprobado en la base de datos: 0 filas con `file_path` fuera de `data/raw/vllm-0.10.1/`, 0 filas donde `len(text) != last - first` y 0 chunks por encima de 2000 (el más ancho mide 2000).
  - **Reconstrucción sin marca de agua:** indexar con `--max_chunk_size 50` deja el fichero en 55.009.280 bytes y volver a 2000 lo devuelve a 26.075.136 bytes, estable en la siguiente ejecución. Antes del `unlink` se quedaba en el tamaño mayor para siempre.
- **Siguiente paso propuesto:** slice #24 "Implement the search command",
  el primero que hace visible BM25 por terminal. Después #25
  (`retrieved_sources` reales), #26 (`evaluate` con recall@k) y #27 (línea
  base). Con esos cuatro, M3 cierra y el RAG ya recupera y se mide.

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
| 2026-09-18 | M1 cerrado en GitHub; issues de M2 (#17-#21) y M3 (#22-#27) creados | Solo se crean issues del milestone actual y del siguiente |
| 2026-09-18 | Se indexan `.py`, `.md` y `.txt` (1A); flags opcionales `--raw_directory` e `--index_path` con valores por defecto (3A); `last_character_index` exclusivo (FACT medido) | Detalle en `docs/SPEC_NOTES.md` |
| 2026-10-01 | BM25 y no TF-IDF | Medido en los dos chunks reales: la ventaja del correcto pasa de ×1,78 (TF-IDF) a ×4,79 (BM25). El motivo decisivo no es ese ejemplo, es que TF-IDF no normaliza por longitud y nuestros chunks van de 0 a 404 tokens |
| 2026-10-01 | El índice invertido vive en memoria, no en SQLite (opción A) | Medido: construirlo cuesta 0,88-1,22 s por proceso y las 199 preguntas 1,75 s, o sea ~3 s de los 90 permitidos. Persistirlo añadiría 957.148 filas y dos tablas a una base de datos que queremos de una sola tabla. Para el bonus de la API HTTP, un proceso largo lo construye una vez al arrancar, así que en memoria es lo natural. Primer candidato de optimización si M4 aprieta |
| 2026-10-01 | `idf` es una función aparte, no una expresión dentro de `rank` | Es lo que un evaluador pedirá explicar o cambiar en el recode; con función propia y test propio, «cámbiame la variante de IDF» toca un solo sitio |
| 2026-10-01 | La consulta se recorre sin repetidos (`set`) y el empate se rompe por `chunk_id` ascendente | Existe una variante de BM25 que pondera cuántas veces aparece un término **en la consulta**; usamos la versión simple, que suma una vez por término distinto. Sin desempate explícito, el orden de dos chunks empatados dependería del recorrido del diccionario y los resultados cambiarían entre ejecuciones |
| 2026-10-01 | `K1=1.5` y `B=0.75`, y no se tocan | Son los valores empíricos de la literatura (Lucene y Elasticsearch traen 1.2 y 0.75). Medido: con `k1=0, b=0` la ventaja del chunk correcto sube a ×8,63 en **una** pregunta, que es exactamente la trampa de ajustar contra respuestas conocidas. El comentario junto a las constantes lo deja escrito |
| 2026-09-29 | Un token es `[a-z0-9_]+` sobre el texto en minúsculas (opción A), no `\w+` | Medido: `\w+` solo añade 40 palabras de 55.397 (0,07%), todas CJK o acentuadas y de ficheros de prueba de vLLM; la única pregunta no ASCII usa emojis, que los dos patrones descartan. El guion bajo y los dígitos se quedan dentro del token porque 79 de las 199 preguntas preguntan por identificadores (`lm_eval`, `mm_kwargs`, `qk_max`) y `int8`/`fp8` son nombres de técnicas. Coste conocido: `israéliennes` se parte en dos |
| 2026-09-29 | No se quitan stop words ni se hace stemming | IDF ya reduce a casi cero las palabras comunes; una lista de palabras prohibidas es una cosa más que mantener y justificar. El stemming es experimento medible de M4 |
| 2026-09-29 | Corrección: compilar el patrón fuera de la función NO es una mejora de rendimiento relevante | Medido: 1,243 s frente a 1,323 s en 200.000 llamadas (×1,06), porque el módulo `re` ya cachea los patrones compilados. El motivo real de la constante es la intención (un único sitio que define qué es una palabra). No rompe la regla del estado global mutable porque un patrón compilado es inmutable (`readonly attribute`) y `findall` devuelve una lista nueva en cada llamada |
| 2026-09-25 | `max_chunk_size` se valida en `run_index`, no en la CLI (opción A) | La regla 1..2000 es del enunciado, no de la terminal: así vale para cualquier adaptador de entrada (la API HTTP del bonus entraría por el mismo caso de uso). En la CLI solo irían las reglas propias del terminal, como rechazar un `--save_directory` que parezca un fichero |
| 2026-09-25 | Se rechaza el `bool` explícitamente, aquí y en la validación de `k` (opción B1) | `bool` hereda de `int` en Python, así que `isinstance(True, int)` es `True` y `--max_chunk_size True` colaba como 1 (20 M de chunks de un carácter). Se arregla la causa en los dos sitios, no el síntoma en uno |
| 2026-09-25 | Constante `MAX_CHUNK_SIZE` en `src/application/index_corpus.py`, leída por la guarda, por el mensaje (f-string) y por el valor por defecto de la CLI | El 2000 estaba en tres sitios. No añade dependencias: la CLI ya importaba de ese módulo. Probado: cambiarla a 1000 actualiza mensaje y límite sin tocar nada más |
| 2026-09-25 | No se extrae un ayudante de validación compartido | Solo hay dos sitios, con límites y mensajes distintos (ponytail peldaño 2). El disparador para extraerlo será el tercero, `search --k` en M3 |
| 2026-09-23 | El índice es una sola tabla plana `chunks` (opción 1A) y guarda el texto del chunk (opción 2A) | Una tabla se explica en una frase y una sola consulta devuelve todo lo que `search` necesita; el texto ocupa 25 MB y evita reabrir 1.847 ficheros por búsqueda |
| 2026-09-23 | `save_chunks` reconstruye el índice borrando el fichero (`unlink(missing_ok=True)`) en vez de vaciar la tabla con `DELETE FROM` (opción A) | SQLite marca las páginas borradas como libres pero nunca las devuelve al sistema: con `DELETE` el fichero heredaba su tamaño máximo (medido: 55 MB tras un `--max_chunk_size 50`, sin bajar nunca). Trade-off aceptado: si el indexado falla, no queda índice viejo; reconstruirlo cuesta 3,65 s |
| 2026-09-23 | `CREATE TABLE` sin `IF NOT EXISTS` | Con el fichero recién borrado la tabla no puede existir, así que la cláusula no protegía de nada (ponytail). Efecto medido: si alguien quita el `unlink`, dos tests se ponen rojos en vez de duplicar filas en silencio |
| 2026-09-23 | `CHUNKERS` solo lista las extensiones con estrategia propia (`.py`); el resto cae en `chunk_text` con `.get(suffix, chunk_text)`. `Chunker` es un alias `Callable`, no un puerto | El patrón Strategy con funciones basta: añadir una estrategia es una línea en el mapa. Un puerto exigiría dos implementaciones reales o un doble de test, y no hay ninguno |
| 2026-09-23 | `load_dataset` recibe `Path` en vez de `str`; la conversión ocurre en la CLI | La frontera traduce lo que llega del exterior (cadenas) al tipo del dominio una sola vez |
| 2026-09-22 | Python se trocea con `ast` por definiciones de primer nivel (opción A) y reutiliza la cascada de texto; si el fichero no parsea, se trocea como texto | Medido: 0 errores de sintaxis en 1.763 ficheros, pero el 23,7% de las definiciones pasa de 2000, así que el último recurso es inevitable. Bajar a métodos (opción B) es experimento de M4 |
| 2026-09-22 | El cuerpo común de las dos estrategias vive en `_chunk_with_cuts`; la maquinaria interna del módulo lleva `_` delante y la API pública son `chunk_text` y `chunk_python` | Reutilizar en vez de duplicar (ponytail peldaño 2) y dejar claro qué se puede llamar desde fuera; los 71 tests previos probaron que el refactor no cambió el comportamiento |
| 2026-09-21 | Chunking de Markdown/texto en cascada (títulos → párrafos → corte a lo bruto), con `pack` voraz que solo mira el último chunk | Opción B del slice #18; medido en el corpus: 1.759 chunks, 0 violaciones, mediana 399 |
| 2026-09-21 | Los `#` dentro de bloques de código cuentan como título (limitación conocida, comentario `ponytail:`) | Solo añade un corte extra y no rompe el invariante; detectar bloques de código sería más lógica para un caso raro |
| 2026-09-18 | Provisional: `RagCli.index` llama directamente al adaptador `find_corpus_files` | El caso de uso de indexado nacerá en el slice #20, cuando coordine descubrir, trocear y guardar; hoy solo reenviaría la llamada |
| 2026-09-18 | Corrección: los datasets públicos tienen 199 fuentes, no 398 | Error de conteo del 2026-09-13; corregido en `docs/SPEC_NOTES.md` |
| 2026-09-17 | Se mantiene `.flake8` en vez de pasar las exclusiones al `Makefile` | El enunciado da el comando literal `flake8 .`; el fichero aplica a quien ejecute flake8 (corrector, VS Code, CI). Sin él: 49.694 errores ajenos (40.788 de `.venv`, 8.906 de `data/`) |
| 2026-09-17 | Se desarrolla con Python 3.12 (`.python-version`); en la escuela (Python 3.10) `uv sync` descargará 3.12 automáticamente | Misma versión en casa, CI y escuela. Plan B si la descarga falla: `.python-version` = `3.10` (el código pasa `mypy --python-version 3.10`) |
| 2026-09-15 | La CLI vive en `src/adapters/` (carpeta plana, opción B); desaparece `src/interface/` | En hexagonal la CLI es un adaptador de entrada; `interface` chocaba con "interfaz" = puerto. Se descartó separar `inbound/`/`outbound/` (opción C) por simplicidad |

## Métricas

Gates de métrica locales (necesitan corpus y modelo). La línea base se mide en
M3 antes de optimizar nada.

| Fecha | Métrica | Valor | Umbral | Comando que lo reproduce |
|---|---|---|---|---|
| 2026-09-23 | Tiempo de indexado | **3,65 s** (1.969 ficheros, 18.942 chunks) | ≤ 300 s | `uv run python -m src index` |
| 2026-09-23 | Tamaño del índice | 25 MB (26.075.136 bytes), 0 páginas libres | — | `uv run python -m src index` + `ls -l data/processed/index.db` |
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
- **Ensayar en el primer `/ensayo` (paso 8 del slice #17, 2026-09-18):** el
  motivo principal para no usar rutas absolutas es que la moulinette compara
  `file_path` letra a letra con `data/raw/vllm-0.10.1/...` y nunca
  coincidirían (recall 0 aunque la búsqueda fuera perfecta); Jose dio como
  motivo que cambian entre máquinas, que es secundario.
- **Repasar (paso 8 del slice #20, respondido el 2026-09-24):** 2 de 3.
  Bien la garantía del `unlink` y los tres sitios que toca una estrategia
  nueva (`INDEXABLE_SUFFIXES`, la función nueva y una línea en `CHUNKERS`).
  **Falló** el segundo gestor de contexto: Jose dijo que muestra un mensaje
  de si todo fue bien; en realidad gestiona la **transacción** (commit al
  salir bien, rollback si hay excepción) y **no cierra** la conexión, que es
  para lo que hace falta `closing`. Medido: sin el segundo `connection` el
  índice queda con 0 filas sin dar ningún error; sin `closing` queda 1
  fichero abierto. Falta también decir en una frase por qué `DELETE FROM`
  dejaba el fichero grande (páginas libres que SQLite no devuelve al
  sistema).
- **Paso 8 del slice #21 (2026-09-25): 3 de 3.** El orden de las
  comprobaciones (el tipo antes de las comparaciones, por el cortocircuito
  del `or`), por qué `bool` necesita su propia comprobación, y por qué la
  guarda vive en el caso de uso y no en la CLI.
- **Paso 8 del slice #22 (2026-09-29): 2 de 3 y media.** Bien por qué la
  misma función tokeniza la pregunta y el corpus, y por qué devuelve una
  lista (BM25 cuenta repeticiones). A medias la tercera: dio el beneficio de
  mantenimiento, pero faltaba que la regla prohíbe el estado **mutable** y
  que un patrón compilado es inmutable (`readonly attribute`), además de que
  `findall` devuelve una lista nueva cada vez. Repasar también que el ahorro
  por compilar fuera es solo del 6%.
- **Paso 8 del slice #23 (2026-10-01): 2 y medio de 3.** Bien el `set` de la
  consulta, el IDF calculado fuera del bucle interior, y qué término aportó
  más (`adapter`, raro y repetido). **A medias** la del `sorted`: confundió
  cuál es `pair[0]` (el id) y cuál `pair[1]` (la puntuación), y faltaban las
  dos consecuencias: sin el signo menos salen los peores primero, y sin el
  desempate explícito el orden depende del recorrido del diccionario.
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
