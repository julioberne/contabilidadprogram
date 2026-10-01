# Guía de trabajo con Claude — plan y seguimiento

> Las reglas del día a día están en `CLAUDE.md` (raíz), que se carga solo en cada sesión.
> Este documento explica **por qué** existen y lleva el **plan de implantación** con su avance.
> Creado el 01-oct-2026.

## 1. Diagnóstico (medido el 30-sep-2026)

Datos de 18 sesiones en 30 días (`scripts/medir_consumo_claude.py`):

| Medida | Valor |
|---|---|
| Tokens releídos de caché (contexto reenviado en cada turno) | 4.450 M, el 96% del volumen |
| Tokens escritos por Claude (salida) | 19 M (0,4%) |
| Contexto medio por turno | ~370.000 |
| Sesiones que pasaron de 700.000 | 5, y aportan el 75% del gasto |
| Sesión más grande | 3.089 turnos, pico 959.000, 1.430 M ella sola |
| Qué llena el contexto | navegador 40%, lecturas de archivos 27%, terminal 17% |
| Archivos más releídos | `bot_driver.py` 45 veces, `database_driver.py` 29, `bot_sms.py` 21 |

**Conclusión:** el gasto lo domina la *longitud de las sesiones*, no el tamaño del repo ni el modelo.
Cada turno reenvía todo el contexto acumulado; una sesión a 900k paga 900k en cada turno.
Con un tope de 200k por turno y el mismo trabajo, el total habría bajado al menos a la mitad.

**De qué están hechos los mensajes** (medido el 01-oct sobre las mismas 18 sesiones, 23,8 M caracteres):

| Parte | % |
|---|---|
| Resultados del navegador | 23% |
| Código que Claude escribe en ediciones (Edit/Write) | 19% |
| Lecturas de código | 13% |
| Salida de terminal | 11% |
| Entradas de otras herramientas (comandos, scripts) | 10% |
| Conversación real (lo que escribe Andrés, texto y razonamiento de Claude) | 14% |
| Lecturas de documentos `.md` (docs y memoria) | 2% |

El 86% es tráfico de herramientas. Al cerrar un hito ese tráfico ya no sirve, pero sigue viajando en cada turno hasta que se limpia con `/clear` o `/compact`.
Los documentos desactualizados pesan poco *dentro* de la sesión (2%); su costo es que se leen al arrancar y confunden con estado viejo.

## 2. Decisión sobre orquestar otros modelos (Kimi, Hermes, ChatGPT/Codex)

Investigación profunda del 30-sep-2026 (25 afirmaciones verificadas):

- Delegar a varios agentes **multiplica** el consumo total (Anthropic: ~15x un chat frente a ~4x un agente solo); lo que baja es el contexto del orquestador.
- El código se paraleliza mal; la regla más respaldada es **un solo agente escribe** y los demás buscan, leen y revisan.
- El orquestador debe ser el modelo más fuerte; un modelo barato como principal limita la calidad.
- Los subagentes nativos de Claude Code (con `model: haiku` o `sonnet`) ya aíslan la salida verbosa. Su límite: solo modelos de Anthropic y gastan del mismo plan.
- `codex mcp-server` fue eliminado en Codex 0.154.0 (sep-2026) y PAL MCP (zen-mcp) está sin mantenimiento desde dic-2025: no depender de MCPs de terceros.

**Decisión:** primero corte por hito (limpiar el contexto al cerrar cada hito y seguir desde el frente) + subagentes nativos.
Un modelo externo solo entra más adelante como **revisor de solo lectura** y solo si, después de las fases 1-3, se sigue agotando la cuota (fase 5).
Partir `bot_driver.py` y `database_driver.py` quedó **descartado** por Andrés el 01-oct: el problema no es el tamaño de los archivos sino arrastrar el contexto de hitos ya cerrados.

## 3. Arquitectura de roles

| Rol | Quién | Hace | No hace |
|---|---|---|---|
| Orquestador y único escritor | Sesión principal (Opus) | Decide, diagnostica, edita, commitea | Leer logs o páginas enteras, verificar visualmente |
| `lector` | Subagente Haiku | Buscar y resumir código: `archivo:línea` + resumen | Editar, ejecutar |
| `corredor-tests` | Subagente Haiku | Correr tests, health check, build; devolver solo fallos | Editar, git, comandos que escriban en la BD |
| `verificador-visual` | Subagente Sonnet | Probar un flujo en el navegador; veredicto con evidencia | Editar código o datos |
| Explore / Plan | Subagentes nativos | Exploración amplia y diseño | Editar |
| Revisor externo (futuro) | Codex / Kimi vía script | Segunda opinión sobre un diff | Escribir, ver `.env` |

Las definiciones de los subagentes están en `.claude/agents/` (ver fase 1).

## 4. Plan de implantación

| Fase | Qué | Quién | Estado |
|---|---|---|---|
| 0 | `CLAUDE.md`, subagentes (repo + copia global), `docs/frentes/`, script de medición, índice de memoria recortado, cabeceras de `AGENTS.md`/`WORKFLOW.md`/`CHECKLIST.md` apuntando a `CLAUDE.md` | Claude | HECHO 01-oct (pendiente push) |
| 1 | Que todas las instancias arranquen con la guía (ver 4.1) | Andrés | PENDIENTE |
| 2 | Adelgazar lo que se lee al arrancar (ver 4.2) | Claude, con aprobación | PENDIENTE |
| 3 | Ciclo por hito y limpieza del contexto (ver 4.3) | Claude en cada sesión; hooks con aprobación | EN CURSO desde 01-oct |
| 4 | Medir a las 2 semanas (ver 4.4) | Claude | PENDIENTE (~15-oct) |
| 5 | Revisor externo, solo si la fase 4 lo justifica (ver 4.5) | Decide Andrés | EN ESPERA |

### 4.1 Fase 1 — Que la guía valga en cualquier instancia

Problema: la rama por defecto de GitHub es `main`, que está vacía. Cada worktree que crea la app nace de `main` sin el código ni esta guía, y hay que hacer `git reset --hard master` a mano.

Cómo llega la guía a cada sesión (según la documentación de Claude Code):

| Pieza | Dónde vive | Llega a… |
|---|---|---|
| `CLAUDE.md` | raíz del repo (`master`) | Toda sesión del checkout principal y de sus worktrees: Claude Code carga los `CLAUDE.md` de la carpeta actual **y de todas las carpetas padre**, y los worktrees están dentro del repo |
| Subagentes | `.claude/agents/` (versionados) **y** copia en `~/.claude/agents/` (instalada el 01-oct) | Toda sesión de este PC, aunque el worktree nazca vacío. Si existen en ambos sitios, gana la del proyecto |
| Memoria (`MEMORY.md`) | `~/.claude/projects/...contabilidadprogram/memory/` | Ya es compartida por todas las sesiones y worktrees del proyecto |
| Frentes | `docs/frentes/` (versionados) | Cualquier sesión que esté sobre `master` |

Nota: si antes Claude leía `AGENTS.md` solo, al existir `CLAUDE.md` deja de hacerlo; por eso las reglas críticas están copiadas en `CLAUDE.md` §6.

Pasos:

1. **Push de la fase 0:** `git push origin claude/multi-model-mcp-orchestration-3d985e:master` y luego `git pull` en el checkout principal (para que su `CLAUDE.md` lo vean los worktrees).
2. **Que los worktrees nazcan de `master`**, una de dos:
   - (Recomendada) rama por defecto = `master` en GitHub (Settings → General → Default branch) y luego `git remote set-head origin -a` en el checkout principal. Antes, confirmar que Dokploy despliega `master` por nombre y no "la rama por defecto".
   - O el ajuste `worktree.baseRef: "head"` en la configuración de Claude Code (los worktrees salen del `HEAD` local del checkout principal). Falta confirmar que la app de escritorio lo respeta.
   - Opcional: un archivo `.worktreeinclude` con `.env` para que cada worktree nuevo traiga su copia (hoy se usa el `.env` del checkout principal).
3. **Red de seguridad, no tope** (decisión de Andrés del 01-oct: un número fijo como 200k restringe las tareas grandes). Opus 5.5 trae 1M de serie y compacta solo cerca de ~967k. Opcional: `CLAUDE_CODE_AUTO_COMPACT_WINDOW=500000` en el bloque `env` de `~/.claude/settings.json`, para que una sesión que se olvidó de cortar se compacte sola a ~500k y no a ~967k (por sesión: `/autocompact 500k`). El mecanismo principal sigue siendo el corte por hito (4.3).
4. **Comprobar** en la próxima sesión nueva, en un worktree recién creado, que `CLAUDE.md` se carga y que aparecen `lector`, `corredor-tests` y `verificador-visual` (las sesiones abiertas antes del 01-oct no los ven hasta reiniciarse).
5. Si se edita un subagente en el repo, recopiarlo a la carpeta global (PowerShell): `Copy-Item .claude\agents\*.md $HOME\.claude\agents\ -Force`.

### 4.2 Fase 2 — Adelgazar el arranque

Hoy el protocolo de inicio pide leer `AGENTS.md` completo (15 KB), `CHECKLIST.md` (22 KB), `WORKFLOW.md` (15 KB) y el último checkpoint de `docs/checkpoints.md` (75 KB en total).

1. `AGENTS.md` y `WORKFLOW.md` → referencia por secciones (las cabeceras ya lo dicen desde la fase 0). Falta quitarles lo duplicado con `CLAUDE.md` y lo obsoleto de julio.
2. `docs/checkpoints.md` → mover lo anterior a septiembre a `docs/archive/` y dejar solo los últimos; el estado vivo pasa a `docs/frentes/`.
3. Índice de memoria (`MEMORY.md`): una línea por entrada (≤ 250 caracteres); el estado vivo va en `docs/frentes/`, no en el índice. Claude Code carga en cada sesión las primeras 200 líneas o 25 KB del índice.
4. **Memoria vieja:** cinco fotos de estado ya superadas (`estado-proyecto-sep-04/07/09/11/15`) siguen en el índice. Consolidarlas con la skill `consolidate-memory`, revisando antes lo que se va.
5. **Docs que no se tocan desde junio-agosto** (~90 KB): `PRD.md`, `walkthrough.md`, `system_patterns.md`, `architecture_design.md`, `D02_FIN_spec.md`, `module_08_project_hub.md`, `conexion_bd_guia.md`, `design_system.md`, `remediacion_2026-07.md`. Revisar cuáles siguen vigentes; los demás a `docs/archive/`.
6. **Reglas por ruta:** las reglas que solo aplican a una parte del código pueden ir en `.claude/rules/<tema>.md` con `paths:` en el encabezado; Claude Code las carga solo cuando trabaja con esos archivos (p. ej. reglas del bot para `fin_sys_core/bot_*.py`).
7. **Procedimientos como skills:** recetas largas que se usan de vez en cuando (deploy por Dokploy, túnel de SMS) pueden ir en `.claude/skills/`; solo cargan nombre y descripción hasta que se usan.

### 4.3 Fase 3 — Ciclo por hito y limpieza del contexto

Reemplaza a "partir archivos gigantes" (descartado el 01-oct). La idea: la sesión crece lo que la tarea pida, pero al cerrar cada hito se actualiza el estado y se suelta el tráfico de herramientas que ya no sirve.

**Ciclo** (detalle en `CLAUDE.md` §2):
1. Trabajar el hito; lo verboso va a subagentes.
2. Hito cerrado y verificado → actualizar el frente.
3. Limpiar con la herramienta que corresponda.
4. Seguir desde el frente; ampliar a la spec o al código solo si hace falta.

**Herramientas de Claude Code para soltar contexto** (documentación oficial, consultada el 01-oct):

| Herramienta | Qué hace | Cuándo |
|---|---|---|
| `/clear` | Deja el contexto en cero; la conversación queda en `/resume`. `CLAUDE.md` y memoria se recargan | Hito cerrado y el siguiente arranca bien desde el frente |
| `/rewind` (Esc Esc) → "Summarize from here" | Condensa solo desde un punto en adelante; lo anterior queda intacto | Cerrar un hito largo sin perder el contexto previo |
| `/rewind` → "Restore conversation" | Vuelve la conversación a un punto anterior sin tocar el código | Descartar un camino de diagnóstico que no llevó a nada |
| `/compact <foco>` | Condensa todo guiado por el foco y por "Compact Instructions" de `CLAUDE.md` | Seguir en la misma línea pero con el contexto ya pesado |
| `/context` | Muestra qué ocupa el contexto (memoria, herramientas, skills, mensajes) | Diagnóstico |
| Automático | Cerca del límite, Claude Code borra primero resultados viejos de herramientas y luego condensa | Solo ocurre cerca del límite: no reemplaza al ciclo |

**Propuestas pendientes de aprobación de Andrés:**
- **Hook `SessionStart`** (eventos `clear` y `compact`): tras limpiar, inyecta automáticamente la lista de frentes activos con su próximo paso, para retomar sin buscar. Va en `.claude/settings.json` del proyecto y un script corto. No existe un evento documentado *antes* de compactar, así que el frente se sigue actualizando a mano en el paso 2.
- **Red de seguridad** de compactación a ~500k (4.1, paso 3).

### 4.4 Fase 4 — Medir

`.venv\Scripts\python.exe scripts\medir_consumo_claude.py --dias 14`

| Indicador | Línea base (30-sep) | Meta |
|---|---|---|
| Contexto medio por turno (el indicador principal) | ~370.000 | < 150.000 |
| Tokens releídos de caché en 14 días | ~2.100 M (mitad de 30 días) | < 900 M |
| Sesiones que pasan de 700.000 | 5 de 18 | 0, salvo una tarea grande justificada |
| Peso del navegador en la sesión principal | 40% | < 10% (lo absorbe `verificador-visual`) |
| Subagentes con modelo barato | 0 | uso habitual en tests, lecturas y verificación visual |

No hay meta de contexto *pico*: una tarea grande puede necesitar mucho contexto. Lo que debe bajar es el contexto *medio*, que es lo que se paga en cada turno.

### 4.5 Fase 5 — Revisor externo (solo si hace falta)

Criterio de entrada: tras las fases 1-4 se sigue agotando la cuota con frecuencia, o se quiere una revisión independiente antes de despliegues grandes.

- Forma mínima: un script (`scripts/segunda_opinion.py`) que envíe un diff a otro modelo y devuelva hallazgos. Sin MCP de terceros.
- Solo lectura, sin `.env` ni credenciales, nunca escribe en el repo.
- Antes de elegir proveedor: investigar precios, calidad en código y términos de uso de suscripciones (pendiente; la investigación del 30-sep no lo cubrió).
