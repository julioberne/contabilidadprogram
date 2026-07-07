# Contexto Activo — FIN-SYS OS v2.0

> **ACTUALIZAR al inicio Y al final de cada sesión de trabajo con el AI.**
> Este archivo le dice al agente exactamente qué puede y no puede tocar HOY.

---

## Estado: 05 Jul 2026 — 19:09 COT

## Módulos Activos

| # | Módulo | Estado | Archivos clave |
|---|---|---|---|
| 01–06 | Contabilidad (TXs, Diario, KPIs, Voz, Perfil, Evidencia) | ✅ COMPLETO | `App.jsx`, `server.py` |
| 07 | Control Tower | ✅ COMPLETO | `control-tower/`, `control_tower_driver.py` |
| 08 | Project Hub | ✅ COMPLETO | `project-hub/`, `hub_driver.py` |
| 08c | RRHH / Empresas / Documentos / Historial | ✅ EN USO | `project-hub/features/members/`, `hr_driver.py`, `hr_documents_driver.py` |
| 09 | Bot IA (WhatsApp/Telegram + Groq) | 🔵 PLANIFICADO | — |
| 10 | Trading NASDAQ (PnL, velas, heatmap) | 🔵 PLANIFICADO | — |

---

## Trabajo Realizado en Sesión (2026-07-05)

### Módulo 08c — RRHH/Empresas: FIXES CRÍTICOS

| Archivo | Cambio |
|---|---|
| `frontend/src/project-hub/features/members/tabs/DocumentsTab.jsx` | Fix descarga blob, ícono 🧾 comprobante, FileCard voucher preview |
| `frontend/src/project-hub/features/members/tabs/HistorialTab.jsx` | Upload comprobante vía `supabase.storage.from('hr-docs').upload()` directo (sin backend), fix closing brace parse error |
| `server.py` | Endpoint `POST /api/hr/storage/sign-upload` actualizado a requests HTTP (sin SDK supabase Python) |

### Bugs Corregidos Esta Sesión:
1. **Parse error** en HistorialTab.jsx — llave de cierre `};` faltante por merge corrupto
2. **`mime type text/html is not supported`** — Supabase Storage bloquea text/html; cambiado a `application/octet-stream`
3. **`No module named 'supabase'`** — SDK Python no instalado; reemplazado por llamadas HTTP directas con `requests`
4. **Descarga 404** — `<a href download>` → `downloadFile()` blob-based en FileCard y FileRow
5. **Miniaturas** — FileCard ahora detecta `isVoucher` y muestra ícono 🧾 + label COMPROBANTE

---

## Archivos Permitidos en Próxima Sesión

### Si se trabaja en RRHH (módulo 08c):
```
frontend/src/project-hub/features/members/tabs/DocumentsTab.jsx   ← Activo
frontend/src/project-hub/features/members/tabs/HistorialTab.jsx    ← Activo
frontend/src/project-hub/features/members/MemberProfile.jsx        ← Activo
frontend/src/project-hub/features/members/CompanyMapTab.jsx        ← Activo
frontend/src/project-hub/features/members/RRHHView.jsx             ← Activo
fin_sys_core/hr_driver.py                                          ← Solo agregar, no modificar existentes
fin_sys_core/hr_documents_driver.py                                ← Solo agregar, no modificar existentes
server.py                                                          ← Solo agregar al FINAL
```

### Si se trabaja en Módulo 09 (Bot IA):
```
server.py                    (solo agregar al FINAL)
fin_sys_core/bot_driver.py   (NUEVO)
frontend/src/bot/BotApp.jsx  (NUEVO)
frontend/src/bot/components/ (NUEVO)
main.jsx                     (solo añadir pestaña Bot al router)
```

### Si se trabaja en Módulo 10 (Trading):
```
server.py                        (solo agregar al FINAL)
fin_sys_core/trading_driver.py   (NUEVO)
frontend/src/trading/TradingApp.jsx (NUEVO)
main.jsx                         (solo añadir pestaña Trading al router)
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

## Estado de Salud del Sistema (Verificado 05 Jul 2026 — 19:09 COT)

```
✅ Frontend (React/Vite)    → :5173 OK
✅  Backend (FastAPI)         → :8000 OK
✅ PostgreSQL (Supabase)     → 13 TXs | 37 tablas | 13 entidades CT
✅  Motor Matemático           → IVA=19.000 | GMF=400
✅  Control Tower API          → Balance Holding $8,550,656
✅  RRHH/Empresas              → N/A miembros | 13 pagos | 6 docs
   Project Hub                  → 6 usuarios | 21 tareas | 7 notas
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
| DT-03 | CT: CXP/CXC en KPIs parcial | Media |
| DT-04 | MD5 en workspace_users → bcrypt | Alta |
| DT-05 | SHA-256 en hub_users → bcrypt | Alta |
| DT-06 | Bundle ~1.7MB sin code splitting | Media |
| DT-07 | Fuentes Kanban/TaskModal pendientes (CSS classes no aplicadas) | Baja |
| DT-08 | Integración contabilidad-nómina (totalizar gasto nómina en CoA) | Media |
| DT-09 | Comprobante nómina: integrar con tablas contables al generarse | Baja |

---

## Instrucción al Agente al Inicio de Próxima Sesión

1. Leer este archivo completo
2. Correr `python scripts/health_check.py`
3. Correr `python scripts/session_maintenance.py --check` para estado actual
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

**Flujo comprobante** (Historial → Documentos):
1. Click "◈ Generar" en HistorialTab
2. Genera HTML → sube a `hr-docs` bucket como `application/octet-stream`
3. Guarda metadata en `hr_documents` via `POST /api/hr/documents/{user_id}`
4. Vincula via `PUT /api/hr/payments/{user_id}/{rec_id}/voucher?doc_id={id}`
5. DocumentsTab recarga y muestra tarjeta 🧾 COMPROBANTE
