# FIN-SYS OS — guía de sesión para Claude

> Se carga sola en cada sesión, también en los worktrees de `.claude/worktrees/`.
> Reemplaza "leer AGENTS.md completo": lo demás se lee **por sección**, solo si la tarea lo pide (mapa en §7).
> Por qué existe y plan de implantación: `docs/guia-trabajo-claude.md`.

## 1. Arranque de sesión

1. Si el worktree está vacío o en una rama nacida de `main`: `git reset --hard master` (`main` está vacía; `master` es la rama real).
2. `git status` y `git fetch`: Andrés trabaja con varias sesiones a la vez.
3. Lee **solo** el frente de tu tarea en `docs/frentes/<nombre>.md`, si existe. No leas `docs/checkpoints.md` completo ni los demás frentes.
4. Si la tarea no es obvia, confírmala en una frase.

## 2. Contexto: lo que más tokens ahorra

Cada turno reenvía todo el contexto acumulado. Una sesión de 900k paga 900k en cada turno.

- **Una tarea = una sesión.** Al cambiar de tema, se cierra el frente y se abre otra sesión.
- **Tope de ~200k.** Al acercarte, actualiza el frente (§5) y pide a Andrés abrir una sesión nueva. No estires hasta 1M.
- **Archivos grandes por rangos.** Grep primero y Read con `offset`/`limit`. Nunca enteros: `fin_sys_core/bot_driver.py` (~2.000 líneas), `database_driver.py` (~2.100), `hub_driver.py`, `bot_sms.py`, `control_tower_driver.py`.
- **Lo verboso, a un subagente:** tests, logs, búsquedas amplias y, sobre todo, la verificación en el navegador.

## 3. Quién hace qué

| Rol | Quién | Para qué |
|---|---|---|
| Orquestador y **único que edita** | Sesión principal | Decidir, diagnosticar, editar, commitear |
| `lector` (Haiku) | Subagente | "¿Dónde/cómo se hace X?": devuelve `archivo:línea` + resumen |
| `corredor-tests` (Haiku) | Subagente | Tests, `health_check.py`, `npm run build`: devuelve solo los fallos |
| `verificador-visual` (Sonnet) | Subagente | Probar un flujo en el navegador: veredicto con evidencia |
| Explore / Plan | Subagentes nativos | Exploración amplia y diseño |

- El diagnóstico de bugs y todas las ediciones quedan en la sesión principal; los subagentes juntan evidencia.
- Dos sesiones no editan los mismos archivos. Si un frente activo ya los toca, coordina con Andrés.

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
- Se actualiza al cerrar, antes de pasar de ~200k y antes de un `/compact`.
- El índice de memoria (`MEMORY.md`) lleva **una línea por entrada**; el estado vivo va en el frente, no en el índice.

## 6. Reglas del proyecto que no se negocian

- **La BD (Supabase) es la misma en local y en producción.** Un dato de prueba o un borrado en local existe en producción. Los tests usan chats `test-…`, la cola `sms_prueba` y limpian sus filas.
- `scripts/session_maintenance.py` **solo con `--check`** (sin argumentos borra en la BD compartida).
- **Token de Telegram compartido:** nunca lanzar `fin_sys_core/bot_telegram.py` en local.
- **Bot (Regla 6b): el bot no adivina.** Dato estructurado en la web o se pide a mano; nada contable sin confirmación humana (borrador → ✅).
- **Python:** siempre `.venv\Scripts\python.exe` (en un worktree sin `.venv`, el del checkout principal).
- **Git:** commits pequeños con archivos explícitos (nunca `git add .`). El **push lo hace Andrés**: `git push origin <rama>:master`. Deploy: `scratch\deploy_prod.py` + sonda (ruta nueva 404→401, `/api/health`).
- **Permiso explícito antes de tocar:** `fin_sys_core/database_driver.py`, `control_tower_driver.py`, esquema de tablas existentes. `.env`: nunca.
- **Zero-impact:** funcionalidad nueva en archivos o routers nuevos (`routers/*.py` + `include_router`); módulos nuevos se registran en `frontend/src/registry/moduleRegistry.js`.
- **Plan antes de código:** lista de archivos a tocar → aprobación de Andrés → cambios.
- La terminal de Andrés es **PowerShell 5.1**: comandos para él con `;` y `curl.exe`, nunca `&&`.

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
