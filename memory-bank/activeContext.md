# Contexto Activo — FIN-SYS OS v2.0

> **ACTUALIZAR al inicio Y al final de cada sesión de trabajo con el AI.**
> Este archivo le dice al agente exactamente qué puede y no puede tocar HOY.

---

## Estado: 22 Jun 2026 — 10:50 COT

## Módulos Activos

| # | Módulo | Estado | Archivos clave |
|---|---|---|---|
| 01–06 | Contabilidad (TXs, Diario, KPIs, Voz, Perfil, Evidencia) | ✅ COMPLETO | `App.jsx`, `server.py` |
| 07 | Control Tower | ✅ COMPLETO | `control-tower/`, `control_tower_driver.py` |
| 08 | Project Hub | ✅ COMPLETO | `project-hub/`, `hub_driver.py` |
| 08c | RRHH / Empresas / Documentos / Historial | ✅ EN USO | `project-hub/features/members/`, `hr_driver.py`, `hr_documents_driver.py` |
| **Cartera CXC/CXP** | **Sub-módulo del ContextPanel** | ✅ EN USO | `ContextPanel.jsx`, `server.py` (endpoints finales) |
| **Zero-COA** | **Motor contable automático** | ✅ FASE 1+2 COMPLETAS | `server.py`, `kernel/`, `posting_rules` |
| **Shell Unificado** | **Navegación entre módulos** | ✅ NUEVO | `frontend/src/shell/*`, `main.jsx` |
| 09 | Bot IA (WhatsApp/Telegram + Groq) | 🔵 PLANIFICADO | — |
| 10 | Trading NASDAQ (PnL, velas, heatmap) | 🔵 PLANIFICADO | — |

---

## Zero-COA — Estado Verificado E2E ✅

**Arquitectura**: El usuario opera en lenguaje de negocio → el backend traduce a partida doble automáticamente.

| Componente | Archivo | Estado |
|---|---|---|
| Tabla `posting_rules` | `database_driver.py` (init_db) | ✅ 22 reglas (17 base + 5 fallback) |
| Tabla `kernel_journal_entries` | `kernel/kernel_accounting.py` | ✅ 30 entries, todos cuadrados |
| Helper `_emit_journal_entry()` | `server.py` (final del archivo) | ✅ Con fallback `__FALLBACK__` |
| Listener `registrar_asiento` | `server.py` startup_event() L197-207 | ✅ Con dedup `off()` antes de `on()` |
| emit() en POST /api/transactions | `server.py` L334-355 | ✅ Integrado |
| emit() en POST /api/cartera | `server.py` (bloque cartera) | ✅ Integrado |
| emit() en POST /api/cartera/{id}/payment | `server.py` (bloque cartera) | ✅ Integrado |
| GET /api/posting-rules | `server.py` | ✅ Activo |
| GET /api/posting-rules/preview | `server.py` | ✅ Con fallback |
| GET /api/journal-entries | `server.py` | ✅ Activo |
| GET /api/financial-summary | `server.py` | ✅ Activo |
| GET /api/dashboard-data | `server.py` L1430-1505 | ✅ Consolidado (TX + accounts + profile + COA) |
| Toggle "👁️ Ver Asiento" | `ContextPanel.jsx` L664-726 | ✅ Activo |

### Bugs corregidos esta sesión (22 Jun 2026):
1. **Listener no registrado** → `on()` en `startup_event()` — commit `b452c6d`
2. **Categorías sin match** → fallback `__FALLBACK__` — commit `b452c6d`
3. **Listener duplicado en hot-reload** → `off()` antes de `on()` — commit `2a21393`
4. **"No hay registros" en Libro Diario** → `/api/dashboard-data` enriquecido — commit `2ca15cf`

---

## Datos Actuales en BD (Verificado 22 Jun 2026 10:50 COT)

| Tabla | Registros |
|---|---|
| `portfolios` | 4 (Negocio A, Pegasus, MI EMPRESA, Negocio Principal) |
| `user_accounts` | 5 (Efectivo, Bancolombia, Nequi, Davivienda, Binance) |
| `transactions` | 10 |
| `third_parties` | 5 (Papelería El Dorado, Carlos Mejía, Claro, Test, WeWork) |
| `cxp_cxc_ledger` | 2 (CXC $3.2M + CXP $379.8K) |
| `posting_rules` | 22 (17 base + 5 fallback) |
| `kernel_journal_entries` | 30 (todos cuadrados Db=Cr) |
| `tags` | 6 (Oficina, Operativo, Recurrente + 3 basura) |
| `entities` (CT) | 13 |
| `hub_workspaces` | 1 |
| `hub_users` | 6 |
| **Total tablas** | **~36** |

---

## Endpoints — Referencia Rápida

### Cartera
| Método | Ruta | Descripción |
|---|---|---|
| `GET` | `/api/cartera` | Lista todas CXC/CXP |
| `GET` | `/api/cartera/summary` | KPIs |
| `GET` | `/api/cartera/alerts` | Alertas inteligentes |
| `POST` | `/api/cartera` | Crea cuenta (+ emit Zero-COA) |
| `POST` | `/api/cartera/{id}/payment` | Registra abono (+ emit Zero-COA) |
| `GET` | `/api/cartera/{id}/payments` | Historial de abonos |
| `DELETE` | `/api/cartera/{id}` | Elimina cuenta |

### Zero-COA
| `GET` | `/api/posting-rules` | Lista 22 reglas de mapeo |
| `GET` | `/api/posting-rules/preview` | Preview asiento sin emitir |
| `GET` | `/api/journal-entries` | Lista asientos contables |
| `GET` | `/api/financial-summary` | Resumen financiero |

### Dashboard Consolidado (SOL-04A)
| `GET` | `/api/dashboard-data` | KPIs + transactions + accounts + portfolios + profile + COA |

**Endpoints totales servidor**: ~94

---

## Archivos Permitidos en Próxima Sesión

### Si se continúa con Contabilidad / Zero-COA:
```
frontend/src/components/ContextPanel.jsx  ← Libre modificación
server.py                                  ← Solo agregar al FINAL
kernel/*                                   ← Libre modificación
```

### Si se trabaja en Módulo 09 (Bot IA) o 10 (Trading):
```
server.py                                (solo agregar al FINAL)
fin_sys_core/bot_driver.py               (NUEVO)
frontend/src/bot/ o frontend/src/trading/ (NUEVO)
frontend/src/main.jsx                    (solo añadir al switch)
frontend/src/shell/Sidebar.jsx           (solo añadir item al array NAV)
```

## Archivos PROHIBIDOS (Zero-Impact Policy)
```
frontend/src/App.jsx                    ← Preferir extraer componente
frontend/src/control-tower/*            ← NO tocar
fin_sys_core/control_tower_driver.py    ← NO tocar (aprobación explícita)
fin_sys_core/database_driver.py         ← Solo con aprobación explícita
.env                                    ← NUNCA tocar
Tablas de BD existentes                 ← NO alterar schema sin aprobación
```

---

## Datos de Acceso

**Workspace Hub**: Inversiones FIN-SYS (`37888f92-8bef-4528-b187-2064c6f0049c`)

| Rol | Email | Contraseña |
|---|---|---|
| OWNER | andres@finsys.io | admin123 |
| ADMIN | sofia@finsys.io | sofia123 |
| MEMBER | camilo@finsys.io | camilo123 |
| MEMBER | valentina@finsys.io | vale123 |
| VIEWER | daniel@finsys.io | daniel123 |

**CT Login**: andres@finsys.os / admin123  
**Supabase Project**: `sciorfjvdqxvcwgvnmbv` (us-east-2)  
**Storage Bucket**: `hr-docs` (público)

---

## Deuda Técnica Pendiente

| ID | Problema | Prioridad |
|---|---|---|
| DT-01 | Balance Efectivo -$11.2M (legacy sin account_id) | Media |
| DT-02 | `on_event` deprecation → migrar a `lifespan` FastAPI | Baja |
| DT-03 | CT: CXP/CXP en KPIs parcial | Media |
| DT-04 | MD5 en workspace_users → bcrypt | Alta |
| DT-05 | SHA-256 en hub_users → bcrypt | Alta |
| DT-06 | Bundle ~1.7MB sin code splitting | Media |
| DT-07 | Fuentes Kanban/TaskModal pendientes | Baja |
| DT-08 | Integración contabilidad-nómina | Media |
| DT-09 | Comprobante nómina: integrar con tablas contables | Baja |
| DT-10 | `<form>` anidado en App.jsx:1238 | Alta |
| DT-11 | `userProfile` undefined en App.jsx:2450 | Alta |
| ~~DT-12~~ | ~~Auto-mark VENCIDO en cartera batch~~ | ~~Resuelto~~ ✅ |
| DT-13 | Limpiar tags basura (bnm, dfghj, nm) | Baja |
| DT-14 | Limpiar TX de prueba ("Test debug emit" x2) | Baja |

---

## Instrucción al Agente al Inicio de Próxima Sesión

1. Leer este archivo completo
2. Leer `AGENTS.md` para reglas del proyecto
3. Correr `python scripts/health_check.py`
4. **ANTES** de cualquier cambio: listar archivos a modificar y esperar aprobación
5. Nunca modificar módulos COMPLETOS (01–08) sin aprobación explícita
6. Zero-Impact Policy: módulos nuevos = nuevas carpetas

## Contexto RRHH para Próxima Sesión

El módulo 08c (RRHH/Empresas) incluye:
- `CompanyMapTab.jsx` — árbol jerárquico Holding→Empresa→Subsidiaria→Proyecto
- `MemberProfile.jsx` — perfil con pestañas: Documentos | Historial
- `DocumentsTab.jsx` — gestor de documentos (drive-style) con preview HTML para comprobantes
- `HistorialTab.jsx` — historial de pagos con generación de comprobantes
- `RRHHView.jsx` — vista principal del módulo RRHH
