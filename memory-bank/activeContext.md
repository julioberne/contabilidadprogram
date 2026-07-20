# Contexto Activo — FIN-SYS OS v2.0

> **ACTUALIZAR al inicio Y al final de cada sesión de trabajo con el AI.**
> Este archivo le dice al agente exactamente qué puede y no puede tocar HOY.

---

## Estado: 19 Jul 2026 — UNIFICACIÓN DE CONTABILIDAD COMPLETADA

**Un solo módulo Contabilidad** (UI de v1 + arquitectura modular v2).
`App.jsx` monolítico ELIMINADO. Paridad verificada por el usuario antes del flip.

## Estructura del módulo unificado (`frontend/src/contabilidad-v2/`)

| Capa | Contenido |
|---|---|
| `ContabilidadApp.jsx` | Shell con layout v1 (header empresas, alertas, dashboard, grid, diario) |
| `engine/` | EmpresaProvider (portafolio+empresa+datos) · TransactionDraftProvider (form completo) · TenantProvider (labels por industria) · buildTransactionPayload (puro, con tests) |
| `modules/` | registro/ (TransactionForm+CoA+widgets) · voz/ · diario/ · empresas/ · perfil/ — UI v1 + adapters |
| `components/` | ContextPanel (7 tabs) + tabs/ + cartera/ + inventory/ + modales |
| `hooks/` | useDashboardData (contrato real + paginación) · useCalculator · useAdminActions |

Tests: `npm test` → buildTransactionPayload (paridad payload v1) + useCalculator + useProfile.

---

## Módulos Activos

| # | Módulo | Estado | Archivos clave |
|---|---|---|---|
| 01–06 | **Contabilidad (unificado)** | ✅ ACTIVO | `contabilidad-v2/` (ver arriba) |
| 07 | Control Tower | ✅ COMPLETO | `control-tower/`, `control_tower_driver.py` |
| 08 | Project Hub | ✅ COMPLETO | `project-hub/`, `hub_driver.py` |
| 08c | RRHH / Empresas / Documentos / Historial | ✅ EN USO | `project-hub/features/members/`, `hr_driver.py` |
| — | Zero-COA Kernel | ✅ Fase 1+2 | `kernel/`, `routers/zero_coa.py` |
| 09 | Bot IA (WhatsApp/Telegram + Groq) | 🔵 PLANIFICADO | — |
| 10 | Trading NASDAQ (PnL, velas, heatmap) | 🔵 PLANIFICADO | — |

**Pendiente menor**: renombrar carpeta `contabilidad-v2/` → `contabilidad/`
(requiere Vite detenido — el watcher bloquea el rename en Windows).

---

## Estado de Salud del Sistema (Verificado 13 Jul 2026 — 02:43 COT)

```
❌ Frontend (React/Vite)    → :5173 y :5174 CAÍDOS
❌ Backend (FastAPI)         → :8000 CAÍDO
✅ PostgreSQL (Supabase)     → 15 TXs | 13 entidades CT | 5 cuentas (dinámicas, creadas por usuario)
✅ Motor Matemático           → IVA=19.000 | GMF=400
⚠️  Control Tower API          → OMITIDO (backend caído)
⚠️  Project Hub API            → OMITIDO (backend caído)
✅ Integridad de datos        → Sin anomalías (cuentas dinámicas: las crea el usuario)
```

**Arrancar servicios:**
```bash
python server.py                    # Terminal 1
cd frontend && npm run dev          # Terminal 2
python scripts/health_check.py      # Re-verificar
```

---

## Archivos Permitidos en Próxima Sesión

### Si se continúa Contabilidad v2 (prioridad actual):
```
frontend/src/contabilidad-v2/**                              ← Activo
frontend/src/registry/moduleRegistry.js                      ← Solo si se registra módulo nuevo
```

**Pendiente v2 antes de commit:**
- Unificar API base URL (`config.js` vs `localhost:8000` hardcodeado)
- Completar campos faltantes en RegistroForm (categoría, método pago, TRM)
- Decidir estrategia v1 vs v2 (convivencia o migración)

### Si se trabaja en RRHH (módulo 08c):
```
frontend/src/project-hub/features/members/tabs/DocumentsTab.jsx
frontend/src/project-hub/features/members/tabs/HistorialTab.jsx
frontend/src/project-hub/features/members/MemberProfile.jsx
frontend/src/project-hub/features/members/CompanyMapTab.jsx
frontend/src/project-hub/features/members/RRHHView.jsx
fin_sys_core/hr_driver.py                                          ← Solo agregar
fin_sys_core/hr_documents_driver.py                                ← Solo agregar
server.py                                                          ← Solo agregar al FINAL
```

### Si se trabaja en Módulo 09 (Bot IA):
```
server.py                    (solo agregar al FINAL)
fin_sys_core/bot_driver.py   (NUEVO)
frontend/src/bot/BotApp.jsx  (NUEVO)
frontend/src/bot/components/ (NUEVO)
frontend/src/registry/moduleRegistry.js  (entrada bot)
```

### Si se trabaja en Módulo 10 (Trading):
```
server.py                        (solo agregar al FINAL)
fin_sys_core/trading_driver.py   (NUEVO)
frontend/src/trading/TradingApp.jsx (NUEVO)
frontend/src/registry/moduleRegistry.js  (entrada trading)
```

## Archivos PROHIBIDOS (Zero-Impact Policy)
```
frontend/src/App.jsx                    ← NO tocar
frontend/src/control-tower/*            ← NO tocar
fin_sys_core/database_driver.py         ← NO tocar (aprobación explícita)
fin_sys_core/control_tower_driver.py    ← NO tocar (aprobación explícita)
.env                                    ← NUNCA tocar bajo ninguna circunstancia
Tablas de BD existentes                 ← NO alterar schema sin aprobación explícita
```

---

## Deuda Técnica Pendiente

| ID | Problema | Prioridad |
|---|---|---|
| DT-01 | Balance Efectivo -$11.2M (legacy sin account_id) | Media |
| DT-02 | `on_event` deprecation → migrar a `lifespan` FastAPI | Baja |
| DT-03 | CT: CXP/CXC en KPIs parcial | Media |
| DT-04 | MD5 en workspace_users → bcrypt | Alta |
| DT-05 | SHA-256 en hub_users → bcrypt | Alta |
| DT-06 | Bundle ~1.7MB sin code splitting | Media |
| DT-07 | Fuentes Kanban/TaskModal pendientes (CSS classes no aplicadas) | Baja |
| DT-08 | Integración contabilidad-nómina (totalizar gasto nómina en CoA) | Media |
| DT-09 | Comprobante nómina: integrar con tablas contables al generarse | Baja |

---

## Orden de Trabajo — Sesión 13 Jul 2026

### Opciones priorizadas (elegir una):
1. **Opción E** — Cerrar Contabilidad v2 Fase 2 (paridad registro, unificar API, commit WIP) — **FOCO ACTUAL**
2. **Opción A** — Módulo 09 Bot IA (WhatsApp + Groq Whisper) — ALTO VALOR
3. **Opción B** — Módulo 10 Trading NASDAQ (posiciones + PnL) — ALTO VALOR
4. **Opción C** — Kernel Partida Doble (K1–K6, cierra gap contable crítico)
5. **Opción D** — Limpieza técnica (bcrypt, DT-01 balance, DT-02 lifespan)

---

## Instrucción al Agente al Inicio de Próxima Sesión

1. Leer este archivo completo
2. Leer `docs/estado_proyecto_13jul2026.md` para panorama completo
3. Correr `python scripts/health_check.py`
4. Correr `python scripts/session_maintenance.py --check` para estado actual
5. **ANTES** de cualquier cambio: listar archivos a modificar y esperar aprobación
6. Nunca modificar módulos COMPLETOS (01–08) sin aprobación explícita
7. Zero-Impact Policy: módulos nuevos = nuevas carpetas

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

## Contexto RRHH (referencia)

El módulo 08c (RRHH/Empresas) incluye:
- `CompanyMapTab.jsx` — árbol jerárquico Holding→Empresa→Subsidiaria→Proyecto
- `MemberProfile.jsx` — perfil con pestañas: Documentos | Historial
- `DocumentsTab.jsx` — gestor de documentos (drive-style) con preview HTML para comprobantes
- `HistorialTab.jsx` — historial de pagos con generación de comprobantes
- `RRHHView.jsx` — vista principal del módulo RRHH

**Flujo comprobante** (Historial → Documentos):
1. Click "◈ Generar" en HistorialTab
2. Genera HTML → sube a `hr-docs` bucket como `application/octet-stream`
3. Guarda metadata en `hr_documents` via `POST /api/hr/documents/{user_id}`
4. Vincula via `PUT /api/hr/payments/{user_id}/{rec_id}/voucher?doc_id={id}`
5. DocumentsTab recarga y muestra tarjeta 🧾 COMPROBANTE

---

## Trabajo previo documentado

- **Sesión 2026-07-05:** Fixes críticos RRHH (comprobantes, storage, parse error) — ver `docs/checkpoints.md`
- **Sesión 2026-07-12:** Análisis arquitectura completo
- **Sesión 2026-07-13:** Documentación de estado + foco Contabilidad v2
