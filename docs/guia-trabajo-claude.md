# Guía de trabajo con Claude — síntesis, manual y plan

> Las reglas del día a día están en `CLAUDE.md` (raíz), que se carga solo en cada sesión.
> Este documento resume **por qué** se trabaja así, **cómo se usa** el kit y el **plan** con su avance.
> Creado el 01-oct-2026 a partir de la investigación del 30-sep y las decisiones de Andrés del 01-oct.

## 1. En una página

- **Problema:** cada sesión gastaba más a medida que crecía el proyecto. Medido: 4.450 M tokens en 30 días, el 96% por **reenviar el contexto acumulado en cada turno** de sesiones muy largas (hasta 960k). El tamaño del repo y el modelo pesan poco.
- **Idea inicial descartada por ahora:** orquestar otros modelos (Kimi, Hermes, ChatGPT/Codex) por un MCP propio. Multiplica el consumo total, el código se paraleliza mal y no ataca el 96%. Queda como fase 5 opcional, solo como revisor.
- **Lo que se hace:**
  1. **Corte por hito.** La sesión crece lo que la tarea pida (sin tope fijo); al cerrar cada hito se actualiza el frente y se suelta el contexto que ya no sirve.
  2. **Subagentes baratos** para lo verboso: leer código, correr tests, verificar en el navegador.
  3. **Kit automático** dentro de cada sesión: hooks de arranque y medidor, skill `/cerrar-hito`.
  4. **Agente de mantenimiento** diario fuera de las sesiones: prepara, revisa, mide y propone en un tablero.
- **Regla que no se mueve:** un solo agente escribe (la sesión principal). Nadie limpia ni edita desde afuera las sesiones de otro; la app tampoco lo permite.

## 2. Diagnóstico (30-sep y 01-oct-2026)

| Medida | Valor |
|---|---|
| Tokens releídos de caché en 30 días | 4.450 M (96% del volumen); salida 19 M |
| Contexto medio por turno | ~370.000 |
| Sesiones que pasaron de 700.000 | 5 de 18, y aportan el 75% del gasto |
| Base fija de cada sesión antes del primer mensaje | ~70k (herramientas 38k, MCP 16-19k, skills, memoria) |

De qué están hechos los mensajes (23,8 M caracteres):

| Parte | % |
|---|---|
| Resultados del navegador | 23% |
| Código escrito en ediciones (Edit/Write) | 19% |
| Lecturas de código | 13% |
| Salida de terminal | 11% |
| Entradas de otras herramientas | 10% |
| Conversación real (Andrés + texto y razonamiento de Claude) | 14% |
| Documentos `.md` (docs y memoria) | 2% |

El 86% es tráfico de herramientas: útil mientras dura el hito, peso muerto después. Los documentos viejos pesan poco dentro de la sesión; su costo es que se leen al arrancar y meten estado desactualizado.

## 3. Decisiones

| Decisión | Por qué |
|---|---|
| No orquestar otros modelos todavía | Investigación del 30-sep (25 afirmaciones verificadas): multiagente multiplica tokens (Anthropic ~15x vs ~4x), el orquestador debe ser el modelo más fuerte, un solo agente debe escribir; `codex mcp-server` eliminado en sep-2026 y PAL MCP sin mantenimiento |
| Sin tope fijo de contexto | Andrés, 01-oct: 200k restringe las tareas grandes. La meta es bajar el contexto *medio*, no el pico |
| No partir `bot_driver.py` / `database_driver.py` | Andrés, 01-oct: el problema es arrastrar hitos cerrados, no el tamaño de los archivos |
| Corte por hito + frentes | El 86% del contexto es tráfico de herramientas que deja de servir al cerrar el hito |
| Kit instalado a nivel de usuario | Llega a todas las instancias aunque el worktree nazca de `main` vacía; solo actúa en este proyecto |
| Agente de mantenimiento solo lee y propone | La BD es la de producción, un solo escritor, y la app no deja tocar sesiones ajenas |

## 4. Arquitectura

```
              ┌──────────── Agente de mantenimiento (tarea programada, 10 pm) ────────────┐
              │ semáforo de sesiones · medición · git/producción · frentes · specs ·       │
              │ salud (solo lectura + tests puros del CI) · propuestas de memoria y docs   │
              └───────────────────────────────┬────────────────────────────────────────────┘
                                              │ escribe
                                              ▼
                                   scratch/tablero.md  ◄── lo lee el hook de arranque
                                              │
  Cada sesión de trabajo (cualquier instancia) ▼
  ┌──────────────────────────────────────────────────────────────────────────────────────┐
  │ CLAUDE.md (reglas) · hook de arranque (frentes + tablero) · hook medidor (avisos)    │
  │ Sesión principal = orquestador y único escritor                                      │
  │   ├─ lector (Haiku) · corredor-tests (Haiku) · verificador-visual (Sonnet)           │
  │   └─ /cerrar-hito → verifica · commit · frente · mide · limpia (clic de Andrés)      │
  └──────────────────────────────────────────────────────────────────────────────────────┘
                     docs/frentes/<nombre>.md = traspaso entre hitos y sesiones
```

| Pieza | Dónde vive | Qué hace |
|---|---|---|
| `CLAUDE.md` | raíz del repo | Reglas de sesión; se carga solo, también en los worktrees (lee los `CLAUDE.md` de las carpetas padre) |
| Hook de arranque | `~/.claude/hooks/finsys/arranque.py` (fuente: `scripts/claude_kit/`) | Al iniciar, tras `/clear` y tras compactar: frentes activos + resumen del tablero + aviso si el worktree está vacío |
| Hook medidor | `~/.claude/hooks/finsys/medidor.py` | En cada mensaje calcula el contexto desde la transcripción; desde 350k avisa una vez por tramo de 100k |
| Skill `/cerrar-hito` | `~/.claude/skills/cerrar-hito/` (fuente: `.claude/skills/`) | Verificar → commit → frente → medir → limpiar |
| Subagentes | `~/.claude/agents/` (fuente: `.claude/agents/`) | Lectura, tests y verificación visual fuera del contexto principal |
| Frentes | `docs/frentes/` | Estado de cada línea de trabajo; se sobrescribe (≤60 líneas) |
| Agente de mantenimiento | tarea programada `mantenimiento-finsys` (fuente: `scripts/claude_kit/mantenimiento.md`) | Tablero diario en `scratch/tablero.md` + historial en `scratch/medicion-historial.csv` |
| Medición | `scripts/medir_consumo_claude.py` | Antes/después, solo lectura |

## 5. Manual de uso diario

1. **Abrir sesión** (cualquier instancia o worktree). El hook te muestra los frentes activos y el resumen del tablero. Di en qué frente se trabaja; la sesión lee solo ese frente.
   - Si avisa que el worktree está vacío, la sesión hace `git reset --hard master` antes de nada.
2. **Trabajar el hito.** La sesión delega a los subagentes lo verboso. Tú solo apruebas planes y cambios, como siempre.
3. **Si llega el aviso del medidor** (desde ~350k), la sesión te lo dice en una línea:
   - Si el hito ya está cerrado → `/cerrar-hito`.
   - Si va a mitad de un hito → seguir; el aviso no vuelve hasta el siguiente tramo de 100k.
4. **Cerrar el hito:** escribe `/cerrar-hito` (o la sesión lo propone). Verifica, commitea, actualiza el frente y te pide un clic para limpiar.
   - Si el siguiente hito depende de detalles finos de este, en vez de limpiar usa `/compact <qué conservar>` o Esc Esc → "Summarize from here" desde el inicio del hito.
   - Para descartar un camino de diagnóstico que no llevó a nada: Esc Esc → "Restore conversation".
5. **Seguir.** Tras limpiar, el hook vuelve a mostrar los frentes; la sesión retoma desde el frente.
6. **Push y deploy:** como siempre, los haces tú (`git push origin <rama>:master`, luego el deploy por script).
7. **Cada día, después de las 10 pm,** el tablero queda actualizado. Revisa la sección "Propuestas" y aprueba lo que quieras aplicar (consolidar memoria, archivar docs, cerrar frentes) en una sesión de trabajo.
8. **Cada semana:** mira la línea "Tendencia" del tablero o corre `.venv\Scripts\python.exe scripts\medir_consumo_claude.py --dias 7`.

## 6. Repercusiones

**Qué cambia para ti**
- Más cortes: cada hito termina con `/cerrar-hito` y un clic para limpiar. A cambio, cada turno siguiente pesa mucho menos.
- La memoria de trabajo vive en `docs/frentes/`, y su calidad depende de cómo se escriba el frente. Un frente pobre obliga a releer.
- Recibes una notificación diaria del agente de mantenimiento, y propuestas para aprobar.

**Costos**
- Hooks: ~0,2 s por mensaje (medido) y unas pocas líneas de contexto al arrancar. El medidor no agrega nada hasta los 350k.
- Agente de mantenimiento: una corrida diaria que gasta de tu plan; lee con Haiku y escribe un tablero corto. Se verá su costo en la medición de la primera semana.
- `/cerrar-hito`: un subagente de tests y unas líneas de frente por hito; mucho menos que arrastrar el hito en cada turno.

**Riesgos y cómo se cubren**
- *Limpiar con trabajo a medias:* la skill se detiene si el hito no está verificado, y la limpieza siempre pide tu clic. Una conversación limpiada se recupera con `/resume`.
- *Tests sobre la BD de producción:* el agente de mantenimiento solo corre `health_check.py` (solo lee), `session_maintenance.py --check` y los tests puros del CI (conexiones simuladas, vigiladas por `tests.test_mock_policy`).
- *Hooks a nivel de usuario:* corren en todas tus sesiones de cualquier proyecto, pero salen de inmediato si la carpeta no es `contabilidadprogram`. Si fallan, no estorban: están escritos para callar ante un error.
- *Tarea programada:* solo corre con la app abierta; si a las 10 pm está cerrada, corre al abrirla. En la primera corrida puede pedir permisos: conviene lanzarla una vez con "Run now" para aprobarlos.
- *Desfase entre repo y `~/.claude`:* si se edita una pieza en el repo, hay que reinstalar (sección 7). `instalar.py --check` muestra qué difiere.

**Cómo deshacer**
- Kit: `python scripts/claude_kit/instalar.py --desinstalar` (quita hooks y skill; deja respaldo de `settings.json`).
- Tarea programada: desactivarla o borrarla en "Scheduled" de la barra lateral.
- `CLAUDE.md` y frentes: `git revert` de los commits de la guía.

## 7. Instalación y mantenimiento del kit

```
python scripts/claude_kit/instalar.py            # instala o actualiza (con respaldo de settings.json)
python scripts/claude_kit/instalar.py --check    # qué difiere entre el repo y ~/.claude
python scripts/claude_kit/instalar.py --desinstalar
```

- Instalado el 01-oct-2026 en este PC. Respaldo previo: `~/.claude/settings.json.bak-20261001-154957`.
- Las sesiones abiertas antes de instalar no ven los hooks, la skill ni los subagentes hasta reiniciarse.
- Umbral del medidor: variables de entorno `FINSYS_CTX_AVISO` (por defecto 350000) y `FINSYS_CTX_PASO` (100000).
- La tarea programada se creó desde una sesión de Claude con el texto de `scripts/claude_kit/mantenimiento.md`. Si se cambia ese archivo, hay que actualizar la tarea.

## 8. Plan y avance

| Fase | Qué | Quién | Estado |
|---|---|---|---|
| 0 | `CLAUDE.md`, subagentes, `docs/frentes/`, script de medición, cabeceras de `AGENTS.md`/`WORKFLOW.md`/`CHECKLIST.md` | Claude | HECHO 01-oct |
| 1 | Que la guía llegue a todas las instancias (8.1) | Andrés | PENDIENTE: push y rama por defecto |
| 2 | Adelgazar lo que se lee al arrancar (8.2) | Claude, con aprobación | PENDIENTE (el tablero irá proponiendo) |
| 3 | Corte por hito + kit automático + agente de mantenimiento | Claude | HECHO 01-oct (falta probar en sesión nueva) |
| 4 | Medir a la semana y a las dos semanas (8.3) | agente de mantenimiento + Claude | EN CURSO (diario) |
| 5 | Revisor externo, solo si la fase 4 lo justifica (8.4) | Decide Andrés | EN ESPERA |
| 6 | Herramientas especializadas de construcción (sección 9) | Claude, con aprobación | HECHO 06-oct (los 5 del catálogo) |

### 8.1 Fase 1 — Pendiente de Andrés
1. Push de la rama de la guía: `git push origin claude/multi-model-mcp-orchestration-3d985e:master`; luego `git pull --ff-only` en el checkout principal.
2. Rama por defecto de GitHub = `master` (Settings → General → Default branch) y `git remote set-head origin -a`. Antes, confirmar que Dokploy despliega `master` por nombre.
3. En "Scheduled", lanzar una vez `mantenimiento-finsys` con "Run now" y aprobar los permisos que pida.
4. Abrir una sesión nueva y comprobar: el hook de arranque muestra frentes y tablero; aparecen `lector`, `corredor-tests`, `verificador-visual` y `/cerrar-hito`.
5. Opcionales: red de seguridad de compactación (`CLAUDE_CODE_AUTO_COMPACT_WINDOW=500000` en el `env` de `~/.claude/settings.json`), desactivar en este proyecto los MCP que no se usan (baja la base de ~70k), y `.worktreeinclude` con `.env`.

### 8.2 Fase 2 — Adelgazar el arranque (el tablero lo irá proponiendo)
1. `AGENTS.md` y `WORKFLOW.md`: quitar lo duplicado con `CLAUDE.md` y lo obsoleto de julio.
2. `docs/checkpoints.md` (75 KB): mover lo anterior a septiembre a `docs/archive/`.
3. Memoria: consolidar las 5 fotos `estado-proyecto-sep-*` (skill `consolidate-memory`, revisando antes).
4. Docs sin tocar desde junio-agosto (~90 KB): revisar vigencia y archivar.
5. Reglas que solo aplican a una parte del código → `.claude/rules/<tema>.md` con `paths:` (se cargan solo al tocar esos archivos). Recetas largas (deploy, túnel de SMS) → skills.

### 8.3 Medición

| Indicador | Línea base (30-sep) | Meta a dos semanas |
|---|---|---|
| Contexto medio por turno (el principal) | ~370.000 | < 150.000 |
| Tokens releídos en 7 días | ~1.050 M (proporcional) | < 450 M |
| Sesiones que pasan de 700.000 | 5 de 18 en 30 días | 0, salvo una tarea grande justificada |
| Peso del navegador en la sesión principal | 40% | < 10% |
| Subagentes con modelo barato | 0 | uso habitual |

No hay meta de contexto *pico*: una tarea grande puede necesitarlo. Lo que debe bajar es el *medio*, que es lo que se paga en cada turno.

### 8.4 Fase 5 — Revisor externo (solo si hace falta)
Si tras dos semanas se sigue agotando la cuota, o se quiere una revisión independiente antes de despliegues grandes: un script `scripts/segunda_opinion.py` que envíe un diff a otro modelo (Codex, Kimi…) y devuelva hallazgos. Solo lectura, sin `.env`, sin MCP de terceros. Antes, investigar precios, calidad en código y términos de uso (no lo cubrió la investigación del 30-sep).

## 9. Herramientas especializadas de construcción (investigación del 01-oct-2026)

Investigación profunda con 26 fuentes y 25 afirmaciones verificadas (21 confirmadas, 4 refutadas), más inspección del repo y medición local. Estado: **los 5 HECHOS el 06-oct** (guardia, lint crítico en hook y CI, `auditor-spec`, `/desplegar`, permisos).

**Principio.** El proceso mejora menos por sumar agentes que por dos cosas:
1. Convertir las reglas no negociables en mecanismos que se cumplen solos (hooks `PreToolUse`, reglas de permisos). Una regla en `CLAUDE.md`, en una skill o en el prompt de un subagente es una petición; un hook o un permiso lo hace cumplir Claude Code. Límites: los hooks fallan abiertos (si el script falla, la acción sigue) y actúan por llamada de herramienta (un `.py` escrito y luego ejecutado puede esquivarlos).
2. Pocos agentes bien acotados, creados cuando un disparador se repite, con una descripción que diga **cuándo** actuar, herramientas restringidas y modelo explícito.

**Qué pieza usar para qué** (documentación oficial):

| Pieza | Cuándo |
|---|---|
| `CLAUDE.md` / `.claude/rules/` | Lo que debe saberse siempre (un error que se repite dos veces) |
| Skill | Un procedimiento que se repite (el mismo pegado por tercera vez). Con `disable-model-invocation: true` si tiene efectos (deploy) |
| Subagente | Tarea lateral con salida voluminosa, o para restringir herramientas |
| Hook | Lo que debe pasar siempre, sin pedirlo |
| Plugin | Empaquetar para otra máquina u otro repo |

**Catálogo priorizado:**

| # | Pieza | Tipo | Qué hace | Estado |
|---|---|---|---|---|
| 1 | `guardia` | Hook `PreToolUse`, script sin modelo | Bloquea `git push`, `session_maintenance.py` sin `--check`, `bot_telegram.py` local, `scripts/migrate_*.py`, SQL de escritura en comandos, `.env` y la API de Dokploy fuera de `deploy_prod.py`; pide confirmación para `database_driver.py` y `control_tower_driver.py`; registra en `scratch/guardia.log` | HECHO 06-oct (`scripts/claude_kit/guardia.py`, 15 tests en `tests/test_claude_kit.py`) |
| 2 | `lint-al-editar` | Hook `PostToolUse` | ruff (errores graves) en `.py` y eslint en `.js`/`.jsx` del archivo recién editado; devuelve los errores a Claude. Además, ruff y `npm run lint` en el CI | HECHO 06-oct (`scripts/lint_critico.py` + hook; en el CI: ruff E9/F63/F7/F82 y eslint solo reglas graves — el lint de estilo tiene 191 errores viejos y no bloquea) |
| 3 | `auditor-spec` | Subagente Sonnet, solo lectura | Antes de marcar una etapa HECHA: cada `CA-` → CUMPLE / FALTA / SIN EVIDENCIA con `archivo:línea`, y casos borde sin test | HECHO 06-oct (`.claude/agents/auditor-spec.md`; prueba con la spec 13.4: halló 2 CA manuales en vez de 1, 6 casos borde sin test y texto desactualizado; ~200k tokens de Sonnet por auditoría → una vez por etapa) |
| 4 | `/desplegar` | Skill que solo invoca Andrés | Chequeos previos (git limpio, `origin/master` = HEAD, CI en verde) → `deploy_prod.py` → sondas → línea para el frente | HECHO 06-oct (`.claude/skills/desplegar/SKILL.md`; adaptada a `publicar.cmd`: Claude prepara y verifica, Andrés publica) |
| 5 | Ajustes | — | `verificador-visual` sin Bash/PowerShell y descripciones con "cuándo" (HECHO 01-oct). Quitados `git push *` y `python -c ' *` de `.claude/settings.local.json` (06-oct) | HECHO |

**Adoptar de terceros (copiar después de leer; no instalar colecciones):**
- `systematic-debugging` y `verification-before-completion` de Superpowers (obra/superpowers, MIT, marketplace oficial, mantenido). Trae telemetría activa por defecto (`SUPERPOWERS_DISABLE_TELEMETRY` la apaga). Sus skills de git y worktrees chocan con las reglas de este repo.
- `/code-review` y `/security-review` integrados antes del push en cambios de auth o de dinero, en vez de crear revisores propios.
- Evaluar un plugin LSP para Python y JavaScript (señal: `bot_driver.py` releído 45 veces en 14 días), revisando antes su costo de contexto por turno.

**No hacer:**
- Instalar colecciones grandes de agentes o skills: más de 15k tokens de descripciones disparan una advertencia y la delegación se vuelve menos fiable.
- Confiar la seguridad a `permissionMode` (se ignora si la sesión está en auto, bypass o acceptEdits), al texto de un prompt o a `disallowedTools` con especificador (quita la herramienta entera).
- Usar `isolation: worktree` mientras `main` esté vacía; bajar Explore a Haiku para ahorrar (pesa ~1% del gasto).
- Crear agentes para dependencias, APM o documentación: mejor herramientas deterministas (dependabot, `pip-audit`, `npm audit`) o el agente de mantenimiento.
- Instalar sin revisión plugins con hooks o MCP: corren con tus privilegios y fuera del sandbox; en Windows no hay sandbox integrado. Un escaneo de Snyk (feb-2026) halló problemas críticos en el 13% de casi 4.000 skills públicas.

**El dato que más pesa: el modelo de la sesión principal.** En 14 días, el 90% del contexto releído corrió en Fable 5 (51%) y Fable 5.1 (40%); Opus 5.5, solo el 1%. Lectura de caché por millón de tokens (precios de lista al 25-sep-2026; la cuota del plan puede contar distinto): Fable 5 US$1,00 · Fable 5.1 US$0,25 · Opus 5.5 US$0,20 · Sonnet 5.5 US$0,20. Entrada/salida: Fable US$10/50, Opus 5.5 US$4/20, Sonnet 5.5 US$2/10, Haiku 4.5 US$1/5 (ventana de 200k). Recomendación: no abrir sesiones nuevas en Fable 5; Opus 5.5 por defecto y Fable 5.1 para lo más difícil. Cambiar de modelo invalida la caché, así que conviene hacerlo justo después de `/cerrar-hito`.

**Cómo medir cada pieza:** extender `medir_consumo_claude.py` para contar invocaciones de skills y bloqueos de la guardia; retirar lo que no se use en 14 días; para cada skill o agente, 10-20 prompts que deberían dispararlo y otros que no, corridos con y sin la pieza (`claude plugin eval` o skill-creator).

**Preguntas abiertas:** cómo hacer real "nada escribe en la BD" si los hooks fallan abiertos (rol de Postgres de solo lectura para las sesiones, proyecto Supabase aparte para tests, credenciales separadas para migraciones); si un `ask` de `PreToolUse` sigue pidiendo confirmación en modo auto en la app de escritorio; si las skills de diseño (Impeccable, Taste, Claude Design) aportan a un ERP interno (sin evidencia verificada).
