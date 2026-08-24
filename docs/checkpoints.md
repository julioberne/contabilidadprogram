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

**El webhook de Dokploy NO disparó — tercera vez (DT-10).** Verificado contra producción:
`Last-Modified: Wed, 29 Jul 2026` y `GET /api/org/consolidated` → **404**. El deploy sigue
sin hacerse. Además, el token de `scratch/dokploy.env` responde **401** en
`GET /api/deployment.allByCompose`: fue revocado o rotado, así que el deploy manual por API
necesita una key nueva del panel (:3000) o hacerse desde la UI de Dokploy.

### Pendiente al cierre
1. **Desplegar a mano** (el push ya está hecho): panel Dokploy :3000 → compose `finsys-app` →
   Deploy; o `POST /api/compose.deploy` con una API key nueva. Verificar después que
   `Last-Modified` cambió y que `GET /api/org/consolidated` responde 200 en producción.
2. Borrar los 4 worktrees obsoletos y las 6 ramas `claude/*` + `gilded-mask` (comandos en
   la conversación de la sesión; ninguna tiene trabajo tras el cherry-pick).
3. Decidir sobre `main` vs `master` en GitHub (DT-17) y sobre los 10 audios huérfanos (DT-19).
4. Re-correr TestSprite sobre el build con los fixes (y avanzar TC031–TC050).
5. Buscador del Libro Diario (TC022) · normalizar upsert de `module_flags` (DT-12).

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
