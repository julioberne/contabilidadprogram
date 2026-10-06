# FIN-SYS OS — guía de sesión para Claude

> Se carga sola en cada sesión, también en los worktrees de `.claude/worktrees/`.
> Reemplaza "leer AGENTS.md completo": lo demás se lee **por sección**, solo si la tarea lo pide (mapa en §7).
> Por qué existe y plan de implantación: `docs/guia-trabajo-claude.md`.

## 1. Arranque de sesión

1. Si el worktree está vacío o en una rama nacida de `main`: `git reset --hard master` (`main` está vacía; `master` es la rama real).
2. `git status` y `git fetch`: Andrés trabaja con varias sesiones a la vez.
3. Lee **solo** el frente de tu tarea en `docs/frentes/<nombre>.md`, si existe. No leas `docs/checkpoints.md` completo ni los demás frentes.
4. Si la tarea no es obvia, confírmala en una frase.

## 2. Contexto: corte por hito, no por número

Cada turno reenvía todo el contexto acumulado: una sesión de 900k paga 900k en cada turno.
En los mensajes, el 86% es tráfico de herramientas (navegador, ediciones, lecturas, terminal) y solo el 14% es la conversación. Ese tráfico de un hito ya cerrado es peso muerto.

- **La sesión crece lo que la tarea necesite.** No hay tope fijo: una tarea grande puede usar 400k o más si va a mitad de un hito.
- **La señal de corte es el hito:** algo terminado y verificado (un commit, una etapa, un bug cerrado) o un cambio de subtarea.
- **Al cerrar un hito** (la skill `/cerrar-hito` hace todo esto: verificar, commit, frente, medir, limpiar):
  1. Actualiza el frente (§5) con lo que el siguiente hito necesita saber.
  2. Limpia con la herramienta que corresponda:
     - `/clear`: el siguiente hito arranca bien desde el frente. Lo deja en cero; la conversación queda guardada en `/resume`.
     - `/rewind` (Esc Esc) → "Summarize from here" sobre el inicio del hito: condensa solo ese hito y conserva lo anterior.
     - `/compact <qué conservar>`: condensa todo, guiado por la sección "Compact Instructions" de abajo.
  3. Sigue desde el frente. Para ver qué ocupa el contexto: `/context`.
- **Ampliar solo si hace falta:** primero el frente, luego la spec, luego el código. Archivos grandes con Grep y Read por rangos (`offset`/`limit`); enteros solo si la tarea lo exige.
- **Lo verboso, a un subagente:** tests, logs, búsquedas amplias y, sobre todo, la verificación en el navegador.
- **Referencia:** a 400k cada turno cuesta el doble que a 200k. Si estás ahí y no vas a mitad de un hito, toca cortar.

## 3. Quién hace qué

La sesión principal orquesta y es la **única que edita**: decide, diagnostica, edita, commitea. Para lo demás:

| Para… | Usa |
|---|---|
| "¿Dónde/cómo se hace X?", resumir un archivo grande | subagente `lector` (Haiku): `archivo:línea` + resumen |
| Tests, `health_check.py`, `npm run build`, logs largos | subagente `corredor-tests` (Haiku): solo los fallos |
| Probar un flujo en el navegador | subagente `verificador-visual` (Sonnet): veredicto con evidencia |
| Exploración amplia o diseño de un plan | subagentes nativos Explore / Plan (corren en el modelo principal: no son baratos; para ubicar algo concreto, `lector`) |
| Cerrar un hito y soltar contexto | skill `/cerrar-hito` |
| Contexto y cuota de esta sesión | herramienta de uso de sesión de la app (`self`) o `/context` |
| Dudas sobre Claude Code (hooks, skills, ajustes) | subagente `claude-code-guide` |
| Planes de prueba automáticos | MCP TestSprite, solo si Andrés lo pide |
| Investigación con fuentes verificadas | `/deep-research`, solo si Andrés lo pide (gasta mucho) |

- El diagnóstico de bugs y todas las ediciones quedan en la sesión principal; los subagentes juntan evidencia.
- Dos sesiones no editan los mismos archivos. Si un frente activo ya los toca, coordina con Andrés.
- **Kit automático** (instalado en `~/.claude`, fuente en `scripts/claude_kit/`): al arrancar, tras `/clear` y tras compactar, un hook te muestra los frentes activos y el resumen del tablero del agente de mantenimiento (`scratch/tablero.md`); desde ~350k, otro hook te avisa una vez por tramo para proponer `/cerrar-hito`.

## 4. Brief para delegar (las 4 partes, siempre)

```
OBJETIVO: qué necesito saber o comprobar, y para qué decisión.
SALIDA: formato y largo máximo (p. ej. "≤15 líneas: veredicto + archivo:línea").
FUENTES/HERRAMIENTAS: dónde buscar, qué comandos o URL usar, qué Python (`.venv\Scripts\python.exe`).
LÍMITES: qué NO hacer (no editar, no escribir en la BD, no enviar formularios), cuándo parar.
```

El subagente no ve esta conversación: pon en el brief todo lo que necesita.

## 5. Frentes: traspaso entre sesiones

`docs/frentes/<nombre>.md` (plantilla en `docs/frentes/README.md`): objetivo, estado, próximo paso, decisiones, archivos clave, cómo verificar.

- Se **sobrescribe**, no se anexa (≤60 líneas); el historial está en `git log`.
- Se actualiza **al cerrar cada hito**, antes de un `/clear` o `/compact` y al cerrar la sesión.
- El índice de memoria (`MEMORY.md`) lleva **una línea por entrada**; el estado vivo va en el frente, no en el índice.

## 6. Reglas del proyecto que no se negocian

- **La BD (Supabase) es la misma en local y en producción.** Un dato de prueba o un borrado en local existe en producción. Los tests usan chats `test-…`, la cola `sms_prueba` y limpian sus filas.
- `scripts/session_maintenance.py` **solo con `--check`** (sin argumentos borra en la BD compartida).
- **Token de Telegram compartido:** nunca lanzar `fin_sys_core/bot_telegram.py` en local.
- **Bot (Regla 6b): el bot no adivina.** Dato estructurado en la web o se pide a mano; nada contable sin confirmación humana (borrador → ✅).
- **Python:** siempre `.venv\Scripts\python.exe` (en un worktree sin `.venv`, el del checkout principal).
- **Git:** commits pequeños con archivos explícitos (nunca `git add .`). **Publicar lo hace Andrés** con `scripts\publicar.cmd` en la terminal de la sesión (push a master + CI + deploy con sonda + `:8000` al día; `--sin-deploy`, `--simular`). Al terminar un hito, dile "listo para publicar" con la lista de commits. A mano: `git push origin <rama>:master`, `scratch\deploy_prod.py` + sonda (ruta nueva 404→401, `/api/health`).
- **Permiso explícito antes de tocar:** `fin_sys_core/database_driver.py`, `control_tower_driver.py`, esquema de tablas existentes. `.env`: nunca.
- **Zero-impact:** funcionalidad nueva en archivos o routers nuevos (`routers/*.py` + `include_router`); módulos nuevos se registran en `frontend/src/registry/moduleRegistry.js`.
- **Plan antes de código:** lista de archivos a tocar → aprobación de Andrés → cambios.
- La terminal de Andrés es **PowerShell 5.1**: comandos para él con `;` y `curl.exe`, nunca `&&`.

## Compact Instructions

Al compactar (manual o automático), conserva:
- El frente activo: objetivo, próximo paso y decisiones tomadas con su porqué.
- Archivos modificados y commits del trabajo en curso (sha y qué cambió), y lo pendiente de push o deploy.
- Errores sin resolver, con su mensaje exacto y dónde aparecen.
- Las instrucciones y aprobaciones explícitas de Andrés en esta sesión.

Descarta: salida de tests que pasaron, contenido de archivos ya commiteados, capturas y páginas del navegador, resultados de búsquedas ya usados y caminos de diagnóstico descartados.

## 7. Mapa: leer bajo demanda, por sección

| Necesito… | Dónde |
|---|---|
| Estado de módulos y permisos por archivo | `AGENTS.md` → "Estado de Módulos", "PERMISOS EXPLÍCITOS POR ARCHIVO" |
| Reglas completas del bot | `AGENTS.md` → "BOT IA (Módulo 09)"; `docs/reglas_proyecto.md` |
| Comandos de desarrollo y tests | `AGENTS.md` → "Comandos de Desarrollo" |
| Cómo se trabaja hoy (push, deploy, producción) | `WORKFLOW.md` → "Estado real" |
| Pendientes y deuda técnica | `CHECKLIST.md` → "2. Pendientes abiertos" |
| Spec de una etapa | `docs/specs/README.md` |
| Esquema de BD / API | `docs/database_schema.md`, `docs/api_spec.md` |
| Qué pasó antes | `git log`, el frente; `docs/checkpoints.md` solo la entrada concreta (Grep) |
| Medir el consumo de tokens | `.venv\Scripts\python.exe scripts\medir_consumo_claude.py --dias 14` |
