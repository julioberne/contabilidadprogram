# Frentes de trabajo — traspaso entre sesiones

Un **frente** es una línea de trabajo que dura más de una sesión (p. ej. `bot-sms`, `terceros`, `partir-bot-driver`).
Cada frente tiene **un solo archivo** aquí: `docs/frentes/<nombre>.md`.

Es la memoria de trabajo que pasa de una sesión a la siguiente, sin importar en qué instancia o worktree se abra.
Es lo que permite limpiar el contexto al cerrar cada hito (`/clear` o `/compact`) sin perder el hilo: el siguiente hito arranca desde aquí y no desde todo el historial.

## Reglas

- **Se sobrescribe, no se anexa.** Máximo ~60 líneas. El historial vive en `git log`.
- **Se actualiza** al cerrar cada hito, antes de un `/clear` o `/compact` y al cerrar la sesión.
- **Una sesión, un frente.** Si dos sesiones necesitan los mismos archivos, Andrés decide cuál edita.
- **Se commitea** con el resto del trabajo (commit `docs(frente): ...`). Al terminar el frente: estado `CERRADO` y una línea en `CHECKLIST.md`.
- Al abrir sesión se lee **solo** el frente de la tarea, no los demás ni `docs/checkpoints.md` completo.

## Plantilla

```markdown
# Frente: <nombre>
Estado: ACTIVO | BLOQUEADO | CERRADO · Actualizado: <AAAA-MM-DD HH:MM> · Rama/commit: <rama> @ <sha>

## Objetivo
<1-3 frases: qué se quiere lograr y cómo se sabe que terminó>

## Estado actual
- Hecho: ...
- En producción: <sha o "no">
- Pendiente de push/deploy: ...

## Próximo paso (concreto, ejecutable sin releer todo)
1. ...

## Decisiones tomadas (y por qué)
- ...

## Archivos clave (ruta:línea cuando aplique)
- ...

## Cómo verificar
- Comando / sonda / flujo en el navegador

## Bloqueos y riesgos
- ...
```
