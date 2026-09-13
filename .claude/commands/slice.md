---
description: Arranca un slice - limpieza del anterior, aceptación, rama, tarjeta, concepto, diseño mínimo y test en rojo. Para antes de la implementación
---

Arranca el slice del issue: $ARGUMENTS

0. Limpieza del slice anterior: si queda alguna rama local de un slice cuya
   PR está mergeada, aplica el procedimiento "Tras el merge" de `CLAUDE.md`
   (comprobar merge, actualizar `main`, borrar rama local y remota, tablero en
   `Done`). Nunca borres una rama cuya PR no esté mergeada.
1. Lee el issue (`gh issue view <N> --repo jose-car95/RAG`),
   `docs/PROGRESS.md` y `docs/SPEC_NOTES.md`. Si el slice depende de un punto
   ABIERTO, resuélvelo antes con `/decide`.
2. Presenta a Jose UN comportamiento observable y sus ejemplos de aceptación
   (entrada -> salida esperada). Si difieren del issue, propón la edición del
   issue. ESPERA su OK.
3. Con el OK: `git switch main && git pull --ff-only`, crea la rama
   `<tipo>/<N>-<slug-corto>` y mueve la tarjeta a `In progress`.
4. Explica los conceptos nuevos del slice (tabla "Conceptos nuevos" de
   `CLAUDE.md`) siguiendo "Cómo enseñar", o delega en `/explica`.
5. Diseño mínimo en 5-10 líneas: ficheros, capa en la que vive cada uno,
   firmas (nombre, parámetros, tipo de retorno) y qué devuelve cada función.
   Aplica la skill `ponytail` y di en qué peldaño paras.
6. Escribe el test mínimo que falla, ejecútalo y pega la salida real del
   rojo. No hagas `git add`: Jose revisa el test en VS Code.
7. PARA. El cuerpo lo escribe Jose. Recuérdale que, si se atasca, la ayuda va
   por peldaños (pregunta, pista, pseudocódigo y, solo si lo pide, código).
