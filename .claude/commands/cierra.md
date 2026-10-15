---
description: Cierra el slice actual - gates, docs, commits, push, PR y tablero. Para si algo está en rojo
---

Cierra el slice en curso. $ARGUMENTS

1. Identifica el slice: rama actual (`<tipo>/<N>-<slug>`) e issue #N. Si
   estás en `main` o no hay issue, PARA y dilo.
2. Ejecuta TODOS los gates y guarda la salida real:
   - `make lint`
   - `make test`
   - Si el slice toca indexado, recuperación o rendimiento: la medición de
     métricas y la tabla de métricas de `docs/PROGRESS.md`.
   Si algún gate está en rojo: PARA, pega la salida y no abras nada.
3. Comprueba que no se importa la moulinette:
   `grep -rnE "^[[:space:]]*(import|from)[[:space:]]+moulinette" src/ tests/ --include="*.py"`
   debe salir vacío.
4. Actualiza `docs/PROGRESS.md` (estado actual, verificado con qué comandos,
   siguiente paso, decisiones nuevas) y añade la fila del slice en
   `docs/AI_USAGE.md`: una frase genérica con las tareas en que ayudó la IA,
   sin detallar líneas ni funciones concretas (ver `CLAUDE.md`). Actualiza
   `docs/EVALUATION.md` si el slice aporta evidencia.
5. PAUSA DE REVISIÓN: enseña `git status --short` y `git diff --stat`, di a
   Jose que revise los cambios resaltados en VS Code y ESPERA su OK. No hagas
   `git add` antes. Si pide cambios, aplícalos (o guíale si es código de
   producción) y vuelve a este paso.
   Con el OK, añade rutas concretas (nunca `git add -A` ni `git add .`). Nada
   generado, pesado (>5 MB) ni secretos.
6. Commits pequeños con la convención de `CLAUDE.md`: inglés, imperativo,
   <=50 caracteres, sin cuerpo salvo que el porqué no sea evidente, y SIN
   NINGUNA atribución a la IA (ni Co-Authored-By, ni Generated with, ni
   enlaces de sesión, ni emojis).
7. `git push -u origin <rama>`.
8. Abre la PR con `gh pr create` rellenando `.github/pull_request_template.md`
   con evidencia real pegada, `Closes #N` y el veredicto ponytail en "Diseño en
   5 líneas". Sin atribución a la IA en título ni cuerpo.
9. Mueve la tarjeta del issue a `In review` en el tablero si la automatización
   no lo ha hecho (comprueba con `gh project item-list`).
10. Termina con la URL de la PR y recuerda a Jose que el merge lo hace él.
    Cuando diga que ha mergeado, sigue el procedimiento "Tras el merge" de
    `CLAUDE.md` (borrar rama local y remota, actualizar `main`, tablero).
