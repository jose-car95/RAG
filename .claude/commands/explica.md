---
description: Explica un concepto delegando en el subagent tutor (no modifica ficheros)
---

Explica a Jose el concepto: $ARGUMENTS

1. Delega la explicación en el subagent `tutor` (Agent con
   `subagent_type: tutor`), pasándole el concepto y el contexto mínimo
   necesario: milestone actual (según `docs/PROGRESS.md`) y el fichero o slice
   en el que estamos trabajando, si aplica.
2. Presenta la respuesta del tutor tal cual, sin recortarla ni reescribirla.
3. Si la explicación contradice una decisión registrada en `docs/PROGRESS.md`
   o `docs/SPEC_NOTES.md`, señala la discrepancia debajo, citando la decisión.
4. No modifiques ningún fichero.
