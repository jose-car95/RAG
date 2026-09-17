# PLAN

Milestones incrementales, **sin fechas** (decisión de Jose, 2026-09-13).
Horizonte de referencia: 4 semanas. Mandatory-first estricto: nunca se empieza
un milestone posterior para que uno anterior "parezca útil".

Cada slice = un comportamiento observable de punta a punta (ver `CLAUDE.md`,
"Flujo de trabajo"). Solo los slices del milestone actual y el siguiente tienen
issue en GitHub; el resto se detalla cuando llegue su momento.

---

## M0 — Esqueleto ejecutable

1. Exponer el punto de entrada `uv run python -m src` con Fire y los seis
   comandos obligatorios como stubs que avisan de que no están implementados.
2. Frontera de errores en la CLI: ninguna excepción sale como traceback; se
   convierte en `Error: <mensaje>` por stderr y código de salida 1.

Salida: `uv run python -m src <comando>` responde para los seis comandos sin traceback y los gates están en verde en CI.

## M1 — Modelos de datos y E/S de datasets

3. Los 8 modelos pydantic del enunciado (VI.4) en la capa de dominio.
4. Cargar un dataset de preguntas desde JSON con errores claros (fichero
   inexistente, JSON roto, esquema inválido).
5. `search_dataset` escribe un `StudentSearchResults` con `retrieved_sources`
   vacíos en `<save_directory>/<nombre del dataset>`.

Salida: `search_dataset` sobre un dataset público real escribe un JSON que la moulinette acepta como válido (recall 0, forma correcta).

## M2 — Indexado: ingesta, chunking y persistencia en SQLite

6. Descubrir los ficheros indexables bajo `data/raw/`; mensaje claro si falta
   o está vacío.
7. Chunking de Markdown/texto con offsets de carácter.
8. Chunking de Python respetando la estructura del código.
9. Persistir los chunks en SQLite bajo `data/processed/` (comando `index`,
   tqdm, una transacción).
10. Validar `--max_chunk_size` (entero positivo, máximo 2000).

Invariante que se testea desde el slice 7: para todo chunk,
`last_character_index - first_character_index <= max_chunk_size <= 2000`
y el rango corresponde a texto real del fichero.

Salida: `index --max_chunk_size 2000` indexa el corpus en ≤ 300 s, deja el índice en `data/processed/` y ningún chunk supera 2000 caracteres.

## M3 — Recuperación BM25 y línea base

Arranca con `/decide` para confirmar BM25 frente a TF-IDF.

11. Tokenizar texto para el emparejamiento léxico.
12. Puntuar chunks con BM25 a partir de las estadísticas guardadas en SQLite.
13. `search <query> --k` imprime las fuentes ordenadas.
14. `search_dataset` rellena `retrieved_sources`.
15. `evaluate` propio: recall@k con solapamiento IoU > 0.05 en el mismo
    fichero (implementación nuestra; nunca la moulinette).
16. Medir y registrar la línea base: Recall@1/3/5/10 (docs y code públicos),
    tiempo de indexado y tiempo de 200 preguntas.

Salida: primer Recall@1/3/5/10 real sobre los datasets públicos y tiempos, registrados como línea base en `docs/PROGRESS.md`.

## M4 — Recall hasta los umbrales

Cada experimento es un slice con número antes/después en la tabla de métricas.
Candidatos (no decididos): partir identificadores (`snake_case`, `CamelCase`),
fronteras y solapamiento de chunks, peso de la ruta del fichero y de los
títulos, tratamiento de docs frente a código. Regla: ningún parámetro se
elige por búsqueda ciega contra los datasets públicos (ver
`docs/SPEC_NOTES.md`).

Salida: Recall@5 ≥ 0.80 en docs y ≥ 0.50 en code sobre los públicos (verificado con la moulinette local) y 200 preguntas en ≤ 90 s.

## M5 — Generación con Qwen3-0.6B en CPU

Requiere OK de Jose para la descarga (torch CPU + transformers + pesos).

17. Añadir el stack de generación solo para CPU.
18. Construir el prompt con el contexto recuperado dentro del presupuesto de
    tokens.
19. `answer <query> --k` genera una respuesta fundamentada.
20. `answer_dataset` escribe un `StudentSearchResultsAndAnswer`.

Salida: `answer "How to configure OpenAI server?" --k 10` produce en CPU una respuesta fundamentada en las fuentes, y `answer_dataset` escribe un JSON válido.

## M6 — Robustez, README y ensayo de defensa

21. Entradas degeneradas: query vacía, query sin sentido, `k=0`, ficheros
    inexistentes, JSON malformado.
22. README completo con todas las secciones del enunciado (capítulo VIII).
23. Ensayo de recode y de las preguntas de comprensión.
24. Prueba en la máquina de la escuela (disco, cachés, CPU) y checklist del
    repo de entrega.
25. Pulir mensajes de error con detalle en una línea: línea y columna del
    JSON roto y campo que falla en pydantic (decisión de Jose, 2026-09-17).

Salida: los tres flujos de examen en verde en local, README completo y ensayo de recode superado.

## M7 — Bonus

Solo si M0–M6 están cerrados. Orden propuesto: caché, indexado incremental
(SQLite lo abarata), embeddings semánticos, recuperación híbrida, API HTTP
local.

Salida: cada bonus implementado se demuestra con un comando y queda documentado con resultados en el README.
