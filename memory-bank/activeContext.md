# Contexto Activo — FIN-SYS OS v2.0

> **ACTUALIZAR al inicio Y al final de cada sesión de trabajo con el AI.**
> Este archivo le dice al agente exactamente qué puede y no puede tocar HOY.

---

## Estado: 22 Jun 2026 — 00:15 COT

## Módulos Activos

| # | Módulo | Estado | Archivos clave |
|---|---|---|---|
| 01–06 | Contabilidad (TXs, Diario, KPIs, Voz, Perfil, Evidencia) | ✅ COMPLETO | `App.jsx`, `server.py` |
| 07 | Control Tower | ✅ COMPLETO | `control-tower/`, `control_tower_driver.py` |
| 08 | Project Hub | ✅ COMPLETO | `project-hub/`, `hub_driver.py` |
| 08c | RRHH / Empresas / Documentos / Historial | ✅ EN USO | `project-hub/features/members/`, `hr_driver.py`, `hr_documents_driver.py` |
| **Cartera CXC/CXP** | **Sub-módulo del ContextPanel** | ✅ EN USO | `ContextPanel.jsx`, `server.py` (endpoints finales) |
| **Zero-COA** | **Motor contable automático** | ✅ FASE 1+2 COMPLETAS | `server.py`, `kernel/`, `posting_rules` |
| 09 | Bot IA (WhatsApp/Telegram + Groq) | 🔵 PLANIFICADO | — |
| 10 | Trading NASDAQ (PnL, velas, heatmap) | 🔵 PLANIFICADO | — |

---

## Zero-COA — Estado Actual

**Arquitectura**: El usuario opera en lenguaje de negocio → el backend traduce a partida doble automáticamente.

| Componente | Archivo | Estado |
|---|---|---|
| Tabla `posting_rules` | `database_driver.py` (init_db L371-388) | ✅ Creada |
| 17 reglas de mapeo | `scripts/seed_puc.py` | ✅ Pobladas en Supabase |
| Helper `_emit_journal_entry()` | `server.py` (final del archivo) | ✅ Activo |
| emit() en POST /api/transactions | `server.py` L334-345 | ✅ Integrado |
| emit() en POST /api/cartera | `server.py` (bloque cartera) | ✅ Integrado |
| emit() en POST /api/cartera/{id}/payment | `server.py` (bloque cartera) | ✅ Integrado |
| GET /api/posting-rules | `server.py` | ✅ Nuevo |
| GET /api/posting-rules/preview | `server.py` | ✅ Nuevo |
| GET /api/journal-entries | `server.py` | ✅ Nuevo |
| GET /api/financial-summary | `server.py` | ✅ Nuevo |
| Toggle "👁️ Ver Asiento" | `ContextPanel.jsx` L664-726 | ✅ Nuevo |

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

### Terceros
| `POST` | `/api/third-parties` | Crea tercero standalone |
| `PUT` | `/api/third-parties/{id}` | Actualiza tercero |

### Zero-COA
| `GET` | `/api/posting-rules` | Lista 17 reglas de mapeo |
| `GET` | `/api/posting-rules/preview` | Preview asiento sin emitir |
| `GET` | `/api/journal-entries` | Lista asientos contables |
| `GET` | `/api/financial-summary` | Resumen financiero |

**Endpoints totales servidor**: ~94

---

## Archivos Permitidos en Próxima Sesión

### Si se continúa con Cartera / Zero-COA:
```
frontend/src/components/ContextPanel.jsx  ← Libre modificación
server.py                                  ← Solo agregar al FINAL
```

### Si se trabaja en Módulo 09 (Bot IA) o 10 (Trading):
```
server.py                                (solo agregar al FINAL)
fin_sys_core/bot_driver.py               (NUEVO)
frontend/src/bot/ o frontend/src/trading/ (NUEVO)
main.jsx                                 (solo añadir pestaña al router)
```

## Archivos PROHIBIDOS (Zero-Impact Policy)
```
frontend/src/control-tower/*            ← NO tocar
fin_sys_core/control_tower_driver.py    ← NO tocar (aprobación explícita)
.env                                    ← NUNCA tocar bajo ninguna circunstancia
Tablas de BD existentes                 ← NO alterar schema sin aprobación explícita
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
| **DT-10** | **`<form>` anidado en App.jsx:1238** | **Alta** |
| **DT-11** | **`userProfile` undefined en App.jsx:2450** | **Alta** |
| **DT-12** | **Auto-mark VENCIDO en cartera batch** | **Resuelto** ✅ |
| DT-13 | Limpiar datos sintéticos (IDs 3-7, "Test TP") | Baja |

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
