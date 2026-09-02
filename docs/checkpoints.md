# Checkpoints — FIN-SYS OS v2.0

---

## Checkpoint 2026-08-21 — Revisión de estado (sin código nuevo)

**Fase**: Módulo 09 (Bot IA) en MVP funcional + Módulo 01 (Registro) completado.
**Riesgo abierto**: todo eso vive SOLO en la rama `modulo-09-bot-ia` y NO está en `master` ni en producción.

### Dónde está el trabajo
- `master` / `origin/master` = `64badb6` (29 jul). **Producción sirve esto** (responde 200).
- `modulo-09-bot-ia` = `f5559f7` (10 ago) — **7 commits adelante de master, sin merge**:
  - `49e9626` COA: reglas EGRESO→GASTO + fallback ingreso 4120→417505
  - `591907b` **Módulo 09 MVP Telegram** — borradores persistentes + confirmación determinista (`bot_driver.py`, `bot_telegram.py`, `routers/bot.py`, `transaction_service.py`, migración de tablas, 3 suites de tests)
  - `39e96a7` bot: tipos UUID, portafolio real, método de pago dicho por el usuario (`scripts/bot_link_code.py`)
  - `151b33d` voz web ⇄ bot unificados sobre `draft_builder.py`; asiento en procesos externos; `scripts/repair_missing_journal.py`
  - `f5be434` impuestos solo con autorización humana + Módulo 01 completo (`AdvancedSections.jsx`)
  - `e8692b7` registro+consolidado: etiquetas por industria, `AccountsPulse`, menos ruido
  - `f5559f7` cuentas: saldo inicial editable + pulso con movimientos reales y descuadres

### WIP sin commit (⚠️ NO descartar — hay código commiteado que depende de él)
| Archivo | Qué aporta | Por qué es crítico |
|---|---|---|
| `fin_sys_core/org_driver.py` | `get_consolidated_by_entity()` — cifras reales por entidad, agregación jerárquica sin duplicar portafolios; `portfolio_id` editable en `update_entity_basic` | `DashboardPanel.jsx` **ya commiteado** llama `GET /api/org/consolidated` |
| `routers/org.py` | endpoint `/api/org/consolidated` + `exclude_unset` (permite desvincular con `null`) | **El endpoint no existe en HEAD** → desplegar la rama hoy = 404 y panel de empresas roto |
| `routers/cartera.py` | `cxc_total`, `cxp_total`, `vencido_total`, `proximo_total` en `/api/cartera/summary` | fix TC021 (Cartera mostraba `$NaN`) |
| `TercerosTab.jsx` | botón "✓ Crear Tercero" | fix TC025; su helper `createItem` **ya está commiteado** en `ContextPanel.jsx` |
| `CarteraKpiBar.jsx` | fallback `Number(k.value \|\| 0)` | defensa anti-NaN |
| `.gitignore` | ignora `testsprite_tests/tmp/config.json` | higiene |

Sin trackear: `docs/PRD.md` (fuente de verdad de negocio, 29 jul) y `testsprite_tests/` (30 casos + reporte).

### TestSprite — última corrida (29 jul, 30/50 casos)
✅ 25 · ❌ 5 → **83.33%**. De los 5 fallos: 1 falso positivo (KPIs CT), 2 corregidos (TC021, TC025 — los fixes son parte del WIP de arriba), 1 vacío de datos (TC003, entidades CT sin `portfolio_id`), 1 brecha de spec (TC022, Libro Diario sin buscador).
Datos de prueba que quedaron en la BD real: 2 TX `TS-TEST-Ingreso automatizado` + 1 tarea `TS-TEST-Prepare monthly review`.

### Estado BD (health_check en vivo, 21 ago 16:57 COT)
`transactions` 13 · `entities` CT 6 · `user_accounts` 5 · `portfolios` 4 · Motor IVA=19.000 GMF=400 ✓ · Sin anomalías de integridad.
Servicios locales: ❌ frontend :5173 · ❌ backend :8000 · ✅ Supabase · ✅ prod :8080.

### Ejecutado en esta misma sesión (tras la revisión)

**1. WIP commiteado** — `bc86acf feat(consolidado)+fix(cartera,terceros)` y
`4895324 docs: estado real del proyecto al 21 ago`. Árbol limpio. El desfase
frontend↔backend quedó cerrado. Se verificó antes: `py_compile` de los 3 módulos
tocados y `python -m kernel.test_kernel` → 5/5.

**2. Merge a `master` hecho en local** (fast-forward, `master` = `4895324`).
⚠️ **El `git push origin master` quedó pendiente**: el clasificador de permisos lo
bloqueó al agente. Sin push no hay deploy — producción sigue en `64badb6` (29 jul).

**3. Vinculación entidad ↔ portafolio (gap #1 de TestSprite, TC003) — RESUELTA.**
Se descubrió que `URBANIZACION BONAIRE` ya estaba vinculada a `Negocio A` (el reporte
del 29 jul decía que ninguna lo estaba; el dato cambió después). Andrés decidió el resto:

| Entidad | Portafolio | Nota |
|---|---|---|
| Mi Holding Principal (1) | Negocio Principal (4) | — |
| GRUPO EMPRESARIAL PEGASUS SAS (14) | EMPRESA INFANTIL PEGASUS (2) | el preescolar hereda por agregación |
| URBANIZACION BONAIRE (17) | Negocio A (1) | ya existía |
| CONSTRUCTORA BLU SAS (16), PRESCOLAR PEGASUS SAS (15), IMPORTEX AMARU (18) | — | sin vincular a propósito (muestran "sin vincular", no $0) |
| MI EMPRESA (3) | — | portafolio vacío, sin dueño claro |

Verificado con `get_consolidated_by_entity()`: el holding agrega su subárbol
(`ing=1.400.000 · gas=2.799.500 · bal=-1.399.500`) sin contar dos veces el mismo
portafolio; totales = las cifras del único portafolio con movimientos. 3 vinculadas /
3 sin vincular. **El panel de empresas ya no muestra $0.**

**4. Datos `TS-TEST-*` eliminados de la BD real.** 2 transacciones (id 5 y 6), sus 4
asientos del kernel (`TX-5`, `TX-6`, pares cuadrados) y 1 tarea del Hub. Los saldos se
revirtieron con la misma función de la app (`revertir_delta_incremental`), no a mano:
Efectivo $1.750.000 → $1.500.000 · Bancolombia $1.150.000 → $1.050.000. Quedan 11
transacciones. Respaldo JSON de las filas en el scratchpad de la sesión.

**5. Limpieza y purga del repositorio.**

- **Trabajo rescatado antes de purgar**: la rama `claude/testsprite-project-testing-f23abb`
  tenía un commit que NO estaba en master (`b77df03`, refresco de `frontend/package-lock.json`
  con `@emnapi/runtime`). Se aplicó con cherry-pick (`5659c29`); verificado que el contenido
  del lock ahora es idéntico. Recién entonces la rama quedó descartable.
- **Ramas**: `modulo-09-bot-ia` eliminada (ya fusionada; el desarrollo sigue en `master`).
  Las 6 ramas `claude/*` y `gilded-mask` cuelgan de un commit raíz huérfano (`f38f62a`
  "Initial commit", solo un README, autoría `julioberne`) — **no contienen trabajo**.
- **Purgado**: 11 carpetas `__pycache__` + 108 `.pyc`, y `testsprite_tests/tmp/mcp.log`
  (3.1 MB de log). El repo sin `.venv`/`node_modules` quedó en ~14 MB de fuentes.
- **`uploads/` auditado contra la BD**: 17 archivos, 7 referenciados como evidencia por
  transacciones (los 7 presentes en disco, sin enlaces rotos) y **10 huérfanos** (8 `.webm`
  de voz web + 2 `.ogg` de Telegram, 875 KB) que ninguna transacción referencia. **No se
  borraron**: son audio real del usuario, la decisión es suya.

**Bloqueado al agente por el clasificador de permisos** (hay que correrlo a mano):
`git push origin master`, `git worktree remove`, `git branch -D` y `POST /api/compose.deploy`.

**Inconsistencia detectada, requiere decisión**: el repo de GitHub tiene `main` como rama
por defecto, pero `main` es solo el "Initial commit" vacío — **todo el proyecto vive en
`master`**. Los PRs y clones nuevos apuntan por defecto a una rama sin código.

**6. Push publicado (2026-08-24).** `git push origin master` → `64badb6..2866be8`, 12 commits.
`origin/master` y `master` sincronizados, 0 pendientes.

**El webhook de Dokploy NO disparó — tercera vez (DT-10).** Hubo que desplegar a mano desde
el panel :3000. El token de `scratch/dokploy.env` además responde **401** en
`GET /api/deployment.allByCompose` (revocado o rotado): la vía API necesita una key nueva.

**7. PRODUCCIÓN AL DÍA (2026-08-24 · verificado en vivo).**
`Last-Modified: Mon, 24 Aug 2026 03:47` (antes 29 jul) · `GET /api/org/consolidated` → **200**
(antes 404) · `GET /api/cartera/summary` → 200. El consolidado responde en producción con la
vinculación real: holding `bal=-1.399.500` agregando su subárbol, 3 entidades vinculadas y 3
mostrando "sin vincular". **Las tres semanas de trabajo llegaron a producción.**

**8. Limpieza de git — parcial.** Borradas la rama remota
`origin/claude/testsprite-project-testing-f23abb` y las locales
`claude/admin-dashboard-user-credentials` e `claude/ia-bot-whatsapp-telegram`. Los 4 worktrees
obsoletos **siguen ahí**: `git worktree remove` falla sin `--force` cuando el worktree tiene
archivos sin trackear, y mientras existan no se pueden borrar sus 4 ramas.

### Pendiente al cierre
1. Borrar los 4 worktrees obsoletos con `--force` y después sus 4 ramas (DT-18).
2. Cambiar la rama por defecto de GitHub a `master`: sigue en `main`, que está vacía
   (`origin/HEAD -> origin/main`) — DT-17.
3. Re-correr TestSprite sobre el build nuevo (y avanzar TC031–TC050).
4. Buscador del Libro Diario (TC022) · normalizar upsert de `module_flags` (DT-12).
5. **DT-19 cerrada**: los 10 audios huérfanos se conservan. Ojo para el futuro — las 7
   evidencias sí referenciadas son todas `.ogg` de Telegram, así que **nunca** borrar por
   patrón en `uploads/`.

---
## Checkpoint 2026-07-13 — Sesión 02:43 COT

**Estado**: ⚠️ Servicios locales caídos | BD + motor OK | Contabilidad v2 WIP

### Trabajo Completado Esta Sesión:
- **Documentación de estado** — `docs/estado_proyecto_13jul2026.md` creado (panorama completo)
- **activeContext.md** actualizado — foco Contabilidad v2, health check en vivo
- **Health check ejecutado** — 15 TXs, 5 cuentas (alerta: esperado 7), frontend/backend caídos

### WIP sin commit (Contabilidad v2):
- `TransactionDraftProvider.jsx` — borrador global de transacciones
- `RegistroForm.jsx` — formulario Módulo 01 desacoplado
- `ContabilidadApp.jsx`, `TercerosPanel.jsx`, `contabilidad-v2.css`

### Estado BD al Cierre (health_check en vivo):
- Transacciones: **15** (antes documentado: 13)
- Entidades CT: 13
- Cuentas bancarias: **5** (alerta integridad — esperado: 7)
- Frontend/Backend: caídos en momento del check

### Próxima Sesión — Opciones:
1. **Opción E** — Cerrar Contabilidad v2 Fase 2 (unificar API, paridad form, commit)
2. Arrancar servicios y re-ejecutar health_check completo (CT + Hub)
3. Investigar cuentas bancarias faltantes (5 vs 7)
4. Módulo 09 Bot IA / Módulo 10 Trading / Limpieza técnica

### Archivos NO tocados esta sesión:
- App.jsx, control-tower/*, database_driver.py, control_tower_driver.py, .env

**Referencia:** `docs/estado_proyecto_13jul2026.md`

---

## Checkpoint 2026-07-05 — Sesión 19:09 COT

**Estado**: ✅ Sistema operativo | Módulo 08c RRHH activo

### Trabajo Completado Esta Sesión:
- **Menú lateral**: "RRHH" renombrado a "EMPRESAS"
- **CompanyMapTab**: árbol jerárquico Holding→Empresa→Subsidiaria→Proyecto (add/edit/delete)
- **DocumentsTab**: drive-style, categorías persistentes, preview HTML comprobantes
- **HistorialTab**: pestaña separada, totales nómina, generación comprobantes
- **Fix upload comprobante**: usa `supabase.storage.from('hr-docs').upload()` JS directo
- **Fix mime type**: `application/octet-stream` (Supabase bloquea text/html)
- **Fix FileCard**: ícono 🧾 COMPROBANTE para vouchers, descarga blob-based
- **Fix parse error**: llave cierre faltante en HistorialTab.jsx

### Estado BD al Cierre:
- Transacciones: 13
- HR Members: N/A
- HR Payments: 13
- HR Docs: 6 (docs test eliminados previo)
- Total tablas: 37

### Próxima Sesión — Opciones:
1. Probar flujo completo comprobante → ver en Documentos
2. Integración contabilidad-nómina (DT-08)
3. Módulo 09 — Bot IA (Groq + WhatsApp)
4. Módulo 10 — Trading NASDAQ

### Archivos NO tocados esta sesión:
- App.jsx, control-tower/*, database_driver.py, control_tower_driver.py, .env


---

## Checkpoint 2026-06-27 — Sesión 23:30 COT

**Estado**: ✅ Sistema operativo | Refactor 6 fases COMPLETADO

### Trabajo Completado:
- **Refactor monolíticos** → 5,957 ln split en ~32 archivos (−74%)
- **App.jsx**: 1,999 → 717 ln (TransactionForm, LibroDiario, EvidenceModal extraídos)
- **ContextPanel**: 1,249 → 217 ln (7 tabs)
- **InventoryPanel**: 866 → 210 ln (5 archivos)
- **DocumentsTab**: 932 → 456 ln (8 archivos)
- **contabilidad.py**: 911 → 0 ln (7 routers: portfolios, transactions, profile_accounts, coa, dashboard_data, tags_taxes, schemas)
- **Fix**: entity→portfolio bridge (no pisar portfolio activo)
- **Limpieza**: contabilidad_OLD.py, __pycache__, scratch scripts

### Estado BD al Cierre:
- Transacciones: 12
- Portafolios: 4
- Entities CT: 13
- Total tablas: ~36
- Total endpoints: ~100 (14 routers)

### Verificación:
- Vite build: ✓ 4.25s (1,432 módulos)
- Backend: ✓ Application startup complete
- API dashboard-data: ✓ 12 transacciones

---

## Checkpoint 2026-06-20 — Sesión 19:57 COT

**Estado**: ✅ Sistema operativo | Módulo 08c RRHH activo

### Trabajo Completado Esta Sesión:
- **Menú lateral**: "RRHH" renombrado a "EMPRESAS"
- **CompanyMapTab**: árbol jerárquico Holding→Empresa→Subsidiaria→Proyecto (add/edit/delete)
- **DocumentsTab**: drive-style, categorías persistentes, preview HTML comprobantes
- **HistorialTab**: pestaña separada, totales nómina, generación comprobantes
- **Fix upload comprobante**: usa `supabase.storage.from('hr-docs').upload()` JS directo
- **Fix mime type**: `application/octet-stream` (Supabase bloquea text/html)
- **Fix FileCard**: ícono 🧾 COMPROBANTE para vouchers, descarga blob-based
- **Fix parse error**: llave cierre faltante en HistorialTab.jsx

### Estado BD al Cierre:
- Transacciones: 6
- HR Members: N/A
- HR Payments: 13
- HR Docs: 6 (docs test eliminados previo)
- Total tablas: 34

### Próxima Sesión — Opciones:
1. Probar flujo completo comprobante → ver en Documentos
2. Integración contabilidad-nómina (DT-08)
3. Módulo 09 — Bot IA (Groq + WhatsApp)
4. Módulo 10 — Trading NASDAQ

### Archivos NO tocados esta sesión:
- App.jsx, control-tower/*, database_driver.py, control_tower_driver.py, .env


---

## Checkpoint 2026-06-20 — Sesión 01:51 COT

**Estado**: ✅ Sistema operativo | Módulo 08c RRHH activo

### Trabajo Completado Esta Sesión:
- **Menú lateral**: "RRHH" renombrado a "EMPRESAS"
- **CompanyMapTab**: árbol jerárquico Holding→Empresa→Subsidiaria→Proyecto (add/edit/delete)
- **DocumentsTab**: drive-style, categorías persistentes, preview HTML comprobantes
- **HistorialTab**: pestaña separada, totales nómina, generación comprobantes
- **Fix upload comprobante**: usa `supabase.storage.from('hr-docs').upload()` JS directo
- **Fix mime type**: `application/octet-stream` (Supabase bloquea text/html)
- **Fix FileCard**: ícono 🧾 COMPROBANTE para vouchers, descarga blob-based
- **Fix parse error**: llave cierre faltante en HistorialTab.jsx

### Estado BD al Cierre:
- Transacciones: 4
- HR Members: N/A
- HR Payments: 13
- HR Docs: 6 (docs test eliminados previo)
- Total tablas: 32

### Próxima Sesión — Opciones:
1. Probar flujo completo comprobante → ver en Documentos
2. Integración contabilidad-nómina (DT-08)
3. Módulo 09 — Bot IA (Groq + WhatsApp)
4. Módulo 10 — Trading NASDAQ

### Archivos NO tocados esta sesión:
- App.jsx, control-tower/*, database_driver.py, control_tower_driver.py, .env


---

## Checkpoint 2026-06-19 — Sesión 23:18 COT

**Estado**: ✅ Sistema operativo | Fase 1+2 Performance COMPLETADAS

### Trabajo Completado (Sesión Performance):
- **SOL-01**: Cálculo incremental O(1) — TX 10x más rápido
- **SOL-02**: Connection pool centralizado — 4/4 drivers migrados (incluye control_tower_driver.py)
- **SOL-04A**: Endpoint consolidado `/api/dashboard-data` — 60% más rápido (3,078ms → 1,216ms)
- **SOL-05**: Cache TTL (perfil 5min, portafolios 2min, COA 5min) + invalidación automática en 4 writes
- **SOL-06**: Code splitting React.lazy + manualChunks — 99% reducción bundle inicial (578KB → 5.4KB gzip)
- **Shell Unificado**: Sidebar, login global, módulos como vistas

### Estado BD al Cierre:
- Transacciones: 18+
- Total tablas: 31
- Pool: ThreadedConnectionPool(2, 10)

### Archivos Creados:
- `fin_sys_core/db_pool.py`
- `fin_sys_core/incremental_balance.py`

### Archivos Modificados:
- `database_driver.py`, `hub_driver.py`, `hr_driver.py`, `control_tower_driver.py` — pool
- `server.py` — dashboard-data, cache, reconcile-balances, cache invalidation
- `App.jsx` — fetchData() consolidado
- `main.jsx` — React.lazy + Suspense
- `vite.config.js` — manualChunks()

---

## Checkpoint 2026-06-18 — Sesión 02:28 COT

**Estado**: ✅ Sistema operativo | Módulo 08c RRHH activo

### Trabajo Completado:
- **Shell Unificado**: Sidebar con 5 grupos, login global, HomeDashboard
- **Módulo 08c RRHH**: CompanyMapTab, DocumentsTab, HistorialTab
- **Fixes**: parse error HistorialTab, upload comprobante, mime type, FileCard voucher

### Estado BD: 18 TXs | 31 tablas | 13 pagos HR | 4 docs HR

---

## Checkpoint — 19 Jul 2026 · Unificación de Contabilidad

**Qué**: v1 (App.jsx monolítico) + v2 (contabilidad-v2 parcial) → UN solo módulo.
Estrategia "adapter primero": los componentes v1 REALES montados vía adapters
sobre providers modulares (Empresa → Tenant → Draft). Paridad por construcción,
verificada por el usuario antes del flip.

**Fases**: 0 merge fixes · 1 motor (contrato real + draft provider + tests
payload) · 2 registro+voz+modales · 3 ContextPanel+diario · 4 shell layout v1 ·
5/7 flip directo + limpieza (bake omitido por decisión del usuario).

**Eliminado**: App.jsx, App.css, useTransactionForm, useAccounts(+test),
RegistroForm v2, KPIBar v2, ContextPanel v2, paneles v2 duplicados
(terceros/cartera/cuentas/impuestos/tags/inventarios), engine/index.js.
Recuperable via git history.

**Movido**: components/ y hooks/ de v1 → contabilidad-v2/{modules,components,hooks}.
ErrorBoundary → shell/.

**Bugs de paso**: paginación "Cargar más" (v1 leía data.items inexistente),
KPIs v2 (leía caja_viva en vez de balance), TenantProvider sin industria real.

**Pendiente**: renombrar contabilidad-v2/ → contabilidad/ (Vite lock en Windows).

## Checkpoint — 20 Jul 2026 · Pipeline de deploy restaurado

Prod estuvo congelado del 7 al 20 jul: el compose usa proveedor "Custom Git"
y Dokploy no crea el webhook de GitHub automáticamente — nunca existió.
Diagnóstico vía API de Dokploy (token en scratch/dokploy.env), deploy manual
con POST /api/compose.deploy, y webhook creado en GitHub (push → :3000
/api/deploy/compose/<token>). Módulo Contabilidad unificado EN PRODUCCIÓN.
Pendiente de seguridad: rotar el GitHub PAT del provider.

---

## Checkpoint 2026-08-26 — Armonización: una sola fuente de estado + purga del repo

**Rama**: `claude/harmonizacion-limpieza` (worktree, desde `master`=`2aca212`). Merge y push los corre Andrés.

### 1. Consolidación documental (commit `546845d`)
De cuatro rastreadores de estado divergentes quedaron **dos con roles fijos**:
`docs/checkpoints.md` (bitácora, un checkpoint por sesión) y `CHECKLIST.md` (estado actual +
pendientes DT-* + arranque + accesos). `memory-bank/` se retiró: activeContext/progress/projectbrief
→ `docs/archive/` (índice en su README), `systemPatterns.md` → `docs/system_patterns.md` (sigue vivo).
Archivados además: `estado_proyecto_13jul2026`, `estudio_transcripcion`, `tablas_nuevas_descubiertas`,
`implementaciones_futuras` (sus pendientes pasaron a CHECKLIST como DT-21), `guia_desarrollo_modular_seguro`,
`IDEA.md`. Referencias actualizadas en AGENTS.md, WORKFLOW.md, api_spec.md, reglas_proyecto.md y
`session_maintenance.py` (ya no anuncia .md que dejó de escribir en julio).

### 2. Purga de archivos muertos (commit `dcc7180` — 35 archivos, −788 líneas)
- Boilerplate Vite sin una sola referencia: `react.svg`, `vite.svg`, `hero.png`, `frontend/README.md`.
- Migraciones de cuentas superadas: `migrate_accounts_portfolio.py` (1:1) y `migrate_account_links.py`
  (N:M portafolio). El modelo vigente es `migrate_account_entity_links.py` (cuenta → EMPRESAS).
- `start_*.vbs` (duplicaban `.claude/launch.json` y llamaban al python global, no al venv).
- Carpetas `skills/` anidadas por unzip · `scratch/ct_seed_data.py` destrackeado.
- Tests reubicados: `test_core.py`, `test_coa_fix.py`, `test_e2e.py` → `tests/` (sys.path ajustado).
- `coa_test_module.py` → **`coa_templates.py`** (no era un test: plantillas COA de producción;
  único import en `database_driver.py` actualizado — cambio aprobado en el plan).

### 3. Compuertas de verificación (todas en verde)
`compileall` OK · `tests/test_core.py` **5/5** · `kernel.test_kernel` **5/5** (BD real, auto-limpieza) ·
`unittest` bot (driver 15 + resolvers 10 + confirmación) OK · vitest **45/45** · `npm run build` OK (6.7s).
⚠️ `tests/test_e2e.py` NO se corrió: crea una TX real en la BD compartida — solo a propósito.

### 4. Local en marcha + Dokploy verificado
- Backend :8000 arriba vía `launch.json` (venv por junction en el worktree). Health check **6/7 ✅**
  (solo falta Vite dev, no arrancado a propósito). `/docs`, `/api/org/consolidated`,
  `/api/cartera/summary` → 200.
- **La BD está reiniciada** (`feat(reset)` de la sesión anterior): 0 TXs, patrimonio $1.000.000,
  2 entidades vinculadas / 4 sin vincular. No es anomalía — es el estado limpio.
- **API nueva de Dokploy verificada**: `compose.one` y `deployment.allByCompose` → **200** con la key
  de `scratch/dokploy.env` (la anterior daba 401). El respaldo de deploy por API queda operativo (DT-10).
- Typo corregido en `health_check.py`: imprimía el login viejo `andres@finsys.io` (el real es `.os`).

### Pendiente al cierre
1. Andrés: merge de `claude/harmonizacion-limpieza` a `master` + `git push origin master`.
2. Verificar si el webhook de Dokploy dispara con ese push; si no, `POST /api/compose.deploy` (DT-10).
3. DT-17 (rama por defecto → `master`) y DT-18 (worktrees viejos) siguen manuales.

### Adenda 2026-08-26 (misma sesión) — fixes ejecutados tras la armonización

- **DT-22 (pooler saturado) diagnosticada y semi-resuelta**: con prod + local corriendo, el pooler
  de Supabase en session mode (`:5432`) devolvió `EMAXCONNSESSION` (límite 15 clientes) en vivo —
  500s en `/api/module-flags` y cascada de "Error obteniendo portafolios". El fallback "directo" de
  `db_pool.py` golpea al mismo pooler y amplifica. **Local migrado a `DB_PORT=6543` (transaction
  mode)** — verificado: pool init en 6543, endpoints 200. Falta el mismo cambio en Dokploy (Andrés).
- **`.env.production.example` corregido** (`f672184`): tenía `DB_PASS` (el código lee `DB_PASSWORD`),
  faltaban `SESSION_SECRET` y `TELEGRAM_BOT_TOKEN`, sobraban 3 `SUPABASE_*` que nadie lee.
- **DT-12 RESUELTA**: el `ON CONFLICT` del PUT nunca disparaba con `company_id`/`role_filter` NULL
  (UNIQUE trata NULLs como distintos) → 5 filas para `bot`, y el GET elegía ganador arbitrario
  (¡una decía `enabled=false`!). Fix: UPDATE-first con `IS NOT DISTINCT FROM` en
  `routers/module_flags.py` + `UNIQUE NULLS NOT DISTINCT` en el SQL de instalación (PG 17.6 lo
  soporta). Probado: 3 toggles → 1 fila. Dedup aplicado en la BD real: borradas ids 11/14/15/16,
  conservada id 17 (`bot` enabled=true, estado visible sin cambio).
- **DT-02 / DT-11 parcial**: `server.py` migrado de `@app.on_event("startup")` a `lifespan`
  (asynccontextmanager). Reinicio limpio verificado: cero DeprecationWarning, /docs y API 200.
- **Bot de producción**: Andrés cargó `TELEGRAM_BOT_TOKEN` en Dokploy → Environment. Verificar
  respuesta del bot en Telegram tras el próximo deploy.
- **DT-17**: `gh` sin autenticar → sigue manual (GitHub → Settings → Branches → default `master`).
- **DT-18**: queda 1 worktree obsoleto y 2 ramas muertas; el clasificador bloquea el borrado al
  agente. Comandos para Andrés (PowerShell):
  `git worktree remove --force ".claude\worktrees\admin-dashboard-user-credentials-2aab9b"` ·
  `git branch -D claude/project-status-review-e04f7a claude/duplicate-files-cleanup-78764b`

---

## Checkpoint — 2026-09-02 · Retoma: merge+push de la armonización y deploy a producción

### 1. Git y producción al día
- **Merge fast-forward** de `claude/harmonizacion-limpieza` a `master` (`2aca212..49076ff`, 5 commits)
  y **push a `origin/master` hecho por el agente** (GCM con credencial cacheada — pasó sin bloqueo).
- Compuertas antes del push: kernel **5/5**, motor matemático **5/5**, health check **6/7** (solo
  falta Vite dev, no arrancado a propósito).
- **Deploy a producción verificado**: 3 deployments `done` en Dokploy (20:16/20:18/20:22 UTC) con el
  commit nuevo. El bundle servido en :8080 (`index-DhdhKHl1.js`) es **idéntico** al build local del
  código actual → prod sirve `49076ff`. `/api/health` → `db: connected`, `/api/org/consolidated` y
  `/api/module-flags` → 200.
- Los 2 deployments previos a la llamada API del agente (20:16/20:18) sugieren que **el webhook
  quizá ya dispara** (DT-10) — o Andrés los lanzó del panel. Confirmar con el push de este checkpoint:
  si aparece un deployment sin disparo manual, DT-10 queda cerrada.

### 2. DT-22 CERRADA — pooler en transaction mode en prod
- `DB_PORT=6543` aplicado en Dokploy → Environment (verificado por API releyendo `compose.one`)
  y redeploy hecho. Local ya estaba en 6543. Fin del `EMAXCONNSESSION`.

### 3. Deploy ejecutable por el agente (nuevo)
- Script canónico **`scratch/deploy_prod.py`**: corrige `DB_PORT` si hace falta y dispara
  `compose.deploy`; lee el token de `scratch/dokploy.env` (no imprime secretos).
- Regla de permisos agregada por pedido de Andrés en `~/.claude/settings.json` (user scope, acotada
  al comando exacto): el agente ya puede correr el deploy sin bloqueo del clasificador. Las demás
  mutaciones de Dokploy siguen bloqueadas (correcto).

### Pendiente al cierre
1. **Verificar el bot de producción en Telegram** (Andrés: mandarle un mensaje) — token ya cargado
   y contenedor `bot` redeployado hoy.
2. Confirmar DT-10 (webhook) con el próximo push sin deploy manual.
3. Siguiente frente de desarrollo: **Bot IA etapa C** (bandeja web `BotApp.jsx`), salvo repriorización.
4. DT-17 (rama por defecto) y DT-18 (worktree obsoleto) siguen manuales.

### Adenda 02 sep (misma sesión) — UI: fuera columna Portafolio + formato numérico es-CO

- **DT-10 confirmada muerta por 4ª vez**: el push del checkpoint (`21c4bb3`) no disparó deployment
  en 2+ min. Vía estándar desde ahora: `scratch/deploy_prod.py`.
- **Columna PORTAFOLIO retirada del consolidado** (`DashboardPanel.jsx`, pedido de Andrés): fuera el
  select de vínculos, el botón ＋Portafolio y la celda "vinculada(s)". El vínculo sigue vivo en
  backend (`entities.portfolio_id`); se reubicará con mejor funcionamiento.
- **`shared/NumInput.jsx` nuevo**: input con puntuación de miles/decimales es-CO en vivo
  (`1.234.567,89`), emite el crudo con forma de evento nativo. Aplicado en 12 archivos:
  registro (importe, TRM), cartera (importe/abonos), cuentas (saldos), activos, impuestos (tasas),
  inventario (precios/stock/movimientos), libro diario (edición inline), nómina (MoneyInput).
  Campos chicos (días, repeticiones, cantidad 1-99) quedaron nativos a propósito.
- **Control Tower NO tocado** (Zero-Impact): `CTSidePanel` y `CTApprovalsCenter` tienen montos sin
  formato — pendiente aprobación de Andrés.
- Verificado: vitest 45/45, build OK, columna ausente y formato en vivo comprobados en :8000
  (ojo: la pestaña necesitó recarga real — la navegación SPA retenía el bundle viejo).
