# Frente: guia-claude
Estado: ACTIVO · Actualizado: 2026-10-06 · Rama/commit: claude/multi-model-mcp-orchestration-3d985e @ 4badc82

## Objetivo
Método de trabajo con Claude que baja el consumo de contexto y mejora el proceso de construcción: corte por hito, kit de sesión, agente de mantenimiento y herramientas especializadas. Guía completa: `docs/guia-trabajo-claude.md` (§8 plan, §9 catálogo).

## Estado actual
- En master: `CLAUDE.md`, `docs/frentes/`, guía §1-§9, kit (`scripts/claude_kit/`: hooks arranque y medidor, `instalar.py`, `mantenimiento.md`), `/cerrar-hito`, subagentes `lector`, `corredor-tests`, `verificador-visual`, `scripts/medir_consumo_claude.py`.
- Instalado en `~/.claude` y verificado en uso real (el medidor avisa; `instalar.py --check` da todo igual).
- Modelo: desde el 3-oct las sesiones principales corren 100% en Opus 5.5 (antes, 90% en Fable 5/5.1). HECHO por Andrés.
- Sesiones pesadas archivadas. HECHO por Andrés.
- Otras sesiones ya usan frentes (analisis-exportacion, bot-mini-app-terceros, panel-contexto-crud).
- **Agente de mantenimiento TRABADO:** la corrida del 5-oct espera desde las 12:48 la aprobación de 3 comandos de PowerShell; el tablero sigue del 2-oct.

## Próximo paso
1. Andrés: barra lateral → Scheduled → corrida del 5-oct → aprobar con "permitir siempre" (o detenerla y usar "Run now").
2. Construir guía §9 #1 y #2 (plan de archivos → aprobación → código):
   - Hook `guardia` (PreToolUse, en `scripts/claude_kit/`, instalado con `instalar.py`): negar a Claude `git push`, `scripts\publicar.cmd`/`publicar.py` (los corre Andrés), `session_maintenance.py` sin `--check`, `bot_telegram.py`, `scripts/migrate_*.py`, SQL de escritura en comandos, `.env`, API de Dokploy fuera de `deploy_prod.py`; pedir confirmación para `database_driver.py` y `control_tower_driver.py`; registro en `scratch/guardia.log`; tests del hook.
   - Hook `lint-al-editar` (PostToolUse): `ruff check --select F,E9` en `.py` y eslint en `.js`/`.jsx` del archivo editado; errores a Claude con exit 2. Agregar ruff (dependencia de desarrollo) y `npm run lint` al CI.
3. Script único de chequeos para la tarea de mantenimiento, para que pida un solo permiso.

## Pendiente de decisión de Andrés
- Quitar `Bash(git push *)` y `Bash(python -c ' *)` de `.claude/settings.local.json` (checkout principal y worktrees).
- Consolidar las memorias `estado-proyecto-sep-04/07/09/11/15` y archivar 5 docs viejos (`conexion_bd_guia`, `D02_FIN_spec`, `design_system`, `module_08_project_hub`, `remediacion_2026-07`), revisando antes.
- Spec 09.I dice PLANIFICADO pero la v1 se desplegó el 2-oct: lo corrige la sesión del frente `bot-mini-app-terceros`.

## Decisiones tomadas (y por qué)
- No orquestar otros modelos todavía: multiplican el consumo y no atacan el contexto reenviado.
- Sin tope fijo de contexto y sin partir archivos (Andrés, 01-oct): se corta por hito.
- Un solo agente escribe; los subagentes juntan evidencia.
- Kit a nivel de usuario: llega a worktrees nacidos de `main` vacía; solo actúa en este proyecto.
- Flujo: Claude deja el código commiteado → Andrés publica con `scripts\publicar.cmd` → Claude nunca hace push ni publica.

## Archivos clave
- `CLAUDE.md`, `docs/guia-trabajo-claude.md`, `scripts/claude_kit/*`, `.claude/agents/*`, `.claude/skills/cerrar-hito/SKILL.md`, `~/.claude/settings.json` (hooks), tarea `mantenimiento-finsys`.

## Cómo verificar
- `python scripts/claude_kit/instalar.py --check` → todo "igual".
- `.venv\Scripts\python.exe scripts\medir_consumo_claude.py --dias 7` → contexto medio por turno (base 370k; 02-oct 417k).
- `scratch\tablero.md` con la fecha del día.

## Bloqueos y riesgos
- Las corridas programadas se detienen en avisos de permiso y solo corren con la app abierta.
- Los hooks fallan abiertos: el guardia reduce el riesgo, no lo elimina (ver guía §9, preguntas abiertas).
