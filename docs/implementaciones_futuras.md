# 🚀 FIN-SYS OS v2.0 — Hoja de Ruta e Implementaciones Futuras

> **Última actualización**: 09 Junio 2026

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
| 08 | Trading / NASDAQ-100 | 🔵 PLANIFICADO | 🔴 Alta |
| 09 | Bot WhatsApp / Telegram | 🔵 PLANIFICADO | 🟡 Media |
| 10 | Reportes PDF / Excel | 🔵 PLANIFICADO | 🟡 Media |
| 11 | Facturación B2B desde CT | 🔵 PLANIFICADO | 🟡 Media |
| 12 | Despliegue en Producción (Dokploy) | 🔵 PLANIFICADO | 🟡 Media |

---

## 🔵 Módulo 08: Panel de Trading / NASDAQ-100 *(Prioridad Alta)*

Permite llevar el registro de inversiones financieras en activos bursátiles, integrando su valoración con la caja contable.

### Características Clave:
- **Tabla `trading_positions`**: ticker, precio_entrada (USD), cantidad, TRM_apertura, tipo (LONG/SHORT)
- **Realized PnL**: Al cerrar posición → genera `INGRESO` o `GASTO` automático en el libro diario bajo categoría "Trading"
- **Unrealized PnL**: Consulta periódica a Yahoo Finance / Alpha Vantage — visualización sin impacto contable oficial
- **Conversión a COP**: `PnL_COP = PnL_USD × TRM_salida`
- **Ingestión por voz**: *"Compré 10 acciones de Apple a 180 dólares con TRM de 4200 pesos"*

### Integraciones Requeridas:
- API financiera (Yahoo Finance o Alpha Vantage) para precio actual
- Tabla `trading_positions` nueva en Supabase
- Endpoint `/api/trading/positions` (GET, POST, PUT — cierre)

---

## 🔵 Módulo 09: Bot de Mensajería (WhatsApp / Telegram)

Extensión móvil del motor de voz para ingestión de transacciones desde el teléfono.

### Características Clave:
- Webhook FastAPI integrado con Twilio Gateway
- Flujo: OGG/AAC (WhatsApp) → Groq Whisper STT → Llama 3.3 → BORRADOR en Supabase
- Respuesta automática al usuario con resumen del borrador creado
- Confirmación por mensaje de texto: *"Confirmar #42"* → officializa la transacción

### Integraciones Requeridas:
- Cuenta Twilio con número de WhatsApp Business
- Endpoint `/api/bot/webhook` con firma HMAC de Twilio
- Tabla `bot_sessions` para manejar estados de conversación multi-turno

---

## 🔵 Módulo 10: Reportes PDF / Excel por Entidad

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

### Media Prioridad:
3. **CT: Vincular proyectos/tareas a portafolios**: Crear portafolios específicos para niveles 4 y 5 del árbol CT.
4. **CT: Paginación en árbol grande**: Lazy-loading cuando el árbol supere 50 nodos.
5. **CT: KPIs históricos**: Comparativa mes actual vs mes anterior.
6. **Buscador global**: Un campo de búsqueda que abarque transacciones, terceros y entidades CT.

### Baja Prioridad:
7. **Modo oscuro/claro**: Toggle de paleta en el módulo principal (el CT ya usa su paleta ámbar).
8. **2FA**: Autenticación de dos factores para workspace_users del CT.
9. **Audit log**: Tabla `action_logs` que registre quién hizo qué cambio y cuándo.
