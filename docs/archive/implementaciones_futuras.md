# 🚀 FIN-SYS OS v2.0 — Hoja de Ruta e Implementaciones Futuras

> **Última actualización**: 18 Junio 2026

Este documento registra el backlog priorizado de módulos futuros y mejoras técnicas planificadas.

---

## Estado de Módulos

| # | Módulo | Estado | Prioridad |
|---|---|---|---|
| 01 | Registro Contable Universal | ✅ COMPLETO | — |
| 02 | Libro Diario Inteligente | ✅ COMPLETO | — |
| 03 | Cuentas Multi-Moneda (COP/USD) | ✅ COMPLETO | — |
| 04 | Cartera CXC/CXP | ✅ COMPLETO | — |
| 05 | Activos Patrimoniales | ✅ COMPLETO | — |
| 06 | Motor de Voz (Groq/Gemini + RAG) | ✅ COMPLETO | — |
| **07** | **Control Tower (Multi-Entidad B2B)** | **✅ COMPLETO** | — |
| **08** | **Project Hub (Kanban, Notas, Calendario, Org)** | **✅ COMPLETO** | — |
| **08c** | **RRHH / Empresas (CompanyMap, Documentos, Historial)** | **✅ EN USO** | — |
| 09 | Bot IA (WhatsApp/Telegram + Groq) | 🔵 PLANIFICADO | 🔴 Alta |
| 10 | Trading NASDAQ-100 (PnL, velas, heatmap) | 🔵 PLANIFICADO | 🔴 Alta |
| 11 | Reportes PDF / Excel | 🔵 PLANIFICADO | 🟡 Media |
| 12 | Facturación B2B desde CT | 🔵 PLANIFICADO | 🟡 Media |
| 13 | Despliegue en Producción (Dokploy) | 🔵 PLANIFICADO | 🟡 Media |

---

## 🔵 Módulo 09: Bot IA — WhatsApp / Telegram *(Prioridad Alta)*

Extensión móvil del motor de voz para ingestión de transacciones desde el teléfono.

### Características Clave:
- Webhook FastAPI integrado con Twilio Gateway
- Flujo: OGG/AAC (WhatsApp) → Groq Whisper STT → Llama 3.3 → BORRADOR en Supabase
- Respuesta automática al usuario con resumen del borrador creado
- Confirmación por mensaje de texto: *“Confirmar #42”* → officializa la transacción

### Integraciones Requeridas:
- Cuenta Twilio con número de WhatsApp Business
- Endpoint `/api/bot/webhook` con firma HMAC de Twilio
- Tabla `bot_sessions` para manejar estados de conversación multi-turno

---

## 🔵 Módulo 10: Trading NASDAQ-100 *(Prioridad Alta)*

Permite llevar el registro de inversiones financieras en activos bursátiles, integrando su valoración con la caja contable.

### Características Clave:
- **Tabla `trading_positions`**: ticker, precio_entrada (USD), cantidad, TRM_apertura, tipo (LONG/SHORT)
- **Realized PnL**: Al cerrar posición → genera `INGRESO` o `GASTO` automático en el libro diario bajo categoría "Trading"
- **Unrealized PnL**: Consulta periódica a Yahoo Finance / Alpha Vantage — visualización sin impacto contable oficial
- **Conversión a COP**: `PnL_COP = PnL_USD × TRM_salida`
- **Velas + Heatmap de portafolio**: Charts estilo Bloomberg
- **Ingestión por voz**: *"Compré 10 acciones de Apple a 180 dólares con TRM de 4200 pesos"*

### Integraciones Requeridas:
- API financiera (Yahoo Finance o Alpha Vantage) para precio actual
- Tabla `trading_positions` nueva en Supabase
- Endpoint `/api/trading/positions` (GET, POST, PUT — cierre)
- Carpeta UI nueva: `frontend/src/trading/`

---

## 🔵 Módulo 11: Reportes PDF / Excel por Entidad

Generación de informes contables descargables.

### Características Clave:
- Reporte de libro diario por portafolio con filtros de fecha y categoría
- Balance General y Estado de Resultados básico
- **Desde Control Tower**: Exportar libro de una entidad específica del árbol
- Formatos: PDF (weasyprint/reportlab) + Excel (openpyxl)

---

## 🔵 Módulo 11: Facturación B2B desde Control Tower

Permite al contador cobrar sus servicios a clientes externos directamente desde el CT.

### Características Clave:
- Generar factura de honorarios contables para una entidad cliente
- Plantilla PDF con logo, datos del contador, datos del cliente (de `entities`), valor y NIT
- Registro automático de CXC pendiente en el sistema principal
- Historial de facturas emitidas por entidad

---

## 🔵 Módulo 12: Despliegue en Producción (Dokploy + Supabase)

### Plan de Infraestructura:
```
VPS con Dokploy:
  ├── Nginx (proxy SSL, puerto 443)
  ├── React SPA (archivos estáticos, ruta /)
  └── FastAPI Container (Docker, ruta /api)

Supabase Cloud (ya activo):
  ├── PostgreSQL (us-east-2) — ya en uso en desarrollo
  ├── pgvector — ya habilitado para RAG
  └── Storage Bucket — para evidencias de comprobantes
```

### Pasos Pendientes:
1. Crear Dockerfile para el backend FastAPI
2. Configurar `docker-compose.yml` para desarrollo
3. Configurar variables de entorno de producción en Dokploy
4. Compilar frontend (`npm run build`) y configurar Nginx
5. Probar con dominio real + SSL (Let's Encrypt vía Dokploy)

---

## 🔧 Mejoras Técnicas Pendientes (Deuda Técnica)

### Alta Prioridad:
1. **Fix balance Efectivo -$11.2M**: Asignar `account_id` retroactivo a transacciones legacy con NULL. Script SQL directo.
2. **Migrar `on_event` a `lifespan`** en `server.py`: Eliminar DeprecationWarning de FastAPI.
3. **bcrypt para `workspace_users`** (DT-04): Reemplazar MD5 por bcrypt + JWT antes de producción.
4. **bcrypt para `hub_users`** (DT-05): Reemplazar SHA-256 por bcrypt + JWT.

### Media Prioridad:
5. **CT: Vincular proyectos/tareas a portafolios** (DT-03): Crear portafolios específicos para niveles 4 y 5 del árbol CT.
6. **CT: Paginación en árbol grande**: Lazy-loading cuando el árbol supere 50 nodos.
7. **CT: KPIs históricos**: Comparativa mes actual vs mes anterior.
8. **Buscador global**: Un campo de búsqueda que abarque transacciones, terceros y entidades CT.
9. **Code splitting** (FEAT-03): Bundle ~1.7MB → <500KB mediante lazy imports de módulos grandes.
10. **DT-08: Integración contabilidad-nómina**: Totalizar gasto nómina en Chart of Accounts (CoA) al generar pago RRHH.
11. **DT-09: Comprobante integrado con tablas contables**: Al generar comprobante, registrar automáticamente un GASTO en `transactions`.

### Baja Prioridad:
129. **Modo oscuro/claro**: Toggle de paleta en el módulo principal (el CT ya usa su paleta ámbar).
10. **2FA**: Autenticación de dos factores para workspace_users del CT.
11. **Audit log**: Tabla `action_logs` que registre quién hizo qué cambio y cuándo.
15. **DT-07: Tipografía Kanban/TaskModal**: CSS classes definidas pero no aplicadas correctamente en algunos estados.

---

## 🔧 Deuda Técnica — Sesión 18 Jun 2026

### DT-01: Balance Efectivo -$11.2M
3 transacciones legacy con `account_id = NULL`. Fix: script SQL asigna account_id retroactivo.
Estado: **PENDIENTE** · Impacto: alto (distorsiona caja viva).

### DT-04: MD5 en workspace_users → bcrypt
`workspace_users.password` usa MD5 (inseguro). Migrar a bcrypt antes de producción.
Estado: **PENDIENTE** · Archivo: `fin_sys_core/control_tower_driver.py` 🔴

### DT-05: SHA-256 en hub_users → bcrypt
`hub_users.password` usa SHA-256. Migrar a bcrypt + JWT.
Estado: **PENDIENTE** · Archivo: `fin_sys_core/hub_driver.py` 🔴

### DT-06: Bundle 1.7MB sin code splitting
El bundle de producción pesa 1.7MB. Meta: <500KB con lazy loading por módulo.
Ver FEAT-03 abajo.

### DT-08: Integración Contabilidad ↔ Nómina
Los pagos de nómina (`hr_payments`) NO generan transacciones automáticas en el libro contable.
**Plan**: Al `POST /api/hr/payments/{user_id}`, crear automáticamente un `GASTO` en la tabla `transactions`
con categoría "Nómina" y monto = neto del pago.
Estado: **PLANIFICADO** · Requiere aprobación antes de tocar `database_driver.py`.

### DT-09: Migrar cálculo de nómina de JS a backend
`SalaryTab.jsx` calcula salud, pensión, parafiscales y neto en JavaScript del cliente.
**Plan**: Activar `POST /api/hr/salary/calculate` (endpoint huérfano existente) y mover la lógica
a `fin_sys_core/hr_driver.py` para centralizar los cálculos y facilitar auditorías.
Estado: **PLANIFICADO** · Prerequisito de DT-08.

---

## ⚠️ ENDPOINTS HUÉRFANOS — Limpieza Pendiente

> Estos endpoints existen en `server.py` pero **no tienen consumidor activo**.
> **NO eliminar** hasta confirmar con el usuario. Documentar razón antes de remover.

| Endpoint | Razón Huérfana | Acción Sugerida |
|---|---|---|
| `POST /api/hr/storage/sign-upload` | Storage bucket bloquea `text/html`; reemplazado por data URL | Remover en sesión de limpieza |
| `POST /api/hr/salary/calculate` | Cálculo ocurre en `SalaryTab.jsx` (frontend) | Activar con DT-09 |
| `PUT /api/hr/salary/v2/{user_id}` | Versión beta sin uso | Remover o promover a v1 |
| `PUT /api/hr/profile/v2/{user_id}` | Versión beta sin uso | Remover o promover a v1 |

---

## FEAT-03: Code Splitting — Bundle <500KB

El bundle actual (1.7MB) incluye todos los módulos en un solo chunk.

### Plan de implementación:
```js
// vite.config.js — lazy chunks por módulo
const ControlTower = lazy(() => import('./control-tower/ControlTowerApp'));
const ProjectHub   = lazy(() => import('./project-hub/ProjectHubApp'));
const BotModule    = lazy(() => import('./bot/BotApp'));        // futuro
const TradingModule = lazy(() => import('./trading/TradingApp')); // futuro
```

### Metas:
- Chunk principal (`App`): <150KB
- Chunk CT: <200KB
- Chunk Hub (con 08c): <250KB
- **Total gzipped**: <500KB

Estado: **PLANIFICADO** · Prioridad: 🟡 Media (antes de despliegue producción)

---

## 🔴 KERNEL PARTIDA DOBLE — Gap Diagnosticado (21 Jun 2026)

> **Problema:** El motor de partida doble (`kernel_accounting.py`) está construido y testeado,
> pero **ningún módulo emite eventos hacia él**. La tabla `kernel_journal_entries` tiene 0 registros.
> Esto hace que el sistema sea "ciego" ante eventos económicos que no son efectivo inmediato.

### Diagnóstico: 5 Huecos Críticos

| # | Evento de Negocio | Qué pasa HOY | Qué FALTA |
|---|---|---|---|
| **H1** | Crear CXP (compra a crédito) | Se crea fila en `cxp_cxc_ledger` | Asiento: Db Mercancías / Cr Proveedores |
| **H2** | Crear CXC (venta a crédito) | Se crea fila en `cxp_cxc_ledger` | Asiento: Db Clientes / Cr Ingresos + IVA |
| **H3** | Pagar CXP (liquidar deuda) | Se reduce `remaining_balance` | Asiento: Db Proveedores / Cr Bancos |
| **H4** | Cobrar CXC (recibir pago) | Se reduce `remaining_balance` | Asiento: Db Bancos / Cr Clientes |
| **H5** | Transacción de caja | Se crea fila en `transactions` | Asiento según tipo (ingreso/egreso/transfer) |

### Componentes listos vs. faltantes

| Componente | Estado | Ubicación |
|---|---|---|
| `registrar_asiento()` | ✅ Funcional, validación Db=Cr | `kernel/kernel_accounting.py` |
| `kernel_event_bus` | ✅ 4 listeners activos, 0 emits | `kernel/kernel_event_bus.py` |
| `kernel_journal_entries` | ✅ Tabla + índices creados | PostgreSQL (0 registros) |
| `chart_of_accounts` (PUC) | ⚠️ Tabla existe, ¿tiene seed? | `database_driver.py:357` |
| Mapeo Categoría → Cuenta PUC | ❌ No existe | Necesita dict o tabla |
| `emit()` en endpoints | ❌ No existe | Agregar en `server.py` endpoints cartera + tx |

### Plan de Implementación (6 fases)

| Fase | Qué | Prerequisito | Esfuerzo |
|---|---|---|---|
| **K1** | Seed PUC básico colombiano en `chart_of_accounts` | Ninguno | 🟢 Bajo |
| **K2** | `emit()` al crear CXC/CXP en cartera | K1 | 🟢 Bajo (3 líneas) |
| **K3** | `emit()` al registrar abono/pago | K1 | 🟢 Bajo |
| **K4** | `emit()` al crear transacción de caja | K1 + mapeo categoría→cuenta | 🟡 Medio |
| **K5** | Tab "📒 LIBRO MAYOR" en frontend | K2-K4 | 🟡 Medio |
| **K6** | Widget ecuación contable (A=P+Pt) en dashboard | K5 | 🟢 Bajo |

### UX Recomendada: Invisible (v1)
El usuario no ve cambios en la interfaz. Los asientos se generan automáticamente al crear CXC/CXP,
registrar pagos, o crear transacciones. El resultado visible es:
- Un nuevo tab "📒 LIBRO MAYOR" para consultar asientos agrupados
- Un widget en el dashboard con la ecuación contable en tiempo real

Estado: **DIAGNOSTICADO** · Implementar en sesión futura dedicada al Kernel.
Documento completo: `artifacts/diagnostico_partida_doble.md`
