---
description: Simulacro de defensa - preguntas de comprensión y 3 recodes que Jose resuelve sin ayuda
---

Simulacro de defensa. Alcance opcional: $ARGUMENTS

1. Lee `docs/PROGRESS.md` y el código actual de `src/`. Todo se ancla a lo
   que ya existe: no preguntes por lo que no está implementado.
2. Preguntas de comprensión, DE UNA EN UNA, esperando la respuesta de Jose
   antes de la siguiente:
   1. ¿Qué es RAG y por qué es útil?
   2. Recorre tu pipeline completo, de los documentos al resultado (hasta
      donde esté implementado).
   3. ¿Diferencia entre TF-IDF y BM25? (desde M3)
   4. ¿Qué decisiones de implementación tomaste y qué trade-offs valoraste?
   5. Si tuvieras más tiempo, ¿qué mejorarías?
   No des pistas durante las respuestas. Al terminar las cinco, valora cada
   una (satisfactoria o insuficiente) y di qué faltó.
3. Recode: crea una rama desechable `ensayo/<fecha>` desde `main` y propone 3
   modificaciones pequeñas y plausibles (un cambio de comportamiento, un dato
   nuevo en un modelo, un mensaje o formato de salida), cada una con su
   criterio de aceptación. Jose las implementa SIN ayuda: ni peldaños ni
   pistas.
4. Después, revisa: ejecuta `make lint` y `make test` y pega la salida; di
   qué quedó bien, qué se rompió y qué regla no negociable se saltó.
5. Lo que Jose no supo explicar o modificar se anota en `docs/PROGRESS.md`
   (Preguntas abiertas) como "volver a explicar".
6. Descartar la rama de ensayo es destructivo: enseña la lista de cambios y
   la rama, y espera el OK explícito de Jose antes de borrarla.
