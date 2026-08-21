# Progress — FIN-SYS OS v2.0

> Resumen de avance por módulo. Última actualización: 21 Ago 2026 — 17:05 COT

---

## Módulos

| # | Módulo | Estado | En producción | Archivos principales |
|---|---|---|---|---|
| 01 | Registro de Transacciones | ✅ COMPLETO (cerrado 10 ago: secciones avanzadas, impuestos con autorización humana) | ❌ solo en rama | `contabilidad-v2/modules/registro/` |
| 02 | Libro Diario + Filtros | ✅ COMPLETO (sin buscador — ver TC022) | ✅ | `contabilidad-v2/modules/diario/` |
| 03 | Caja Viva (KPIs) | ✅ COMPLETO | ✅ | `ledger_math.py`, `routers/dashboard_data.py` |
| 04 | Motor de Voz (RAG) | ✅ COMPLETO — unificado con el bot vía `draft_builder.py` (10 ago) | ❌ unificación solo en rama | `ai_engine.py`, `modules/voz/` |
| 05 | Perfil + Cuentas Multi-moneda | ✅ COMPLETO (10 ago: saldo inicial editable + pulso de cuentas con descuadres) | ❌ mejoras solo en rama | `routers/profile_accounts.py`, `modules/empresas/AccountsPulse.jsx` |
| 06 | Evidencia + Edición | ✅ COMPLETO | ✅ | `contabilidad-v2/components/` |
| 07 | Control Tower | ✅ COMPLETO | ✅ | `control-tower/`, `control_tower_driver.py` |
| 08 | Project Hub | ✅ COMPLETO | ✅ | `project-hub/`, `hub_driver.py` |
| 08c | RRHH / Empresas / Documentos / Historial | ✅ EN USO | ✅ | `members/tabs/`, `hr_driver.py` |
| — | Zero-COA Kernel | ✅ Fase 1+2 | ✅ | `kernel/`, `routers/zero_coa.py` |
| 09 | **Bot IA (Telegram + Groq)** | 🟡 **MVP funcional, sin merge ni deploy** | ❌ | `bot_driver.py`, `bot_telegram.py`, `routers/bot.py`, `draft_builder.py` |
| 10 | Trading NASDAQ (PnL, velas, heatmap) | 🔵 PLANIFICADO | ❌ | — |

> ⚠️ **Producción va tres semanas atrás**: sirve `master` = `64badb6` (29 jul).
> Todo lo de agosto vive en `modulo-09-bot-ia` (`f5559f7`) + working tree sin commit.

---

## Sesiones de Trabajo

### Sesión 1 (01–04 Jun 2026)
- Módulos 01–06 completados · Skill `multi-currency-ledger-setup` publicado

### Sesión 2 (09 Jun 2026)
- Módulo 07 Control Tower completo · Seed: 7 entidades, 5 usuarios CT

### Sesión 3 (11 Jun 2026)
- Módulo 08 Project Hub completo (FASES 1–5) · Seed hub · Bug fixes de UI

### Sesión 4 (2026-07-05)
- Módulo 08c RRHH: CompanyMapTab, DocumentsTab, HistorialTab, comprobantes en `hr-docs`
- `scripts/session_maintenance.py` creado

### Sesión 5 (2026-07-19/20) — Unificación + deploy
- Contabilidad v1 + v2 fusionadas en un solo módulo (`App.jsx` monolítico eliminado)
- Pipeline de deploy restaurado: el webhook GitHub→Dokploy nunca existió (proveedor Custom Git);
  prod estuvo congelado del 7 al 20 jul

### Sesión 6 (2026-07-26/27) — Remediación de auditoría (F1–F4)
- Backdoor de login eliminado · auth por token HMAC en endpoints destructivos
- MD5/SHA-256 → bcrypt (DT-04, DT-05 cerradas) · migraciones del kernel aplicadas
- Cuentas demo `@finsys.io` eliminadas; admin real consolidado en `andres@finsys.os`

### Sesión 7 (2026-07-29) — Project Hub + TestSprite + PRD
- Fixes de Hub: workspaces huérfanos, tareas sin guardar con fecha vacía, compendio de tareas
- **TestSprite E2E**: 30/50 casos · 25 ✅ / 5 ❌ (83.33%) — reporte en `testsprite_tests/`
- `docs/PRD.md` creado (fuente de verdad de negocio, sin detalle técnico)

### Sesión 8 (2026-08-09/10) — Módulo 09 Bot IA
- COA: reglas EGRESO→GASTO, fallback de ingreso 4120→417505
- **Bot Telegram MVP**: borradores persistentes en BD + confirmación determinista + tests
- Resolutores reales (portafolio, método de pago, UUID) + `bot_link_code.py`
- `draft_builder.py`: voz web y bot comparten un solo camino de borrador
- Módulo 01 completo (secciones avanzadas, impuestos solo con autorización humana)
- Cuentas: saldo inicial editable, pulso con movimientos reales y descuadres

### Sesión 9 (2026-08-21) — Revisión de estado
- Sin código nuevo. Auditoría de dónde está cada cosa: rama sin merge, WIP sin commit del que
  depende código ya commiteado, prod desactualizada
- `docs/checkpoints.md`, `memory-bank/activeContext.md`, `progress.md` y `CHECKLIST.md` puestos al día

---

## Estado de la Base de Datos (health_check en vivo, 21 Ago 2026 — 16:57 COT)

| Tabla | Registros |
|---|---|
| `portfolios` | 4 |
| `user_accounts` | 5 |
| `transactions` | 13 (incluye 2 `TS-TEST-*` por limpiar) |
| `entities` (CT) | 6 — **ninguna con `portfolio_id` poblado** (DT-14) |
| `hub_workspaces` | 1+ |
| `hub_tasks` | 21 (incluye 1 `TS-TEST-*`) |
| `hr_payment_records` | 13 |
| `hr_documents` | 6 |

Integridad: sin anomalías. Motor matemático: IVA=19.000 · GMF=400 ✓

---

## Métricas del Proyecto (medidas 2026-08-21)

| Métrica | Valor |
|---|---|
| Líneas Python (`fin_sys_core` + `routers` + `kernel` + `scripts` + `tests` + `server.py`) | ~15,587 |
| Líneas JSX/JS/CSS (`frontend/src`) | ~22,549 |
| Endpoints FastAPI | ~132 |
| Tablas Supabase | ~40 |
| Suites de tests | kernel (5/5) · `test_bot_driver` · `test_bot_confirmation` · `test_bot_resolvers` · frontend (`npm test`) |
| Cobertura E2E (TestSprite) | 25/30 casos ejecutados en verde (83.33%) |
| Storage bucket | `hr-docs` (público) |
