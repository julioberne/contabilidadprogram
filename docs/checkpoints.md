# Checkpoints — FIN-SYS OS v2.0

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
