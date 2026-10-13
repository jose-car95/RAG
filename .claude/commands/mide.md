---
description: Mide los gates numéricos (indexado, 200 preguntas, recall@k docs y code) sobre los datasets públicos y registra la fila de métricas
---

Mide las métricas del proyecto. Contexto de la medición: $ARGUMENTS

Solo tiene sentido cuando existen `index` y `search_dataset` con recuperación
real (M3 en adelante). Si no existen, dilo y PARA. La moulinette es material
de evaluación: se ejecuta solo desde este comando, jamás desde `src/` ni
`tests/`. Nunca uses `docs/eval/` ni los datasets privados.

1. Anota qué se mide: `git rev-parse --short HEAD`, `git status --short` y el
   contexto que ha dado Jose.
2. Moulinette local: si no existe `./moulinette-ubuntu`, ejecuta
   `unzip -o docs/moulinette.zip moulinette-ubuntu -d . && chmod +x moulinette-ubuntu`
   (está en `.gitignore`).
3. Si se compara un cambio contra el «antes», el «antes» se mide con un
   índice construido desde `main` (por ejemplo en un `git worktree` aparte),
   nunca con el `data/processed/index.db` que haya en el disco: puede estar
   construido con el código de la rama. Comprueba el número de chunks.
4. Indexado cronometrado:
   `time uv run python -m src index --max_chunk_size 2000`
5. 200 preguntas cronometradas (suma los dos tiempos):
   `time uv run python -m src search_dataset --dataset_path data/datasets/UnansweredQuestions/dataset_docs_public.json --k 10 --save_directory data/output/search_results/UnansweredQuestions`
   `time uv run python -m src search_dataset --dataset_path data/datasets/UnansweredQuestions/dataset_code_public.json --k 10 --save_directory data/output/search_results/UnansweredQuestions`
6. Recall con la moulinette:
   `./moulinette-ubuntu evaluate_student_search_results data/output/search_results/UnansweredQuestions/dataset_docs_public.json data/datasets/AnsweredQuestions/dataset_docs_public.json --k 10 --max_context_length 2000`
   y lo mismo con `dataset_code_public.json`.
7. Pega la salida real de cada paso. Resume en una tabla: métrica, valor,
   umbral (indexado ≤ 300 s; 200 preguntas ≤ 90 s; Recall@5 docs ≥ 0.80;
   code ≥ 0.50), OK o FALLA, y diferencia con la última medición de
   `docs/PROGRESS.md`.
8. Añade las filas a la tabla de métricas de `docs/PROGRESS.md` con fecha
   absoluta y el comando exacto. No hagas `git add`.
9. Si un umbral falla, no propongas tocar parámetros a ciegas contra los
   públicos: formula una hipótesis explicable (qué preguntas fallan y por
   qué) y propón el slice que la prueba.
