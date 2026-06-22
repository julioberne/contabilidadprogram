# 🏁 Manual de Verificación y Uso — FIN-SYS OS v2.0

> **Última actualización**: 18 Junio 2026
> Esta guía detalla cómo iniciar, verificar y operar el sistema completo en localhost.
> Para el detalle de la sesión 11 Jun 2026, ver `docs/checkpoints.md` (Hito 13–14).
> **NOTA DE DUPLICIDAD**: Algunos endpoints documentados aquí también aparecen en `docs/api_spec.md`. El archivo `api_spec.md` es la fuente autoritativa de contratos de API. Este archivo se enfoca en flujos de usuario.

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
| **Módulo 08** | **Project Hub — Kanban, Notas, Calendario, Org Chart** | **✅** |
| **Módulo 08c** | **RRHH / Empresas — CompanyMapTab, Documentos, Historial, Comprobantes** | **✅ EN USO** |

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

Al abrir `http://localhost:5173` se muestra la barra de navegación superior con **4 botones**:

| Botón | Descripción |
|---|---|
| `APP` | Módulos 1–6 (contabilidad principal) |
| `TEST COA` | Módulo de prueba del Catálogo de Cuentas |
| `⧡ CONTROL TOWER` | Módulo 07 — Gestión Multi-Entidad B2B |
| `⧡ PROJECT HUB` | Módulo 08/08c — Hub colaborativo + RRHH |

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

## 👥 7. RRHH / Empresas — Módulo 08c (18 Jun 2026)

### Acceso
1. Click **⧡ PROJECT HUB** en la barra superior
2. Login: `andres@finsys.io` / `admin123`
3. En el sidebar izquierdo click **EMPRESAS** (antes RRHH)

### CompanyMapTab — Árbol Jerárquico
- Muestra el árbol Holding → Empresa → Subsidiaria → Proyecto
- Botones **⊕ Agregar**, **✏️ Editar**, **🗑️ Eliminar** nodo
- Al seleccionar un nodo se abre el panel de miembros de esa compañía
- Click en un miembro abre el **MemberProfile**

### MemberProfile — Pestañas Documentos + Historial

#### Pestaña Documentos (DocumentsTab)
- Vista drive-style: cards con ícono por categoría
- Comprobantes de nómina muestran 🧾u + label **COMPROBANTE**
- Click en tarjeta → modal de preview (HTML renderizado vía `atob()` si es data URL)
- Botón **⤓ Descargar** usa `downloadFile()` blob-based (no `<a href download>` directo)
- Botón **⬆ Subir** permite agregar PDFs/imágenes al perfil

#### Pestaña Historial (HistorialTab)
- Lista todos los registros de pago del miembro con monto, fecha, tipo
- **◈ Generar** en cada fila genera comprobante HTML de nómina:
  1. Construye HTML de comprobante con datos del pago
  2. Codifica con `btoa()` → `data:text/html;base64,...`
  3. Guarda en BD (`hr_documents.file_url`) via `POST /api/hr/documents/{user_id}`
  4. Vincula pago → documento via `PUT /api/hr/payments/{user_id}/{rec_id}/voucher?doc_id={id}`
  5. DocumentsTab recarga automáticamente y muestra tarjeta 🧾

### Bugs Corregidos Sesión 18 Jun 2026
| Bug | Fix |
|---|---|
| Parse error HistorialTab.jsx | Llave de cierre `};` faltante por merge corrupto |
| `mime type text/html is not supported` | Storage bloquea text/html; cambiado a `application/octet-stream`; luego migrado a data URL en BD |
| `No module named 'supabase'` | SDK Python no instalado; reemplazado por llamadas HTTP con `requests` |
| Descarga 404 | `<a href download>` → `downloadFile()` blob-based en FileCard y FileRow |
| Miniaturas comprobante | FileCard detecta `isVoucher` → muestra 🧾 + label COMPROBANTE |

---

## 🔧 8. Estabilidad y Fixes Aplicados (Historial)

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
├── server.py                       ← API FastAPI central (~77KB, 87+ endpoints)
├── .env                            ← Credenciales (NO commitear)
├── CHECKLIST.md                    ← Health Check de inicio de sesión
├── fin_sys_core/
│   ├── database_driver.py          ← Conexión + CRUD módulos 1–6
│   ├── control_tower_driver.py     ← Control Tower: 5 tablas
│   ├── hub_driver.py               ← Project Hub: 10 tablas hub_*
│   ├── hr_driver.py                ← RRHH: hr_members, hr_companies, hr_payment_records
│   ├── hr_documents_driver.py      ← RRHH Documentos: hr_documents
│   ├── ai_engine.py                ← Groq/Gemini + RAG + pgvector
│   ├── ledger_math.py              ← Caja Viva + Pockets
│   ├── tax_motor.py                ← IVA + GMF + personalizados
│   ├── coa_test_module.py          ← Pruebas Catálogo de Cuentas
│   └── test_core.py                ← Suite 5 tests unitarios
├── frontend/src/
│   ├── App.jsx                     ← Módulos 1–6 (SPA principal)
│   ├── CoaTest.jsx                 ← Test COA
│   ├── main.jsx                    ← Router: APP | COA | CT | HUB
│   ├── control-tower/
│   │   ├── ControlTowerApp.jsx     ← Raíz del módulo CT
│   │   ├── hooks/useControlTower.js← Estado global CT
│   │   └── components/ (8 archivos)
│   └── project-hub/
│       ├── ProjectHubApp.jsx       ← Raíz del módulo 08
│       ├── hooks/useProjectHub.js  ← Estado global Hub
│       └── features/
│           ├── tasks/               ← Kanban + Lista + TaskModal
│           ├── notes/               ← NotesApp + NoteEditor
│           ├── calendar/            ← CalendarApp + EventModal
│           ├── members/
│           │   ├── MembersList.jsx
│           │   ├── MemberProfile.jsx
│           │   ├── CompanyMapTab.jsx   ← Árbol jerárquico RRHH
│           │   ├── RRHHView.jsx
│           │   └── tabs/
│           │       ├── DocumentsTab.jsx ← Drive-style + preview comprobantes
│           │       └── HistorialTab.jsx ← Pagos + generación comprobantes
│           └── workspace/ (settings + EntityTree)
├── docs/                           ← Documentación actualizada
├── scripts/
│   ├── health_check.py
│   ├── session_maintenance.py
│   ├── seed_hub.py
│   └── cleanup_empty_workspace.py
└── scratch/
    └── ct_seed_data.py
```
