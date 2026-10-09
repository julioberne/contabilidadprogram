---
name: cerrar-hito
description: Cierra un hito de trabajo en FIN-SYS (contabilidadprogram) y suelta el contexto que ya no sirve. Úsala cuando Andrés escriba /cerrar-hito, cuando el medidor de contexto lo sugiera y el hito en curso esté terminado, o al terminar un commit, una etapa o un bug. Verifica, commitea, actualiza el frente en docs/frentes/ y limpia la sesión.
---

# Cerrar hito

Objetivo: que el siguiente hito arranque desde un frente de ~60 líneas y no desde todo el historial de la sesión.
Sigue los pasos en orden. Si algo falla, detente y dilo; no limpies con trabajo a medias.

## 1. Confirmar el hito
Di en una frase qué hito se cierra y en qué frente (`docs/frentes/<nombre>.md`). Si no hay frente, créalo con la plantilla de `docs/frentes/README.md`.
Si el hito NO está terminado (falta verificar o hay cambios a medias), dilo y no sigas.

## 2. Verificar (con el subagente `corredor-tests`, no en esta sesión)
Brief de 4 partes:
- OBJETIVO: comprobar que el hito no rompió nada.
- SALIDA: su formato estándar (RESULTADO / COMANDOS / RESUMEN / FALLOS).
- FUENTES: los tests del área tocada; además, la lista de tests puros de `.github/workflows/ci.yml` (paso `python -m unittest ...`), con `.venv\Scripts\python.exe` (en un worktree sin `.venv`, el del checkout principal). Si se tocó frontend: `npm run build` en `frontend/`.
- LÍMITES: ningún test que escriba en la BD sin autorización explícita de Andrés en esta sesión (la BD es la de producción); no editar nada.
Si hay fallos: se arreglan antes de cerrar (vuelves al trabajo; el hito no está cerrado).

## 3. Commit
Si hay cambios sin commitear del hito: commit con archivos explícitos (nunca `git add .`), mensaje en el estilo del repo. No hagas push: lo hace Andrés. Si el hito queda listo para producción, en el mensaje final sugiérele `/desplegar`.

## 4. Actualizar el frente (sobrescribir, ≤60 líneas)
Con la plantilla de `docs/frentes/README.md`: estado, hecho, en producción, pendiente de push/deploy, **próximo paso concreto**, decisiones con su porqué, archivos clave (`ruta:línea`), cómo verificar, bloqueos.
Escríbelo pensando en una sesión que no vio nada de esta conversación. Commit `docs(frente): <nombre> — <hito>`.

## 5. Medir
Consulta el contexto de esta sesión (herramienta de uso de sesión de la app, `session_id: "self"`) y anota en el mensaje final: tokens antes de limpiar y % de cuota de 5 horas y semanal.

## 6. Elegir cómo soltar el contexto
- **Limpiar del todo** (lo normal): el siguiente hito arranca bien desde el frente. Usa la herramienta de la app para limpiar esta sesión (`clear_session` con `session_id: "self"`); Andrés aprueba con un clic y la limpieza ocurre al terminar el turno. Al reiniciar, el hook de arranque inyecta los frentes activos.
- **Condensar** (si el siguiente hito depende de detalles finos de este): no limpies; pide a Andrés que escriba `/compact <qué conservar>` o use Esc Esc → "Summarize from here" desde el inicio del hito. Tú no puedes lanzar esos comandos.

## 7. Mensaje final (antes de limpiar: después no queda nada)
Máximo 8 líneas: hito cerrado, commits (sha), qué falta de push/deploy, frente actualizado, contexto medido, y "al limpiar retomo desde `docs/frentes/<nombre>.md`".
