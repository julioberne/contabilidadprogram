# 🏁 Manual de Verificación y Uso — FIN-SYS OS v2.0

> **Última actualización**: 09 Junio 2026
> Esta guía detalla cómo iniciar, verificar y operar el sistema completo en localhost.

---

## 🏛️ Qué está construido

| Módulo | Descripción | Estado |
|---|---|---|
| Módulo 01 | Registro Contable Universal (formulario + paneles colapsables) | ✅ |
| Módulo 02 | Libro Diario Inteligente (tabla multi-portafolio + edición inline) | ✅ |
| Módulo 03 | Cuentas Multi-Moneda COP/USD + Perfil de Usuario | ✅ |
| Módulo 04 | Cartera CXC/CXP con fechas de vencimiento | ✅ |
| Módulo 05 | Activos Patrimoniales + recurrencia | ✅ |
| Módulo 06 | Ingestión por Voz (Groq Whisper + Llama 3.3 + RAG) | ✅ |
| **Módulo 07** | **Control Tower — Contabilidad Multi-Entidad B2B** | **✅** |

**Stack técnico:**
- Backend: FastAPI (`server.py`) en `:8000`
- Frontend: Vite + React (`frontend/`) en `:5173`
- BD: PostgreSQL 17 en Supabase (cloud, us-east-2)
- IA: Groq Cloud (Whisper + Llama 3.3) + Gemini API (fallback)

---

## 🧪 1. Pruebas Unitarias Automáticas

```bash
python -m pytest fin_sys_core/test_core.py -v
# o
python fin_sys_core/test_core.py
```

**Resultado esperado**: `Ran 5 tests in ~0.001s — OK`

---

## 🔌 2. Variables de Entorno (`.env`)

Crear/verificar el archivo `.env` en la raíz del proyecto:

```env
# IA
GEMINI_API_KEY=tu_api_key_de_gemini
GROQ_API_KEY=gsk_...

# PostgreSQL Supabase (Transaction Pooler)
DB_HOST=aws-0-us-east-2.pooler.supabase.com
DB_PORT=5432
DB_NAME=postgres
DB_USER=postgres.sciorfjvdqxvcwgvnmbv
DB_PASSWORD=<ver .env local>
```

---

## 🚀 3. Arranque Local

### Terminal 1 — Backend FastAPI
```bash
# Desde la raíz: contabilidadprogram/
python server.py
```
Levanta en `http://127.0.0.1:8000`. Inicializa todas las tablas automáticamente al arrancar.

### Terminal 2 — Frontend React
```bash
# Desde: contabilidadprogram/frontend/
npm run dev
```
Levanta en `http://localhost:5173`

### Health Check completo:
```bash
python scripts/health_check.py
```

---

## 📱 4. Navegación de la Aplicación

Al abrir `http://localhost:5173` se muestra la barra de navegación superior con **3 botones**:

| Botón | Descripción |
|---|---|
| `APP` | Módulos 1–6 (contabilidad principal) |
| `TEST COA` | Módulo de prueba del Catálogo de Cuentas |
| `⬡ CONTROL TOWER` | Módulo 07 — Gestión Multi-Entidad B2B |

---

## 📊 5. Módulos Principales (APP)

### Módulo 01 — Registro de Transacciones
1. Seleccionar portafolio (Negocio A, EMPRESA INFANTIL PEGASUS, etc.)
2. Toggle: **INGRESO** / **GASTO** / **TRANSF**
3. Ingresar Monto y Concepto
4. Expandir paneles opcionales:
   - **[TERCERO]** — buscar o crear NIT/CC
   - **[%] IMPUESTOS** — IVA, GMF, propina, personalizados
   - **[CARTERA]** — CXC/CXP con fecha de vencimiento
   - **[ACTIVOS]** — registrar activo patrimonial
5. Subir comprobante (PDF/imagen) en "SUBIR COMPROBANTE"
6. Click **REGISTRAR TRANSACCIÓN ✅**

### Módulo 02 — Libro Diario
- **Pestañas**: Seleccionar portafolio para filtrar transacciones
- **Edición inline**: Doble clic en cualquier celda para editar → Enter para guardar
- **Columnas**: Tipo · Valor · Concepto · Tercero · Fecha · Cuenta · Categoría · Evidencia

### Módulo 06 — Ingestión por Voz
1. Click en botón micrófono `🎙️`
2. Hablar libremente: *"Compré cafés por 25 mil pesos en efectivo"*
3. Click `⏹️` para detener
4. Click **⚡ PROCESAR CON IA**
5. El borrador aparece en la bandeja con estado ámbar `[BORRADOR]`
6. Click en borrador → formulario auto-llenado → completar campos faltantes → **REGISTRAR**

---

## ⬡ 6. Control Tower — Guía de Uso

### Login
1. Click **⬡ CONTROL TOWER** en la barra superior
2. Ingresar credenciales:
   - Admin: `andres@finsys.os` / `admin123`
   - Contadora: `maria@finsys.os` / `maria2024`
   - Auditor: `carlos@finsys.os` / `auditor123`
   - Socia: `sofia@finsys.os` / `socia2024`
   - Director: `diego@finsys.os` / `admin2024`

### Árbol de Entidades (Zona Central)
- Click en `▶` para expandir/colapsar nodos
- Click en el nombre de la entidad para seleccionarla
- Al seleccionar: KPIs se actualizan arriba, Panel Lateral muestra acciones
- Botón **+ NUEVA ENTIDAD** → formulario modal para crear sub-nodo

### KPI Cards (Zona Superior)
Al seleccionar una entidad, se muestran 5 KPIs consolidados de toda su jerarquía:
- **💰 Caja Total**: Balance neto (ingresos - egresos) de todos los portafolios vinculados
- **📈 ING vs EGR**: Mini-gráfica de barras
- **📋 CXC Pendiente**: Deudas por cobrar
- **🔔 Aprobaciones**: Pendientes de revisión
- **🏢 Sub-Entidades**: Cantidad de nodos hijos directos

*KPIs verificados (Holding consolidado): $68.575.000 ingresos · $26.352.500 egresos · **$42.222.500 balance***

### Panel Lateral — 4 Acciones
1. **🔔 Aprobaciones** — Ver cola, crear solicitud, aprobar/rechazar con nota
2. **🪪 Inventario IDs** — Ver NITs, licencias, contratos. Las entradas vencidas aparecen en rojo ⚠
3. **👥 Colaboradores** — Ver y asignar usuarios a la entidad con matriz de permisos
4. **⚡ Registrar TX** — Modal pop-up para registrar transacción rápida de la entidad

### Botón "Volver" (⬅)
Regresa al módulo principal sin perder los datos de la app.

---

## 🔧 7. Estabilidad y Fixes Aplicados

| Fix | Descripción |
|---|---|
| `MediaRecorder` Chrome | timeslice 250ms + cascada de códecs Opus/WebM/OGG |
| Audio vacío | Validación <1KB antes de enviar al backend |
| `"null"` de IA | Sanitización: campos null quedan vacíos en formulario |
| CXC en KPIs CT | Query aislada en try/except — no rompe KPIs si tabla no existe |
| Balance Efectivo | Transacciones legacy sin `account_id` — deuda técnica documentada |
| DeprecationWarning | `on_event("startup")` — pendiente migrar a `lifespan` |

---

## 🗃️ 8. Datos Sintéticos Disponibles (CT Seeded)

Ejecutados en `scratch/ct_seed_data.py`. Estado actual en Supabase:

### Árbol de Entidades (7 nodos)
```
🏢 Mi Holding Principal         [HOLDING · AL DÍA]   portfolio: N/A (consolida)
├── 🏭 Jardín Infantil Pegasus  [EMPRESA · AL DÍA]   portfolio: EMPRESA INFANTIL PEGASUS
│   └── 🏗️ Sede Norte — Pegasus [SUB_EMPRESA · AL DÍA]
├── 🏭 Consultora Digital SAS   [EMPRESA · ALERTA]   portfolio: Negocio A
│   └── 📁 Proyecto ERP         [PROYECTO · AL DÍA]
│       └── 📄 Fase 1: Req.     [TAREA · AL DÍA]
└── 🏭 Constructora Norte SAS   [EMPRESA · ALERTA]   portfolio: Negocio Principal
```

### Resource IDs con Alertas
| Entidad | ID | Estado |
|---|---|---|
| Jardín Pegasus | Licencia Operación MEN | ⚠️ VENCIDA (2025-06-30) |
| Consultora Digital | Contrato Proyecto Minero | ⚠️ VENCIDO (2025-01-31) |
| Todas | NIT, RUT, Cuentas | ✅ Vigente |

---

## 📁 9. Estructura de Archivos Clave

```
contabilidadprogram/
├── server.py                       ← API FastAPI central (~ 38KB)
├── .env                            ← Credenciales (NO commitear)
├── CHECKLIST.md                    ← Health Check de inicio de sesión
├── fin_sys_core/
│   ├── database_driver.py          ← Conexión + CRUD módulos 1–6
│   ├── control_tower_driver.py     ← Control Tower: 5 tablas
│   ├── ai_engine.py                ← Groq/Gemini + RAG + pgvector
│   ├── ledger_math.py              ← Caja Viva + Pockets
│   ├── tax_motor.py                ← IVA + GMF + personalizados
│   ├── coa_test_module.py          ← Pruebas Catálogo de Cuentas
│   └── test_core.py                ← Suite 5 tests unitarios
├── frontend/src/
│   ├── App.jsx                     ← Módulos 1–6 (SPA principal)
│   ├── CoaTest.jsx                 ← Test COA
│   ├── main.jsx                    ← Router: APP | COA | CT
│   └── control-tower/
│       ├── ControlTowerApp.jsx     ← Raíz del módulo CT
│       ├── hooks/useControlTower.js← Estado global CT
│       └── components/
│           ├── CTTopBar.jsx
│           ├── CTLoginRegister.jsx
│           ├── CTKpiCards.jsx
│           ├── CTEntityTree.jsx
│           ├── CTSidePanel.jsx
│           ├── CTApprovalsCenter.jsx
│           ├── CTResourceIds.jsx
│           └── CTCollaborators.jsx
├── docs/                           ← Documentación actualizada
│   ├── checkpoints.md              ← Bitácora de hitos
│   ├── user_stories.md             ← Historias de usuario
│   ├── database_schema.md          ← 15 tablas documentadas
│   ├── api_spec.md                 ← Todos los endpoints
│   ├── architecture_design.md      ← Diagramas de arquitectura
│   ├── implementaciones_futuras.md ← Roadmap y backlog
│   ├── reglas_proyecto.md          ← Reglas del proyecto
│   ├── design_system.md            ← Sistema de diseño brutalista
│   └── walkthrough.md              ← Este archivo
├── scripts/
│   └── health_check.py             ← Validación completa del sistema
└── scratch/
    └── ct_seed_data.py             ← Seed datos Control Tower
```
