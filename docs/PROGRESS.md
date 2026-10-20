# PROGRESS

Leer al empezar cada sesión (ver `CLAUDE.md`, "Al empezar cada sesión").

## Estado actual

- **Milestone:** M5 — Generación con Qwen3-0.6B en CPU (en curso). M0 cerrado
  el 2026-09-16; M1 el 2026-09-18; M2 el 2026-09-29; M3 el 2026-10-08;
  **M4 el 2026-10-14**.
- **M4 cerrado (5 issues):** #48 BM25 original de Okapi y #44 identificadores
  por partes se quedan; #43 clases por métodos y #45 ruta como tokens se
  descartan; #46 añade el MRR. Final: docs R@5 0,830 (margen 3), code 0,636
  (margen 14).
- **M3 cerrado (7 slices):** #22 tokenización; #23 BM25; #24 `search`; #25
  fuentes reales en `search_dataset`; #26 `evaluate`; #27 línea base (code
  Recall@5 0,485, falla por 0,015).
- **M2 cerrado (5 slices):** #17 descubrir los 1.969 ficheros indexables;
  #18 chunking de Markdown y texto en cascada; #19 chunking de Python con
  `ast`; #20 índice en SQLite; #21 validación de `max_chunk_size`. Fuera de
  milestone: #35 página de conceptos de BM25.
- **Slice en revisión:** #56 "Answer a whole dataset". `answer_from_sources`
  sale de `run_answer` y la comparten `answer` y `answer_dataset`;
  `src/application/answer_dataset.py` (`run_answer_dataset`) lee el fichero de
  `search_dataset`, carga Qwen una vez, responde con las fuentes que ya trae
  (sin buscar otra vez; sin fuentes, el mensaje fijo sin llamar al modelo) y
  escribe `StudentSearchResultsAndAnswer` con el nombre del fichero de
  entrada. `write_search_results` acepta los dos tipos de resultados.
- **Verificado (2026-10-16, slice #56):**
  - `make lint` → `Success: no issues found in 42 source files`; `make test` → `230 passed` (5 de `answer_dataset` y 1 de `answer_from_sources`, con el generador falso; `tests/__init__.py` nuevo para que mypy no vea `test_answer` con dos nombres).
  - Real, las 3 primeras preguntas de `data/output/search_results/UnansweredQuestions/dataset_docs_public.json`: `Answering: 3/3 [00:37, 12.35s/question]` y `Saved student_search_results_and_answer to ...`, salida 0. Estimación: ~21 min por dataset de 100 preguntas.
  - Calidad de esas 3: `/v1/load_lora_adapter` correcto; `lm_eval` correcto pero pobre; `llm.generate` para embeddings es incorrecto (es `llm.embed`).
  - Fichero inexistente → `ERROR: search results not found: /nope.json`, salida 1, 0,21 s sin cargar el modelo; JSON roto → `ERROR: search results are not valid JSON: ...`, salida 1.
- **Slice anterior, #55 (cerrado):** `answer` con Qwen. Adaptador
  `src/adapters/qwen_generator.py` (`QwenGenerator` con `count_tokens` y
  `generate`; `load_generator` con import tardío de torch, `HF_HOME` con
  `setdefault`, `float32` y `.to("cpu")`), `read_source_text` en
  `src/adapters/corpus.py`, caso de uso `src/application/answer.py` (puerto
  `Generator`, presupuesto 2.000, el modelo solo se carga si hay fuentes) y
  `answer --index_path` en la CLI. Primer slice en modo velocidad: el código
  lo dio la IA en el chat y Jose lo copió.
- **Verificado (2026-10-15, slice #55):**
  - `make lint` → `Success: no issues found in 39 source files`; `make test` → `224 passed` (4 del adaptador, 2 de ellos con Qwen real si están los pesos; 4 de `read_source_text`; 8 del caso de uso con un generador falso; 6 de la CLI, 1 con Qwen real).
  - `answer "How do I dynamically load a LoRA adapter in vLLM?" --k 10` → «...use the `/v1/load_lora_adapter` endpoint or configure a LoRAResolver plugin...», **24,3 s** y **4,9 GB de RAM máxima** (a vigilar en las máquinas de la escuela).
  - `answer "" --k 10` y `--k 0` → `ERROR: ...`, salida 1, **0,22 s**; `"asdfghjkl"` → `No sources found, so the question cannot be answered.`, salida 0, 1,7 s sin cargar el modelo; índice inexistente → `ERROR: index not found: ...`.
  - **0 ficheros nuevos** en `~/.cache/huggingface` tras un `answer` real (cierra el ABIERTO del #53).
  - Con `load_generator()` (con paréntesis) en la CLI, `answer ""` pasaría de 0,22 a **6,52 s** y mypy da `arg-type`: medido en una copia aparte.
  - `device_map="cpu"` exige el paquete `accelerate`; se usa `.to("cpu")`. Los tipos de `transformers` fallan en mypy incluso con su propio tipo de retorno (`generate`, `to`), por eso el modelo y el tokenizador son `Any`.
  - Qwen solo, sin RAG: acierta «blue» y «144», pero dice que el Mundial de 2010 lo ganó Estados Unidos y se inventa `vllm.from_pretrained` para cargar LoRA. Con RAG responde «The answer is not provided in the available sources.» a lo del Mundial.
  - **Límite conocido (para «qué mejoraría» del README):** con «What is your name?», la fuente nº 1 (`examples/offline_inference/automatic_prefix_caching.py`) contiene otra pregunta con nuestro mismo formato (`Question: what is the age of John Doe?`) y el modelo respondió sobre John Doe. Mejora posible, a medir: delimitar mejor las fuentes o repetir la pregunta antes de ellas.
- **Slice anterior, #54 (cerrado):** `build_prompt` e `INSTRUCTION` en
  `src/domain/prompt.py`.
- **Verificado (2026-10-14, slice #54):**
  - `make lint` → `Success: no issues found in 35 source files`; `make test` → `203 passed` (8 del prompt, con un contador falso de palabras).
  - Con datos reales (BM25 sobre el índice y el tokenizador de Qwen como contador), para «How do I dynamically load a LoRA adapter in vLLM?»: presupuesto 800 → 2 fuentes, 717 tokens; 2.000 → 5 fuentes, 1.801 tokens; 6.000 → las 10, 3.037 tokens. La 1ª fuente es `tests/entrypoints/openai/test_lora_adapters.py`, con `client.post("load_lora_adapter", ...)`.
  - Ventana documentada de Qwen3-0.6B: 32.768 tokens; `float32` es ~2,7 veces más rápido que `bfloat16` en esta CPU (sin `avx512_bf16`): pendiente para el #55.
- **Verificado (2026-10-14, slice #53):**
  - `uv cache dir` → `.cache/uv`; `uv add torch transformers` en 13,9 s; el lock no tiene paquetes NVIDIA/CUDA; `torch.cuda.is_available()` → `False`.
  - Disco: `.cache/uv` 941 MB, `.venv` 89 MB más (los paquetes se enlazan desde la caché), `.cache/huggingface` 1,5 GB.
  - Prueba de humo en CPU: carga en 50,2 s (incluye la descarga), 21 tokens en 2,4 s. Sin fuentes, Qwen respondió que vLLM «is a large language model»: una alucinación, el motivo de un RAG.
  - `huggingface_hub` escribió 2 ficheros pequeños en `~/.cache/huggingface` (`.agent_harnesses.json`, un log de `xet`); se resuelve en el #55 fijando `HF_HOME`.
  - `make lint` y `make test` en verde.
- **Verificado (2026-10-14, slice #45):**
  - Con el cambio: `uv run pytest` → `196 passed`; `make lint` limpio.
  - Antes (índice de `main` en un `git worktree`) y después, `--k 10`: code R@5 0,636 → 0,727, MRR 0,480 → 0,568 (26 suben, 2 bajan; entran 9 en el top 5); docs R@5 0,830 → **0,820**, MRR 0,704 → 0,725 (11 suben, 9 bajan; entran 2 y salen 3). La moulinette coincide.
  - Tras revertir: índice reconstruido, docs 0,830 / code 0,636, MRR 0,704 / 0,480; `make test` → `195 passed`; `make lint` limpio.
- **Slice anterior, #46 (cerrado):** MRR en `evaluate`.
- **Verificado (2026-10-13, slice #46):**
  - `make lint` → `Success: no issues found in 33 source files`; `make test` → `195 passed`.
  - Sobre los resultados actuales (`--k 10`): **docs MRR 0,704**, **code MRR 0,480**; la línea de recall es idéntica a la de la moulinette (docs 0,830 y code 0,636 en @5).
  - Una primera versión calculaba el MRR dentro del bucle de `k` (4 veces la misma cuenta, y `mrr` sin definir si `RECALL_KS` quedara vacío); se sacó a su propio bucle.
- **Slice anterior, #44 (cerrado):** identificadores enteros y por partes, code R@5 0,535 → 0,636.
- **Verificado (2026-10-13, slice #44):**
  - `make lint` → `Success: no issues found in 33 source files`; `make test` → `188 passed` (13 del tokenizador).
  - Antes (índice de `main` en un `git worktree`) y después, `--k 10`: code R@1 0,303 → 0,354, R@3 0,475 → 0,566, **R@5 0,535 → 0,636**, R@10 0,576 → 0,697; docs R@1 0,650 → 0,610, R@3 0,790 → 0,810, **R@5 0,830 → 0,830**, R@10 0,880 → 0,860. La moulinette coincide.
  - Code: 25 suben y 9 bajan; entran 13 en el top 5 y salen 3. Docs: 7 suben y 15 bajan; entra 1 y sale 1.
  - Indexado 3,8 s; 199 preguntas 8,6 s. El índice pasa de 1.827.646 a 2.803.792 tokens.
- **Slice anterior, #48 (cerrado):** BM25 original de Okapi, code R@5 0,485 → 0,535.
- **Verificado (2026-10-13, slice #48):**
  - `make lint` → `Success: no issues found in 33 source files`; `make test` → `185 passed` (22 de BM25).
  - Antes (índice de `main` en un `git worktree`) y después, `--k 10`: docs R@5 0,840 → **0,830**; code R@1 0,263 → 0,303, R@3 0,424 → 0,475, **R@5 0,485 → 0,535**, R@10 igual (0,576).
  - Code: 19 preguntas suben y 3 bajan; entran 5 en el top 5 y no sale ninguna (todas del tipo «what is the default value of <identificador>»). Docs: 5 suben y 3 bajan; sale 1 del top 5 (de la 3 a la 7).
  - Mismas cifras que la prueba de FTS5 con identificadores enteros: confirma la implementación.
  - Margen de code: 53 de 99 frente a las 50 necesarias (3 preguntas).
- **Experimento anterior, #43 (cerrado):** clases por métodos, descartado
  (code R@5 0,465); el código queda en la rama local
  `experiment/43-method-chunks`.
- **Verificado (2026-10-13, slice #43):**
  - Con el cambio: `tests/test_chunking.py` → `48 passed`; `uv run pytest` → `192 passed`; `make lint` limpio.
  - Medición con dos índices de la misma sesión (uno de `main` en un `git worktree` aparte): docs igual; code R@1 0,263 → 0,283, **R@5 0,485 → 0,465**, R@10 0,576 → 0,556. Moulinette y `evaluate` coinciden.
  - 14 preguntas de code cambian de posición: 5 suben (una de la 5 a la 1) y 9 bajan (`fp8.py` sale del top 10; `cuda_communicator.py` pasa de 5 a 6).
  - Tras revertir: índice reconstruido con 18.942 chunks y otra vez docs 0,840 / code 0,485; `make test` → `181 passed`; `make lint` limpio.
- **Verificado (2026-10-08, slice #27):**
  - `make lint` → mypy `Success: no issues found in 33 source files`; `make test` → `181 passed`.
  - Indexado **4,51 s**; 199 preguntas **5,51 s** (115 MB); Recall@5 docs **0,840** (OK) y code **0,485** (falla por 0,015). Moulinette y `evaluate` coinciden en los cuatro valores de k.
  - Se borraron con OK de Jose las dos carpetas `evaluations/retrieval/2026-10-07_*` que había dejado una ejecución de `exam_retrieval.sh` (que usa los datasets privados); sus logs de recall no se abrieron.
- **Verificado (2026-10-08, slice #26):**
  - `make lint` → flake8 sin salida; mypy `Success: no issues found in 33 source files`.
  - `make test` → `181 passed` (15 de `recall`, 12 de `evaluate`, 2 de la CLI).
  - **Mismas cifras que la moulinette** con `search_dataset --k 10` sobre los públicos: docs `Recall@1: 0.650 Recall@3: 0.790 Recall@5: 0.840 Recall@10: 0.880`; code `Recall@1: 0.263 Recall@3: 0.424 Recall@5: 0.485 Recall@10: 0.576`.
  - **Los once criterios del issue por la CLI real:** fichero de resultados o dataset inexistente, JSON roto en cualquiera de los dos, dataset `UnansweredQuestions` y dataset sin preguntas terminan en `ERROR: ...` con salida 1 y sin traceback.
  - **`recall_at_k` se llama 400 veces** (100 preguntas × 4 valores de k), medido con un contador; una primera versión con un bucle de más hacía 40.000.
  - **Diagnóstico para M4 (code, top 5, 99 preguntas):** 48 encontradas, 12 en el fichero correcto pero en otra zona (IoU ≤ 0,05) y 39 sin el fichero correcto en el top 5. El IoU mediano de los aciertos es 0,49: el umbral no es el cuello de botella, lo es el ranking. Faltan 2 preguntas (50/99) para pasar; hay 9 con la fuente en las posiciones 6-10.
- **Verificado (2026-10-06, slice #25):**
  - `make lint` → flake8 sin salida; mypy `Success: no issues found in 29 source files`.
  - `make test` → `153 passed`.
  - **Las 199 preguntas públicas: 3,79 s (docs) + 4,07 s (code) = 7,86 s** de los 90 permitidos, con 115 MB de memoria. Reconstruir el índice por pregunta habría costado 184 s: medido antes de implementar y es el motivo del refactor.
  - **PRIMERA MEDICIÓN DE RECALL con la moulinette local** (`--k 5`):
    - **docs: Recall@5 = 0,840** (umbral ≥ 0,80) → **pasa**, con 4 puntos de margen. Recall@1 0,650; Recall@3 0,790.
    - **code: Recall@5 = 0,485** (umbral ≥ 0,50) → **falla por 0,015**, que es una pregunta y media de 99. Recall@1 0,263; Recall@3 0,424.
    - `recall@10` sale idéntico a `recall@5` porque se generaron 5 fuentes por pregunta (`--k 5`), no porque el método tenga techo ahí.
  - **Objetivo de M4, ya concreto:** subir el recall de código 1,5 puntos mejorando **el método** (trocear clases de Python por métodos, fusionar secciones pequeñas de Markdown) y midiendo antes y después. **No** ajustando `k1` y `b` contra estos datasets, que es lo que prohíbe el contrato.
- **Verificado (2026-10-06, slice #24):**
  - `make lint` → flake8 sin salida; mypy `Success: no issues found in 28 source files`.
  - `make test` → `149 passed` (13 de `run_search`, 2 de `load_chunks`, 3 de la CLI).
  - **`search` real contra el corpus**, con la pregunta literal del enunciado (`"How to configure OpenAI server?" --k 5`): las tres primeras fuentes son ejemplos de `examples/online_serving/openai_*`. **1,12 s** y 115 MB de memoria; tres consultas seguidas dan 1,14 / 1,10 / 1,15 s, así que el tiempo es estable y lo domina construir el índice, no buscar.
  - **Los seis criterios de aceptación, de punta a punta:** query vacía y solo espacios → `ERROR: query must not be empty`, salida 1; `asdfghjkl` → `No sources found.`, salida 0; `--k 0` → `ERROR: k must be a positive integer`, salida 1; sin índice → `ERROR: index not found: <ruta>; run index first`, salida 1 **y el fichero no se crea**; la pregunta de LoRA → la fuente correcta en posición 1 con 41,27.
- **Verificado (2026-10-01, slice #23):**
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
- **Verificado (2026-10-20, issue #65, carpeta de salida que es un
  fichero):** `make lint` OK y `make test` 243 passed. `answer_dataset` y
  `search_dataset` con `--save_directory …/out.json` → `ERROR: save
  directory must be a folder, not a file: …/out.json`, salida `1`, en
  0,47 s sin cargar Qwen ni el índice y sin crear la carpeta. Nuevo método
  `check_save_directory` en el puerto `DatasetStore`. Límite conocido: una
  carpeta con punto en el nombre (`results.v2`) también se rechaza.
- **Verificado (2026-10-20, issue #64, dónde falla la entrada):** `make
  lint` OK y `make test` 240 passed, ya en Python 3.10. Un JSON roto dice
  línea, columna y motivo (`… (line 3, column 3: Expecting property name
  enclosed in double quotes)`); un JSON con otra forma nombra solo el primer
  campo que falla, para seguir en una línea (`evaluate` real → `ERROR: …
  (search_results: Input should be a valid list)`, salida `1`). Un fichero
  binario no tiene líneas y conserva el mensaje anterior.
- **Verificado (2026-10-20, issue #72, salidas como el enunciado):**
  `make test` 238 passed. `index` real: `Ingestion complete! Indexed 18942
  chunks under …/` (formato de la captura de VI.1, que lleva la misma
  información que «Indices saved under» más el número). `answer_dataset`
  real con Qwen sobre 2 preguntas en 35,7 s: `Loaded 2 questions ...
  Processed 2 of 2 questions` y `Saved student_search_results_and_answer to
  …`. `search` ya daba `file_path [inicio:fin]` (más posición y puntuación).
- **Verificado (2026-10-19, issue #62, prompt por roles):** `make lint` OK,
  `make test` 237 passed. Con el modelo real, 6 preguntas con las mismas
  fuentes de la ejecución completa y el caso John Doe, en 119,6 s y 4,9 GB:
  Neuron mejora (antes 3 pasos genéricos, ahora el comando exacto con
  `VLLM_TARGET_DEVICE="neuron"`); reproducibilidad describe la variable de
  V1 en vez de nombrarla; `max_position_embeddings` sigue en 128000 (la
  referencia dice 4096); el resto, igual. John Doe: ya no confunde la
  pregunta de la fuente, pero responde «The name of the model is vLLM.» en
  vez de negarse. 13,9-18,8 s por respuesta, como antes.
- **M6 abierto (2026-10-19):** issues #61-#68. #61 cerrado (PR #69,
  arquitectura hexagonal pura); en curso #66 (pestañas «Arquitectura» y
  «Casos de uso y comandos»). Orden: #61 → #62 prompt por roles → #63 Python 3.10 →
  #64 mensajes con línea y campo → #65 `--save_directory` → #66 guía de
  ejecución → #67 README → #68 escuela y repo de entrega.
- **Pendiente de M5:** nota de Jose de la muestra de 6 respuestas y recode
  del `/ensayo` (rama `ensayo/<fecha>`).
- **Pendiente para M6 (2026-10-13), resuelto (2026-10-20, #63):**
  `chunk_python` captura también `ValueError` (byte nulo en 3.10 y 3.11),
  con su test, que salía en rojo en 3.10.
- **Pendiente apuntado (2026-10-08), resuelto (2026-10-16):** `load_dataset`
  y `load_search_results` son casi idénticas. `answer_dataset` reutiliza
  `load_search_results` tal cual, así que no hubo tercera copia y siguen sin
  unificar (dos copias no compensan una función común).

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
| 2026-10-06 | Lo compartido por los dos casos de uso vive en `src/application/retrieval.py`; `search.py` se queda solo con `run_search` | Pregunta de Jose: un caso de uso no debe depender de otro. `load_index` y `search_index` no son casos de uso (nadie los ejecuta desde la terminal), son pasos compartidos, y con módulo propio los dos casos de uso dependen de él y no entre ellos. Ningún ciclo posible |
| 2026-10-06 | `validate_query_and_k` es una función compartida, llamada desde `run_search` (antes de cargar el índice) y desde `search_index` | El refactor movió las guardas detrás de `load_index` y un test cazó la regresión: una query vacía respondía por el índice en vez de por la query. Una implementación, dos porteros; `run_search` falla antes de gastar un segundo |
| 2026-10-06 | El índice se carga una vez por dataset, no por pregunta | Medido: 0,92 s por llamada × 200 = 184 s frente a los 90 s permitidos. Con una sola carga, 7,86 s. Hay un test (`test_the_index_is_built_only_once`) que cuenta las llamadas, para que nadie lo "simplifique" |
| 2026-10-06 | **Verificado en el enunciado: el proyecto NO exige orientación a objetos** | Se revisaron los 23 «must» del PDF y todas las menciones de clases; detalle en `docs/SPEC_NOTES.md`. Duda de Jose por un proyecto anterior que sí lo exigía |
| 2026-10-06 | Una query vacía o con solo espacios es un error (`ERROR: query must not be empty`, salida 1), no un resultado vacío (opción A1) | Cierra el ABIERTO de `docs/SPEC_NOTES.md`. Mismo trato que `k`: una entrada sin sentido se rechaza en la frontera. `search "asdfghjkl"` es otro caso, una búsqueda legítima sin resultados, y sale con 0 |
| 2026-10-06 | `search` imprime posición, puntuación, `file_path` y rango; sin fragmento del texto (opción B1) | El `file_path` y el rango son lo que exige el enunciado y lo que compara el corrector; el texto añadiría ruido y decisiones nuevas (cuántos caracteres, saltos de línea). Añadirlo es un cambio de dos líneas en M6 si ayuda a la demo |
| 2026-10-06 | Capas separadas: `load_chunks` en el adaptador, `run_search` en aplicación, la CLI solo imprime (opción C1) | `search_dataset` (#25) necesita el mismo pipeline, así que meterlo en la CLI lo habría duplicado de inmediato |
| 2026-10-06 | La ruta del índice la valida el adaptador, no el caso de uso | Cada comprobación vive donde está el conocimiento: `k` y la query son reglas del problema (aplicación), que el índice exista es un hecho del mundo exterior y solo el adaptador sabe qué es un índice válido. Duplicarla se desincronizaría al cambiar el esquema |
| 2026-10-06 | **Medido antes de implementar:** `sqlite3.connect` crea el fichero que no encuentra | Sin comprobarlo antes, un `search` sin índice dejaría un `index.db` de 0 bytes y fallaría con `no such table: chunks`, jerga interna. La guarda va antes de conectar |
| 2026-10-06 | El material de estudio pasa a un único `docs/conceptos/index.html` con pestañas; se borran `bases-de-datos.html` y `busqueda-lexica-bm25.html` | Petición de Jose: todo en un sitio, con una pestaña por bloque. Los identificadores llevan prefijo (`db-`, `lex-`, `pipe-`) porque `glosario` y `defensa` colisionaban. Autocontenido, sin red ni dependencias, y la URL recuerda la pestaña |
| 2026-10-07 | Rango de ancho 0: guarda en `iou`, no regla `first < last` en `MinimalSource` (opción A) | La moulinette acepta fuentes de referencia vacías; endurecer el modelo rechazaría un dataset entero por una. Detalle en `docs/SPEC_NOTES.md` |
| 2026-10-07 | Idea para M4: medir MRR junto a recall@k | Recall@k no distingue la posición 1 de la 5; MRR sí, y reutiliza `is_match` |
| 2026-10-08 | La línea base se mide como los scripts de examen: `--k 10` y `time uv run` | Medir igual que nos van a medir. Leído en `exams/scripts/exam_retrieval.sh`; los scripts se leen, no se ejecutan (usan los datasets privados) |
| 2026-10-13 | **Experimento #43 descartado:** cortar clases grandes por métodos baja code Recall@5 de 0,485 a 0,465 | Medido contra un índice de `main` en la misma sesión; 5 preguntas suben y 9 bajan. Se revierte y el código queda en la rama local `experiment/43-method-chunks`. Detalle en `docs/SPEC_NOTES.md` |
| 2026-10-13 | El «antes» de cada experimento se reconstruye desde `main`, nunca se da por bueno el índice del disco | El índice del disco ya estaba reconstruido con el código nuevo y la primera comparación salió igual por eso; se detectó porque no daba el 0,485 registrado |
| 2026-10-13 | BM25 original de Okapi (`k1` 1,2, IDF de Robertson) con suelo `1e-6` para la IDF no positiva (opción C) | Definición de referencia y más fácil de explicar; el suelo evita castigar palabras de la pregunta y conserva el desempate. Detalle en `docs/SPEC_NOTES.md` |
| 2026-10-13 | Identificadores con `_` se tokenizan enteros y además por partes (opción B); `CamelCase` fuera | Lo pide la pista del enunciado (VI.1) y conserva el identificador entero; decidido antes de medir. Detalle en `docs/SPEC_NOTES.md` |
| 2026-10-13 | M4 continúa con #46 (MRR) y #45 (peso de la ruta) antes de pasar a M5 | Decisión de Jose con los dos umbrales ya cumplidos |
| 2026-10-13 | `run_evaluate` devuelve un `NamedTuple` `Evaluation(recalls, mrr)` (opción A) | Campos con nombre, mismo patrón que `Bm25Index`; una tupla sin nombres no se lee y otra función repetiría la carga y las guardas |
| 2026-10-14 | **Experimento #45 descartado:** la ruta como tokens del chunk sube code R@5 a 0,727 pero baja docs R@5 a 0,820 | Criterio de M4: ningún cambio puede empeorar la métrica del umbral en un dataset; además reduce el margen de docs de 3 a 2. Código en la rama local `experiment/45-path-tokens`. Detalle en `docs/SPEC_NOTES.md` |
| 2026-10-14 | M5 en 4 issues: stack de CPU (#53, IA), prompt (#54), `answer` (#55) y `answer_dataset` (#56) | Aprobado por Jose; los tres últimos los escribe él |
| 2026-10-14 | Todas las descargas dentro del repo: caché de uv en `.cache/uv` (`pyproject.toml`) y pesos en `.cache/huggingface/` | Propuesta de Jose: el home de la escuela tiene 5 GB casi llenos y el repo vive en `sgoinfree`. Detalle en `docs/SPEC_NOTES.md` |
| 2026-10-14 | `torch` desde el índice de CPU de PyTorch (`explicit = true`) | La versión por defecto incluye CUDA (varios GB) y las máquinas de la escuela no tienen GPU |
| 2026-10-16 | `answer_dataset` responde con las fuentes que ya trae el fichero de `search_dataset`, mediante `answer_from_sources` compartida con `answer`; el modelo se carga una vez después de leer el fichero | Una sola receta para responder (un cambio toca un sitio); no repetir la búsqueda; cargar 100 veces costaría ~8 min más con el mismo resultado |
| 2026-10-15 | Presupuesto del prompt 2.000 tokens; el texto de cada fuente se lee del fichero del corpus por su rango (opción A) | Caben ~5 fuentes, el mismo top 5 que mide Recall@5, en ~15 s por respuesta; leer el fichero no toca `retrieval.py` ni ocupa RAM en las búsquedas |
| 2026-10-15 | `run_answer` recibe el cargador del modelo (`load_generator`), no el modelo cargado; puerto `Protocol` `Generator` | El caso de uso decide cuándo pagar la carga (nunca si la pregunta se rechaza o no hay fuentes); el puerto tiene dos implementaciones reales: Qwen y el falso de los tests |
| 2026-10-15 | Modo velocidad: la IA da el código de producción en el chat, explicado línea a línea, y Jose lo copia; la IA escribe tests y docstrings | Decisión de Jose por ir atrasado; se mantienen test en rojo, gates, revisión local y ensayo. Detalle en `CLAUDE.md` |
| 2026-10-15 | `docs/AI_USAGE.md` pasa a una línea genérica por slice (opción A) | Decisión de Jose; la sección del README se redacta al final, genérica pero veraz (cap. VIII) |
| 2026-10-14 | El prompt añade fuentes en orden hasta que la siguiente no cabe (opción A); pide responder solo con las fuentes o decir que no se puede | Lo más simple y respeta el orden de BM25; la instrucción de no inventar es idea de Jose. Detalle en `docs/SPEC_NOTES.md` |
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
| 2026-10-19 | Arquitectura hexagonal pura (issue #61): `application/ports/` (4 `Protocol`: `Generator`, `IndexStore`, `CorpusReader`, `DatasetStore`), `application/use_cases/`, `adapters/inbound/` (CLI) y `adapters/outbound/` (corpus, JSON, SQLite, Qwen; nombres de Jose: de entrada y de salida, `in` es palabra reservada), `bootstrap.py` como raíz de composición; tests en espejo y `tests/test_architecture.py` | Los casos de uso importaban SQLite, JSON y el corpus directamente: no era hexagonal aunque lo llamáramos así. Se descartó la capa `infrastructure/` (vocabulario de DDD) para no mezclar escuelas; `outbound` es la misma pieza con el nombre de la hexagonal. Sustituye a la decisión del 2026-09-15 de no separar entrada y salida: entonces había 2 adaptadores, ahora 6, y los bonus (API, caché, embeddings) encajan como adaptadores nuevos |
| 2026-10-20 | `.python-version` baja a `3.10` (issue #63) | Es el Python de la escuela: se desarrolla y la CI prueba con la misma versión que el corrector, y `uv sync` no descarga otro intérprete allí. Sustituye a la decisión del 2026-09-17 (3.12). Verificado: con 3.10, `flake8` y `mypy` limpios y la suite completa en verde |
| 2026-10-19 | Prompt por roles: reglas en `system`, fuentes etiquetadas y pregunta en `user` (opción A, issue #62) | Para que quede más limpio y la información le llegue mejor al modelo, no para subir una nota; las etiquetas separan una fuente que contiene su propio `Question:` |
| 2026-10-19 | Todo debe funcionar en Python 3.10 (issue #63) | Es el Python instalado en la escuela y no se puede cambiar |

## Métricas

### Línea base M3 (2026-10-08, commit `69c3281`, slice #27)

La foto del «antes» de M4. Medida como los scripts de examen: `--k 10`,
tiempo de pared con `uv run` incluido (`time`), datasets públicos. Nada se
ajustó para obtenerla.

| Métrica | Valor | Umbral | Estado | Comando |
|---|---|---|---|---|
| Indexado (1.969 ficheros) | **4,51 s** | ≤ 300 s | OK | `time uv run python -m src index --max_chunk_size 2000` |
| 199 preguntas (100 docs + 99 code) | **5,51 s** (2,64 + 2,87), 115 MB | ≤ 90 s | OK | `time uv run python -m src search_dataset --dataset_path data/datasets/UnansweredQuestions/dataset_{docs,code}_public.json --k 10 --save_directory data/output/search_results/UnansweredQuestions` |
| Recall@1/3/5/10 docs | 0,650 / 0,790 / **0,840** / 0,880 | @5 ≥ 0,80 | OK | `./moulinette-ubuntu evaluate_student_search_results data/output/search_results/UnansweredQuestions/dataset_docs_public.json data/datasets/AnsweredQuestions/dataset_docs_public.json --k 10 --max_context_length 2000`; `uv run python -m src evaluate` da lo mismo |
| Recall@1/3/5/10 code | 0,263 / 0,424 / **0,485** / 0,576 | @5 ≥ 0,50 | **FALLA** por 0,015 (2 de 99) | ídem con `dataset_code_public.json` |

Diferencia con la medición anterior: el recall es idéntico; las 199
preguntas bajan de 7,86 s a 5,51 s aunque ahora se piden 10 fuentes en vez
de 5. El código no ha cambiado, así que la diferencia es del entorno (caché
de disco caliente); ponytail: se toma como ruido y se medirá siempre igual.

### Experimentos de M4

| Fecha | Experimento | Chunks | code R@1 / R@3 / **R@5** / R@10 | docs R@5 | Resultado |
|---|---|---|---|---|---|
| 2026-10-13 | Línea base (`main`, `088f538`) | 18.942 | 0,263 / 0,424 / **0,485** / 0,576 | 0,840 | — |
| 2026-10-13 | #43 clases grandes cortadas por métodos | 19.169 | 0,283 / 0,424 / **0,465** / 0,556 | 0,840 | **Descartado** (−2 preguntas en @5) |
| 2026-10-13 | #48 BM25 original (`k1` 1,2, IDF de Robertson con suelo `1e-6`) | 18.942 | 0,303 / 0,475 / **0,535** / 0,576 | 0,830 | **Se queda**: code pasa el umbral (+5 en @5) |
| 2026-10-13 | #44 identificadores enteros y por partes | 18.942 | 0,354 / 0,566 / **0,636** / 0,697 | 0,830 | **Se queda**: +10 en code @5; docs @5 igual, @1 0,650 → 0,610 |
| 2026-10-14 | #45 ruta del fichero como tokens del chunk | 18.942 | 0,444 / 0,667 / **0,727** / 0,798 | **0,820** | **Descartado**: docs @5 −1 pregunta (margen de 3 a 2) |

MRR (desde el slice #46) del estado actual: docs **0,704**, code **0,480**.
**Estado final de M4:** docs R@5 0,830 (margen 3), code R@5 0,636 (margen 14).

### Historial

Gates de métrica locales (necesitan corpus y modelo). La línea base se mide en
M3 antes de optimizar nada.

| Fecha | Métrica | Valor | Umbral | Comando que lo reproduce |
|---|---|---|---|---|
| 2026-09-23 | Tiempo de indexado | **3,65 s** (1.969 ficheros, 18.942 chunks) | ≤ 300 s | `uv run python -m src index` |
| 2026-10-06 | **Recall@5 docs (públicos)** | **0,840** | ≥ 0,80 | `search_dataset --k 5` + `./moulinette-ubuntu evaluate_student_search_results` |
| 2026-10-06 | **Recall@5 code (públicos)** | **0,485** | ≥ 0,50 | ídem; **falla por 0,015**, objetivo de M4 |
| 2026-10-08 | Recall@1/3/5/10 docs (públicos, `--k 10`) | 0,650 / 0,790 / **0,840** / 0,880 | @5 ≥ 0,80 | `search_dataset --k 10` + `uv run python -m src evaluate`; idéntico a la moulinette |
| 2026-10-08 | Recall@1/3/5/10 code (públicos, `--k 10`) | 0,263 / 0,424 / **0,485** / 0,576 | @5 ≥ 0,50 | ídem; @5 falla por 0,015 (2 preguntas) |
| 2026-10-06 | 199 preguntas (docs + code) | **7,86 s** (3,79 + 4,07), 115 MB | ≤ 90 s | `uv run python -m src search_dataset --dataset_path ... --k 5` |
| 2026-10-06 | `search` de una consulta | **1,12 s** (1,10-1,15 s en tres consultas seguidas), 115 MB | — | `uv run python -m src search "How to configure OpenAI server?" --k 5` |
| 2026-09-23 | Tamaño del índice | 25 MB (26.075.136 bytes), 0 páginas libres | — | `uv run python -m src index` + `ls -l data/processed/index.db` |
| 2026-10-19 | Tiempo de indexado (tras #61, máquina más cargada) | **9,43 s**, 81 MB | ≤ 300 s | `uv run python -m src index` |
| 2026-10-19 | 199 preguntas (`--k 10`, tras #61) | **22,6 s** (11,57 docs + 10,99 code), 126 MB | ≤ 90 s | `uv run python -m src search_dataset --dataset_path ... --k 10` |
| 2026-10-19 | `search` de una consulta | **4,5-5,2 s**, 124 MB: 4,62 s construyendo el índice en memoria, 0,03 s buscando | — | `uv run python -m src search "How to configure OpenAI server?" --k 3` |

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
- **Paso 8 del slice #24 (2026-10-06): RESPONDIDO POR LA IA a petición de
  Jose**, no por él. Las tres preguntas (la cadena completa de `search` capa
  por capa; por qué `load_chunks` comprueba el fichero antes de conectar y
  por qué devuelve `list(...)`; y por qué `k` y la query se validan en la
  aplicación mientras la ruta del índice se valida en el adaptador) quedan
  desarrolladas en la pestaña «El pipeline de búsqueda» de
  `docs/conceptos/index.html`, con diagrama de capas. **Hay que ensayarlas en
  voz alta**: es el recorrido que más probablemente le pidan en la defensa.
- **Paso 8 del slice #25 (2026-10-06): PENDIENTE.** Jose cerró la sesión para
  cambiar de chat. Preguntas a cobrar: por qué el índice se carga una vez y
  qué test lo protege; por qué `load_index` y `search_index` están en
  `retrieval.py` y no en `search.py`; y por qué `validate_query_and_k` se
  llama dos veces sin que eso sea duplicación.
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
  **Fallo (2026-10-08):** los issues #43-#46 no entraron solos al tablero;
  al añadirlos con `gh project item-add` las cuatro tarjetas pasaron a
  `Done` y #43 y #46 se cerraron solos. Se reabrieron y se pusieron en
  `Todo`. Sospechosos: «Item added to project» (pone `Done` en vez de
  `Todo`), «Auto-close issue» y «Auto-add to project» (desactivado). Jose
  debe revisarlos; el agente comprueba el tablero tras crear issues.
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
- [ ] En la escuela (Python 3.10): comprobar que `uv sync` usa el Python
  del sistema y no descarga otro (`uv run python --version` → 3.10).
- [ ] En la escuela, clonar en `sgoinfree` y ejecutar todo desde la raíz del
  repo: `.cache/` (uv ~1 GB, modelo ~1,5 GB) y `.venv/` suman ~2,5 GB dentro
  del repo.
- [ ] En la escuela, antes de presentar: `lscpu | grep -m1 "Model name"`,
  `grep -o -w -E "avx512_bf16|amx_bf16|avx2" /proc/cpuinfo | sort -u` y
  `free -h`. Cargamos Qwen en `float32` (2,2 GB de RAM), rápido en cualquier
  CPU x86; comprobar que hay RAM libre y cronometrar una respuesta de
  `answer`.
