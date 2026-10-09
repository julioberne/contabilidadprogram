# Frente: guia-claude
Estado: ACTIVO · Actualizado: 2026-10-09 · Rama: claude/multi-model-mcp-orchestration-3d985e (lo sin publicar: `git log origin/master..HEAD`)

## Objetivo
Método de trabajo con Claude que baja el consumo de contexto y mejora el proceso de construcción: corte por hito, kit de sesión, agente de mantenimiento y herramientas especializadas. Guía completa: `docs/guia-trabajo-claude.md` (§8 plan, §9 catálogo).

## Estado actual
- En master: `CLAUDE.md`, frentes, guía, kit (hooks arranque y medidor, `/cerrar-hito`, subagentes), `medir_consumo_claude.py`.
- Hecho el 06-oct (falta publicar):
  - **Guardia** (`scripts/claude_kit/guardia.py`, PreToolUse): niega a Claude push y `publicar.*`, `session_maintenance.py` sin `--check`, `bot_telegram.py`, `migrate_*.py`, SQL de escritura contra la BD, `.env`, Dokploy fuera de `deploy_prod.py`; pide confirmación para los drivers 🔴. Registro en `scratch/guardia.log`.
  - **Lint crítico** (`scripts/lint_critico.py`): ruff E9/F63/F7/F82 + eslint solo reglas que rompen en ejecución. Hook `lint_al_editar.py` (PostToolUse) y pasos nuevos en el CI. El lint de estilo tiene 191 errores viejos y no bloquea.
  - **Chequeo diario** (`chequeo_diario.py`): todo lo determinista del mantenimiento en un comando con un solo permiso; tarea programada con prompt nuevo de 3 pasos. Tablero del 06-oct generado y limpio.
  - `tests/test_claude_kit.py` (19 tests puros, en el CI). Kit reinstalado en `~/.claude` (`instalar.py --check`: todo igual).
  - Permisos `git push *` y `python -c ' *` quitados (respaldos en `scratch/settings.local.json.*`).
  - Memoria: 5 `estado-proyecto-sep-*` → `historial-estado-proyecto-sep`. 5 docs viejos → `docs/archive/`. Spec 09.I y SPEC.md del bot al día.
- Verificado en uso real: el lint-al-editar atrapó un nombre no definido en esta sesión; la guardia bloqueó un commit cuyo mensaje decía "git push" (falso positivo, corregido y con test).
- Modelo: Opus 5.5 desde el 3-oct (Andrés). Contexto medio por turno: 417k (02-oct) → 407k (06-oct, 7 días).

- Catálogo §9 completo: también `auditor-spec` (subagente Sonnet, solo lectura, una vez por etapa) y `/desplegar` (skill que solo invoca Andrés: prepara y verifica alrededor de `publicar.cmd`). Instalados; aparecen en las sesiones nuevas. Tests del kit: 23.
- Prueba del auditor con la spec 13.4: "SOLO FALTA LO MANUAL", pero son 2 CA manuales (CA-134-01 y CA-134-11), no 1; 6 casos borde sin test (ANULADO, DT-30, USD en impuestos…); la spec dice 10 hojas y el código genera 12. Le toca al frente `analisis-exportacion`.

## Próximo paso
1. Andrés: publicar con `scripts\publicar.cmd --sin-deploy` (solo scripts, CI y docs; no toca la app) y mirar que el CI quede verde con los pasos nuevos de lint.
2. Confirmar que la corrida de las 10 pm termina sola (tablero con la sección Sesiones llena y una fila nueva en `scratch/medicion-historial.csv`). Si se detiene, ver qué permiso pidió en Scheduled.
3. Revisar `scratch/guardia.log` en los próximos días: cualquier bloqueo injusto se corrige en `guardia.py` + test.
4. Primer uso real de `/desplegar` y de `auditor-spec` al cerrar la próxima etapa; ajustar sus instrucciones con lo que se vea.

## Pendiente de decisión de Andrés
- Propuestas del tablero: acortar 8 entradas largas del índice de memoria; `docs/PRD.md` sin cambios en 45 días.

## Decisiones tomadas (y por qué)
- La guardia niega push y `publicar.*` a Claude porque el flujo es: Claude commitea → Andrés publica. Si bloquea, no se esquiva (CLAUDE.md §6).
- Lint en el CI solo de errores graves: el de estilo tiene deuda vieja y bloquearía todo.
- Un solo comando y un solo permiso para el mantenimiento: la corrida del 5-oct se trabó esperando 3 aprobaciones.
- No orquestar otros modelos; sin tope fijo de contexto; no partir archivos; kit a nivel de usuario.

## Archivos clave
- `scripts/claude_kit/{guardia,lint_al_editar,chequeo_diario,instalar}.py`, `scripts/lint_critico.py`, `scripts/claude_kit/mantenimiento.md`, `tests/test_claude_kit.py`, `.github/workflows/ci.yml`, `CLAUDE.md` §3 y §6, `~/.claude/settings.json` (hooks y permiso del chequeo).

## Cómo verificar
- `.venv\Scripts\python.exe -m unittest tests.test_claude_kit` (19) · `python scripts/lint_critico.py` → sin errores graves.
- `python scripts/claude_kit/instalar.py --check` → todo "igual" y hooks al día.
- `scratch\tablero.md` con la fecha del día; `scratch\guardia.log` para ver qué bloqueó.

## Bloqueos y riesgos
- Los hooks fallan abiertos y actúan por llamada de herramienta: un `.py` escrito y luego ejecutado puede esquivar la guardia.
- Las corridas programadas solo ocurren con la app abierta.
