# Documentación de Estado — FIN-SYS OS v2.0

> ⚠️ **DOCUMENTO HISTÓRICO — no refleja el estado actual.** Retrato del proyecto al
> 13 Jul 2026. Desde entonces pasaron la unificación de Contabilidad, la remediación de
> auditoría, la corrida de TestSprite y el Módulo 09 (Bot IA).
> **Estado vigente**: `memory-bank/activeContext.md` y el último checkpoint de
> `docs/checkpoints.md`. Se conserva por trazabilidad, no como referencia.

**Generado:** 13 Jul 2026 · 02:43 COT  
**Verificación en vivo:** `python scripts/health_check.py` ejecutado en esta sesión

---

## 1. Resumen ejecutivo

FIN-SYS OS es un ERP contable modular para pymes colombianas. El núcleo (módulos 01–08) está **completo a nivel de código**. Hay una **segunda línea de contabilidad** (`contabilidad-v2/`) en desarrollo activo con trabajo local **sin commit**. Los módulos 09 (Bot IA) y 10 (Trading) están planificados.

| Dimensión | Estado |
|---|---|
| Producción-ready | No — deuda de seguridad (bcrypt DT-04/05) y balance legacy (DT-01) |
| Código base | Estable — arquitectura modular documentada |
| Foco actual | Contabilidad v2 (registro + draft provider) |
| Servicios locales (13 Jul 02:43) | Frontend y backend **caídos**; BD y motor **OK** |
| Riesgo principal | Convivencia v1/v2 sin estrategia de migración definida |

---

## 2. Salud del sistema (verificado 13 Jul 2026 — 02:43 COT)

| # | Check | Estado | Detalle |
|---|---|---|---|
| 1 | Frontend Vite | ❌ | `:5173` y `:5174` caídos |
| 2 | Backend FastAPI | ❌ | `:8000` caído |
| 3 | PostgreSQL Supabase | ✅ | **15 TXs** · 13 entidades CT · **5 cuentas** |
| 4 | Motor matemático | ✅ | IVA=19.000 · GMF=400 |
| 5 | Control Tower API | ⚠️ | Omitido (backend caído) |
| 6 | Project Hub API | ⚠️ | Omitido (backend caído) |
| 7 | Integridad de datos | ⚠️ | Solo **5 cuentas bancarias** (esperado: 7) |

> **Nota:** Los conteos de TXs y cuentas provienen del health check en vivo. Cuando frontend/backend estén arriba, re-ejecutar para KPIs de CT y Hub.

### Comandos de verificación

```bash
# Salud completa (7 checks)
python scripts/health_check.py

# Mantenimiento de sesión
python scripts/session_maintenance.py --check

# Tests automatizados
python fin_sys_core/test_core.py          # 5/5 motor matemático
python kernel/test_kernel.py              # partida doble + event bus
python kernel/test_e2e.py                 # end-to-end kernel

# Frontend
cd frontend && npm run lint && npm test
```

### Arranque local

```bash
# Terminal 1 — Backend
python server.py

# Terminal 2 — Frontend
cd frontend && npm run dev
```

---

## 3. Módulos — estado funcional

| ID | Módulo | Estado | Ruta principal |
|---|---|---|---|
| 01–06 | Contabilidad v1 | ✅ COMPLETO | `frontend/src/App.jsx` |
| — | **Contabilidad v2** | 🟡 EN DESARROLLO | `frontend/src/contabilidad-v2/` |
| 07 | Control Tower | ✅ COMPLETO | `frontend/src/control-tower/` |
| 08 | Project Hub | ✅ COMPLETO | `frontend/src/project-hub/` |
| 08c | RRHH / Empresas | ✅ EN USO | `project-hub/features/members/` |
| — | Zero-COA Kernel | ✅ Fase 1+2 | `kernel/` + `routers/zero_coa.py` |
| 09 | Bot IA | 🔵 PLANIFICADO | — |
| 10 | Trading NASDAQ | 🔵 PLANIFICADO | — |
| — | Tesorería, Facturación, Ventas… | 🔵 Inactivos | `active: false` en registry |

**Módulos activos en sidebar** (`frontend/src/registry/moduleRegistry.js`):

- Contabilidad (v1)
- Contabilidad v2
- RRHH
- Control Tower

---

## 4. Arquitectura del codebase

### Stack

| Capa | Tecnología | Puerto / Ruta |
|---|---|---|
| Frontend | Vite + React 19 | `:5173` · `frontend/src/` |
| Backend | FastAPI Python 3.10+ | `:8000` · `server.py` |
| BD | PostgreSQL 17 Supabase | us-east-2 |
| IA | Groq Whisper + Llama 3.3 | `fin_sys_core/ai_engine.py` |
| Estilo | Retro-brutalista | IBM Plex Mono · bordes 2px · radius 0 |

### Estructura raíz

```
contabilidadprogram/
├── server.py                 # Bootstrap (CORS, routers, startup)
├── routers/                  # 14 routers REST
├── fin_sys_core/             # Drivers + motor + IA
├── kernel/                   # Partida doble Zero-COA
├── frontend/src/
│   ├── main.jsx              # Shell unificado
│   ├── registry/moduleRegistry.js  # SSOT módulos
│   ├── shell/                # Login, Sidebar, Header, Home
│   ├── App.jsx               # Contabilidad v1
│   ├── contabilidad-v2/      # Contabilidad v2 (WIP)
│   ├── control-tower/        # Módulo 07
│   └── project-hub/          # Módulo 08 + RRHH
├── scripts/                  # health_check, seed, migraciones
├── docs/                     # Specs y roadmap
└── memory-bank/              # Contexto de sesión AI
```

### Routers backend (14)

| Router | Dominio |
|---|---|
| `portfolios` | Portafolios multi-negocio |
| `transactions` | CRUD transacciones |
| `profile_accounts` | Perfil + cuentas bancarias |
| `coa` | Plan de cuentas (PUC) |
| `dashboard_data` | KPIs + caja viva |
| `tags_taxes` | Etiquetas e impuestos |
| `cartera` | CXC / CXP |
| `inventory` | Activos / inventario |
| `control_tower` | Multi-entidad B2B |
| `hub` | Project Hub |
| `hr` | RRHH / nómina / documentos |
| `org` | Organigrama |
| `zero_coa` | Kernel contable |
| `module_flags` | Feature flags remotos |

### Patrones arquitectónicos

1. **Zero-Impact Policy** — no modificar módulos completos; lo nuevo en carpetas nuevas.
2. **Registry SSOT** — un array en `moduleRegistry.js`; shell lo consume automáticamente.
3. **Driver pattern** — `fin_sys_core/*_driver.py` encapsula SQL.
4. **Event-driven accounting** — kernel emite eventos → asientos automáticos.
5. **Feature flags** — BD override del registry local vía `/module-flags`.

---

## 5. Contabilidad v2 — estado del desarrollo

### Objetivo

Reescribir el módulo 01–06 con arquitectura modular: hooks por panel + providers de contexto, sin tocar `App.jsx`.

### Estructura v2

```
contabilidad-v2/
├── ContabilidadApp.jsx           # Orquestador
├── engine/
│   ├── TenantProvider.jsx        # Labels por industria (estandar/educacion)
│   └── TransactionDraftProvider.jsx  # Borrador global TX [NUEVO]
├── hooks/
│   ├── useDashboardData.js       # Fetch unificado
│   └── useCalculator.js
├── modules/
│   ├── registro/RegistroForm.jsx [NUEVO]
│   ├── terceros/, cartera/, cuentas/, tags/, impuestos/, inventarios/
│   └── */use*.js
└── components/KPIBar.jsx, ContextPanel.jsx
```

### Implementado

| Feature | Estado |
|---|---|
| KPI bar + switcher portafolios | ✅ |
| Panel contextual (7 tabs) | ✅ |
| Libro diario con paginación | ✅ |
| Calculadora rápida | ✅ |
| Registro TX vía POST `/transactions` | ✅ |
| `TransactionDraftProvider` (estado global borrador) | ✅ |
| `RegistroForm` extraído | ✅ |
| Vincular tercero → borrador (botón 🔗) | ✅ |
| Templates por industria | ✅ |

### Pendiente / placeholder

| Feature | Estado |
|---|---|
| Voz (Groq) | 🔵 Placeholder “Fase 3” |
| Borradores de voz | 🔵 Placeholder “Fase 3” |
| Categoría, método pago, TRM en UI | 🟡 En provider, no en form |
| Unificar `API` de `config.js` | 🟡 Hardcode `localhost:8000` en draft/form |
| Paridad total con v1 | 🟡 En progreso |
| Estrategia v1 → v2 (migración) | 🔵 Sin definir |

### Issues técnicos conocidos (v2)

- `TransactionDraftProvider.jsx` y `RegistroForm.jsx` usan `http://localhost:8000` en lugar de `API` de `frontend/src/config.js`.
- `ContabilidadApp.jsx` importa `API` pero no lo usa.
- Comentario “3-column grid” vs layout real (2 cols + diario abajo).

---

## 6. Trabajo en curso (git — sin commit)

| Archivo | Tipo | Descripción |
|---|---|---|
| `engine/TransactionDraftProvider.jsx` | Nuevo | Context: tipo, monto, tercero, evidencia, submit |
| `modules/registro/RegistroForm.jsx` | Nuevo | Formulario Módulo 01 desacoplado |
| `ContabilidadApp.jsx` | Modificado | Integra provider + form + refresh post-TX |
| `modules/terceros/TercerosPanel.jsx` | Modificado | Botón 🔗 vincula tercero al draft |
| `contabilidad-v2.css` | Modificado | Utilidades `cv2-input`, `cv2-btn`, grid |
| `AGENTS.md` | Modificado | Instrucciones agente |

---

## 7. Deuda técnica (DT-01 … DT-09)

| ID | Problema | Prioridad | Acción sugerida |
|---|---|---|---|
| DT-01 | Balance -$11.2M por TXs legacy sin `account_id` | Media | Script migración + backfill `account_id` |
| DT-02 | `@app.on_event("startup")` deprecado | Baja | Migrar a `lifespan` FastAPI |
| DT-03 | CXP/CXC parcial en KPIs CT | Media | Completar agregación en `control_tower_driver` |
| DT-04 | MD5 en `workspace_users` | **Alta** | Migrar a bcrypt |
| DT-05 | SHA-256 en `hub_users` | **Alta** | Migrar a bcrypt |
| DT-06 | Bundle ~1.7MB sin code splitting | Media | Lazy routes adicionales |
| DT-07 | Fuentes Kanban/TaskModal pendientes | Baja | Aplicar CSS classes |
| DT-08 | Integración contabilidad ↔ nómina | Media | Totalizar gasto nómina en CoA |
| DT-09 | Comprobante nómina → tablas contables | Baja | Hook al generar comprobante |

---

## 8. Endpoints huérfanos (no borrar)

Documentados en `AGENTS.md` — existen en `server.py` sin consumidor activo:

- `POST /api/hr/storage/sign-upload` — sustituido por upload directo JS
- `POST /api/hr/salary/calculate` — cálculo local en `SalaryTab.jsx`
- `PUT /api/hr/salary/v2/{user_id}` — beta sin uso
- `PUT /api/hr/profile/v2/{user_id}` — beta sin uso

---

## 9. Accesos y entorno

| Recurso | Valor |
|---|---|
| Workspace Hub | `37888f92-8bef-4528-b187-2064c6f0049c` |
| Supabase Project | `sciorfjvdqxvcwgvnmbv` (us-east-2) |
| Storage Bucket | `hr-docs` (público) |
| CT Login | `andres@finsys.os` / `admin123` |
| Hub OWNER | `andres@finsys.io` / `admin123` |

**Portafolios fijos (IDs 1–4):** Negocio A, Pegasus, Personal, Principal  
**Cuentas bancarias fijas (IDs 1–7):** no reasignar — actualmente **5 en BD** (alerta integridad)

---

## 10. Roadmap — opciones priorizadas

| Opción | Descripción | Valor |
|---|---|---|
| **A** | Módulo 09 Bot IA (WhatsApp + Groq) | Alto — ingestión móvil |
| **B** | Módulo 10 Trading NASDAQ (PnL) | Alto — inversiones |
| **C** | Kernel K1–K6 (emit automático en cada TX) | Crítico contable |
| **D** | Limpieza técnica (bcrypt, DT-01, lifespan) | Seguridad + estabilidad |
| **E** | Cerrar Contabilidad v2 Fase 2 | Paridad v1 + commit WIP |

---

## 11. Reglas para el agente / desarrollador

### Archivos PROHIBIDOS (sin aprobación explícita)

```
frontend/src/App.jsx
frontend/src/control-tower/*
fin_sys_core/database_driver.py
fin_sys_core/control_tower_driver.py
.env
Schema BD existente
```

### Protocolo antes de cambiar código

1. Listar archivos a modificar y el porqué.
2. Mostrar plan → esperar aprobación.
3. Un paso a la vez.
4. Resumir qué cambió, qué no, y riesgos.

### Agregar módulo nuevo

1. Carpeta en `frontend/src/<modulo>/`
2. Una entrada en `moduleRegistry.js`
3. Endpoints al **final** de `server.py` o nuevo router
4. **No editar** el switch de `main.jsx`

---

## 12. Flujos clave

### Registro de transacción (v2)

```
RegistroForm → TransactionDraftProvider.submitTransaction()
  → POST /transactions
  → dashboard.refreshTransactions() + refreshBalance()
```

### Comprobante nómina (RRHH)

```
HistorialTab "◈ Generar"
  → HTML → Supabase hr-docs (application/octet-stream)
  → POST /api/hr/documents/{user_id}
  → PUT /api/hr/payments/.../voucher?doc_id={id}
  → DocumentsTab muestra 🧾 COMPROBANTE
```

### Shell de navegación

```
GlobalLogin → Sidebar/HomeDashboard
  → moduleRegistry (lazy) → *App.jsx del módulo activo
  → feature flags /module-flags override registry
```

---

## 13. Documentos relacionados

| Archivo | Propósito |
|---|---|
| `AGENTS.md` | Reglas operativas para agente IA |
| `memory-bank/activeContext.md` | Contexto de sesión actual |
| `memory-bank/projectbrief.md` | Visión y módulos completados |
| `docs/architecture_design.md` | Diagramas y capas |
| `docs/implementaciones_futuras.md` | Roadmap M09–M13 |
| `docs/checkpoints.md` | Historial de sesiones |

---

*Última actualización: 13 Jul 2026 · health_check en vivo · Contabilidad v2 WIP*
