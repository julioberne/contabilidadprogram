# 📌 Bitácora de Checkpoints — FIN-SYS OS v2.0

> **Última actualización**: 09 Junio 2026, 23:00 COT
> Este documento es la memoria oficial de trabajo del proyecto. Registra todos los hitos alcanzados en orden cronológico y el estado actual del sistema.

---

## 📅 Hitos Completados

### Hito 1 — Planificación y Diseño Arquitectónico
**Fecha**: 01–02 Junio 2026
- Definición del estilo visual "Retro-Brutalista" (IBM Plex Mono, bordes 2px, esquinas 0px)
- Arquitectura desacoplada: `fin_sys_core` (Python puro) + FastAPI + React/Vite
- Base de datos: PostgreSQL en Supabase (proyecto `FIN-SYS OS v2.0`, región us-east-2)
- Motor de voz: Bucle Conversacional con Gemini/Groq + RAG con pgvector
- **Docs creados**: `design_system.md`, `database_schema.md`, `api_spec.md`, `architecture_design.md`, `user_stories.md`, `reglas_proyecto.md`, `checkpoints.md`

---

### Hito 2 — Núcleo Matemático y Pruebas Unitarias
**Fecha**: 01 Junio 2026
- `tax_motor.py`: IVA 19%, GMF 4x1000, tasas personalizadas (aditivas/deductivas)
- `ledger_math.py`: Caja Viva, validación de Pockets, alertas de insolvencia patrimonial
- `test_core.py`: Suite de 5 pruebas unitarias automáticas. Resultado: `OK (5/5)`

---

### Hito 3 — Backend FastAPI + Motor de Voz (RAG + Gemini/Groq)
**Fecha**: 02 Junio 2026
- `database_driver.py`: Conexión PostgreSQL/Supabase, init de tablas, CRUD completo
- `ai_engine.py`: Gemini Multimodal + Groq Whisper STT + Llama 3.3 para estructuración JSON
- `server.py`: Servidor FastAPI con esquemas Pydantic, endpoints REST
- Endpoint `/api/transactions/voice`: recibe audio, transcribe, clasifica, guarda como BORRADOR
- Búsqueda semántica RAG con pgvector para autocompletar terceros recurrentes

---

### Hito 4 — Frontend Brutalista Completo (MVP Visual)
**Fecha**: 02 Junio 2026
- `App.jsx`: SPA completa con Vite + React + TailwindCSS brutalista
- Caja Viva con KPIs en tiempo real (Ingresos / Egresos / Balance / Patrimonio)
- Módulo 01: Formulario de registro manual con toggle INGRESO/GASTO/TRANSFERENCIA
- Módulo 02: Tabla libro diario con filtro por portafolio
- Widget de Micrófono integrado (Web Audio API, MediaRecorder, Opus WebM)
- Bandeja de Borradores con estados `BORRADOR` / `COMPLETO` en ámbar/verde

---

### Hito 5 — Estabilidad, Validaciones y Fixes de Voz
**Fecha**: 02–03 Junio 2026
- Fix `MediaRecorder` Chrome: timeslice 250ms + cascada de códecs Opus/WebM/OGG
- Validación de audio vacío (<1KB) antes de enviar al backend
- Sanitización de `"null"` / `"None"` de la IA en formularios
- Formateo detallado de errores JSON de FastAPI (eliminado `[object Object]`)

---

### Hito 6 — Perfil de Usuario y Cuentas Multi-Moneda (COP/USD)
**Fecha**: 03 Junio 2026
- Tablas `user_profiles` y `user_accounts` en Supabase + modo simulación
- Columnas nuevas en `transactions`: `account_id`, `dest_account_id`, `trm`, `transaction_currency`
- Caja Viva separada por moneda (COP / USD apilados)
- `recalcular_saldos_cuentas()`: recalcula balances recursivamente al insertar/editar
- Perfil editable inline: Nombre, Email, Cargo con avatar pixelado procedural
- Tipos de cuenta: Ahorros, Corriente, Crédito (balance negativo), Crypto, Efectivo, Billetera
- TRM manual obligatoria en transferencias COP↔USD

---

### Hito 7 — Módulo 01 Expandido: Paneles Colapsables Completos
**Fecha**: 03 Junio 2026
- Panel `IDENTIFICACIÓN DE TERCERO`: búsqueda de terceros existentes + creación inline sin duplicar módulo
- Panel `[%] IMPUESTOS Y TASAS OCULTAS`: IVA, GMF, Propina, tasas dinámicas personalizadas
- Panel `CARTERA (CXC / CXP)`: vincula cuentas por cobrar/pagar a transacciones con plazo y vencimiento
- Panel `GESTIÓN DE ACTIVOS`: nombre, valor, etiqueta, flag recurrente, botón GUARDAR ACTIVO
- Tabla `assets` creada en Supabase automáticamente

---

### Hito 8 — Evidencia Global y Edición Estilo Excel
**Fecha**: 04 Junio 2026
- Campo "SUBIR COMPROBANTE" elevado a nivel global del Módulo 01 (aplica a cualquier TX, no solo activos)
- Edición inline: doble clic en celda del Libro Diario → campo editable → `PUT /api/transactions/{id}`
- Botón `GUARDAR ACTIVO` con validación y colapso automático del panel
- `evidence_file_path` en esquema Pydantic y en tabla `transactions` de Supabase
- Datos sintéticos: botón `⚡ SEMILLAR` en barra superior para poblar datos de prueba
- Alertas de insolvencia patrimonial: banner rojo brutalista animado si patrimonio < 0

---

### Hito 9 — Limpieza y Reorganización del Workspace
**Fecha**: 04 Junio 2026
- Eliminados todos los scripts de debug temporales del directorio `scratch/`
- Actualizada documentación en `docs/` para alinear con el código real
- Creado y publicado el Skill `multi-currency-ledger-setup` en `.agents/skills/`
- `coa_test_module.py` añadido a `fin_sys_core/` para pruebas del catálogo de cuentas
- Verificación de integridad de Supabase: schemas y migraciones sincronizados

---

### Hito 10 — Control Tower: Infraestructura Backend
**Fecha**: 09 Junio 2026
- `fin_sys_core/control_tower_driver.py` (24 KB): 5 tablas nuevas + CRUD completo
  - `workspace_users`: Usuarios del CT con roles dinámicos
  - `entities`: Árbol recursivo con `parent_id` auto-referencial (5 niveles)
  - `entity_members`: Asignación usuario↔entidad con permisos JSONB
  - `resource_ids`: Inventario de IDs/documentos clasificados por categoría
  - `approvals_queue`: Cola de aprobaciones de gastos con flujo PENDIENTE → APROBADO/RECHAZADO
- `server.py` extendido con router `/api/ct/*` (15 endpoints nuevos), zero-impact
- Seed automático: 1 holding + 2 empresas + usuario Super-Contador pre-cargados

---

### Hito 11 — Control Tower: Frontend Completo (Módulo Independiente)
**Fecha**: 09 Junio 2026
- `main.jsx` actualizado: navegación 3 pestañas (APP · TEST COA · ⬡ CONTROL TOWER)
- `ControlTowerApp.jsx`: Raíz del módulo, layout 3 zonas + orchestrator de modales
- `useControlTower.js`: Hook de estado global (session, entities, kpis, approvals, resources, members)
- **Zona 1** `CTKpiCards.jsx`: 5 KPI Cards con mini-gráfica ING vs EGR
- **Zona 2** `CTEntityTree.jsx`: Árbol recursivo con expand/collapse, modal de creación
- **Zona 3** `CTSidePanel.jsx`: Panel lateral con 4 acciones + modal TX embebido
- `CTTopBar.jsx`: Header con breadcrumb recursivo, selector entidad, user menu, botón "Volver"
- `CTLoginRegister.jsx`: Login + Registro independiente del sistema principal
- `CTApprovalsCenter.jsx`: Cola de aprobaciones CRUD completa
- `CTResourceIds.jsx`: Inventario de IDs con alertas de vencimiento
- `CTCollaborators.jsx`: Gestión de colaboradores con matriz de permisos y presets de roles
- Build Vite exitoso: `✓ 28 modules transformed in 2.91s` — **0 errores**

---

### Hito 12 — Control Tower: Datos Reales y Vinculación a Portafolios
**Fecha**: 09 Junio 2026
- Script `scratch/ct_seed_data.py`: seed completo en 7 pasos, 0 errores
- **Árbol final**: 7 entidades en 4 niveles (Holding → Empresa → Sub/Proyecto → Tarea)
- **Vinculación portfolio_id** via SQL directo Supabase MCP:
  - Jardín Infantil Pegasus → EMPRESA INFANTIL PEGASUS (portfolio 2)
  - Consultora Digital SAS → Negocio A (portfolio 1)
  - Constructora Norte SAS → Negocio Principal (portfolio 4)
- **5 workspace_users** con roles: Super-Contador, Contador Externo, Auditor Senior, Socia Inversora, Administrador
- **14 resource_ids** clasificados por entidad (NITs, licencias, contratos, cuentas bancarias)
- **7 aprobaciones**: 4 pendientes, 2 aprobadas, 1 rechazada
- **6 asignaciones** de colaboradores entre usuarios y entidades
- KPI verificado en vivo: Holding consolidado = **$42.222.500 COP balance neto**

---

## 📍 Estado Actual del Proyecto (09 Junio 2026)

### ✅ Completamente Funcional en Localhost:
| Componente | Versión | Puerto |
|---|---|---|
| Backend FastAPI | `python server.py` | `:8000` |
| Frontend React/Vite | `npm run dev` | `:5173` |
| Base de datos | Supabase PostgreSQL | Cloud (us-east-2) |
| Control Tower | ⬡ Módulo independiente | — |

### 🗂️ Estructura de Archivos Clave:
```
contabilidadprogram/
├── server.py                       ← API REST principal (15+ endpoints + 15 CT)
├── .env                            ← Variables de entorno (NO commitear)
├── fin_sys_core/
│   ├── database_driver.py          ← Conexión PostgreSQL, CRUD módulos 1-6
│   ├── control_tower_driver.py     ← Control Tower: 5 tablas nuevas, CRUD
│   ├── ai_engine.py                ← Gemini/Groq + RAG + pgvector
│   ├── ledger_math.py              ← Caja Viva, Pockets, insolvencia
│   ├── tax_motor.py                ← IVA, GMF, tasas personalizadas
│   ├── coa_test_module.py          ← Catálogo de cuentas (COA)
│   └── test_core.py                ← Suite de pruebas unitarias (5/5 OK)
├── frontend/src/
│   ├── App.jsx                     ← Módulos 1-6 (130K — app principal)
│   ├── CoaTest.jsx                 ← Test de catálogo de cuentas
│   ├── main.jsx                    ← Router manual: APP | COA | CT
│   └── control-tower/              ← Módulo 07 aislado
│       ├── ControlTowerApp.jsx
│       ├── hooks/useControlTower.js
│       └── components/ (8 archivos)
├── docs/                           ← Documentación actualizada
├── scripts/health_check.py         ← Validación de salud del sistema
└── scratch/ct_seed_data.py         ← Script de datos sintéticos CT
```

### 🔵 Próximos Módulos (Backlog Priorizado):
1. **Módulo 08**: Trading/NASDAQ-100 — PnL realizado/flotante, registro por voz
2. **Módulo 09**: Bot WhatsApp/Telegram — ingestión móvil vía Twilio + Groq
3. **Mejora CT**: Vincular `portfolio_id` a proyectos/tareas del árbol CT
4. **Mejora CT**: Reportes PDF/Excel por entidad del árbol
5. **Mejora CT**: Facturación B2B — generar facturas de servicios contables

### ⚠️ Deuda Técnica Conocida:
1. 🔴 **Balance Efectivo -$11.2M**: transacciones legacy registradas sin `account_id` asignado. Fix: retroactivo en BD.
2. 🟡 **Deprecation Warning**: `on_event("startup")` en `server.py` → migrar a `lifespan` handler de FastAPI.
3. 🟡 **CXP/CXC en KPIs CT**: La tabla `cxp_cxc_ledger` existe pero la vinculación a portafolios del CT está parcial (aislada con try/except, no rompe KPIs).
