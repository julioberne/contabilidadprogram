# Checkpoints — FIN-SYS OS v2.0

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
