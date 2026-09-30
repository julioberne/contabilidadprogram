# 📝 FIN-SYS OS v2.0 — Historias de Usuario (Especificaciones Funcionales)

> **Versión**: 2.2 · **Última actualización**: 30 Sep 2026 (módulo 09 — Bot IA; el resto es de junio) · **Estado**: en producción
> El estado vivo de TODOS los módulos (incluidos RRHH, Contadores y Análisis) está en `CHECKLIST.md`; este documento solo lista historias.

Este documento define las especificaciones funcionales del sistema como Historias de Usuario con criterios de aceptación verificables. Cubre los módulos implementados y los planificados.

---

## ESTADO GENERAL DEL SISTEMA

| Módulo | Estado | Entregado |
|---|---|---|
| Módulo 01 — Registro Contable Universal | ✅ COMPLETO | Jun 2026 |
| Módulo 02 — Libro Diario Inteligente | ✅ COMPLETO | Jun 2026 |
| Módulo 03 — Cuentas Multi-Moneda (COP/USD) | ✅ COMPLETO | Jun 2026 |
| Módulo 04 — CXC/CXP (Cartera) | ✅ COMPLETO | Jun 2026 |
| Módulo 05 — Activos Patrimoniales | ✅ COMPLETO | Jun 2026 |
| Módulo 06 — Ingestión por Voz (Groq/Gemini) | ✅ COMPLETO | Jun 2026 |
| **Módulo 07 — Control Tower (Multi-Entidad B2B)** | ✅ COMPLETO | Jun 2026 |
| Módulo 08 — Trading / NASDAQ-100 | 🔵 PLANIFICADO | — |
| Módulo 09 — Bot IA (Telegram; WhatsApp pendiente) | ✅ EN PRODUCCIÓN — etapas A–G | Sep 2026 |
| Módulo 12 — Contadores | ✅ v1 | Sep 2026 |
| Módulo 13 — Análisis Inteligente | ✅ hitos 1–3 | Sep 2026 |

---

## 1. Módulo 01: Registro Contable Universal ✅

### Historia 1.1: Entrada Manual de Transacciones
> **Como** Administrador,
> **Quiero** registrar manualmente ingresos, egresos y transferencias usando un formulario web de alto contraste,
> **Para** documentar hechos financieros de forma precisa y rápida.

**Criterios de Aceptación** ✅ *Implementados*:
- Toggle triple: INGRESO / GASTO / TRANSFERENCIA
- Panel "Identificación de Tercero": búsqueda por nombre/NIT en terceros existentes o creación inline sin duplicar el módulo de terceros
- Panel colapsable de impuestos: IVA (19% aditivo), GMF (4x1000 deductivo), tasas personalizadas
- Panel CXC/CXP con fecha de vencimiento y plazo (Corto/Mediano/Largo)
- Panel de Activos con botón GUARDAR ACTIVO y flag de recurrencia
- Campo global "SUBIR COMPROBANTE" (PDF/imagen) en primer nivel del formulario
- Al presionar REGISTRAR, los balances se actualizan en tiempo real sin recargar página

### Historia 1.2: Gestión de Terceros sin Duplicados
> **Como** Contador,
> **Quiero** que el sistema busque terceros existentes antes de crear uno nuevo,
> **Para** evitar duplicados en el libro de contactos.

**Criterios de Aceptación** ✅ *Implementados*:
- En el panel de Tercero: campo de búsqueda que filtra por nombre o número de ID
- Si el tercero existe: se despliega lista para seleccionar
- Si no existe: formulario inline de creación (no redirige a otro módulo)
- Módulo de "Terceros" independiente para gestión CRUD completa de contactos

---

## 2. Módulo 02: Libro Diario Inteligente ✅

### Historia 2.1: Pestañas Multi-Portafolio
> **Como** Contador,
> **Quiero** alternar entre portafolios (Negocio A, Jardín Pegasus, etc.) usando pestañas,
> **Para** revisar movimientos de cada negocio de forma aislada.

**Criterios de Aceptación** ✅ *Implementados*:
- Pestañas monospaced con bordes cuadrados sobre la tabla del libro diario
- Al hacer clic, filtra filas al portafolio seleccionado inmediatamente
- Columnas en orden: Tipo · Valor · Concepto · ID Tercero · Fecha · Vencimiento · Cuenta · Categoría · Evidencia

### Historia 2.2: Edición Inline Estilo Excel
> **Como** Administrador,
> **Quiero** hacer doble clic en cualquier celda del libro diario para editarla directamente,
> **Para** corregir errores sin abrir formularios separados.

**Criterios de Aceptación** ✅ *Implementados*:
- Doble clic convierte la celda en `<input>` o `<select>`
- Enter/blur guarda vía `PUT /api/transactions/{id}` y actualiza saldos inmediatamente
- Escape aborta la edición sin guardar cambios

### Historia 2.3: Indicadores de Auditoría
> **Como** Auditor Fiscal,
> **Quiero** ver indicadores visuales de georreferenciación y comprobantes,
> **Para** verificar que cada transacción tiene sustento de auditoría.

**Criterios de Aceptación** ✅ *Implementados*:
- Columna "Evidencia": botón `[Ver]` que abre PDF/imagen en modal
- Columna "Lugar": enlace `[Maps]` si la transacción tiene coordenadas lat/lon

---

## 3. Módulo 03: Cuentas Multi-Moneda (COP/USD) ✅

### Historia 3.1: Gestión de Cuentas Financieras
> **Como** Tesorero,
> **Quiero** gestionar múltiples cuentas (Bancolombia, Nequi, Davivienda Crédito, USDT),
> **Para** tener el balance real de cada cuenta bancaria.

**Criterios de Aceptación** ✅ *Implementados*:
- Tipos: Ahorros, Corriente, Crédito, Crypto, Efectivo, Billetera
- Cuentas en COP y USD con balance inicial configurable
- Cuentas de crédito: balance se vuelve negativo al registrar gastos
- Recalculación automática de balances al insertar/modificar transacciones

### Historia 3.2: TRM Manual para Conversión de Divisas
> **Como** Contador,
> **Quiero** ingresar una TRM manual al hacer transferencias entre cuentas COP↔USD,
> **Para** que la conversión sea exacta y auditable.

**Criterios de Aceptación** ✅ *Implementados*:
- TRM requerida cuando cuenta origen y destino tienen monedas diferentes
- Caja Viva muestra balances COP y USD por separado sin distorsión

---

## 4. Módulo 06: Ingestión por Voz (IA + RAG) ✅

### Historia 4.1: Registro por Voz con Lenguaje Natural
> **Como** Dueño de Negocio,
> **Quiero** hablar libremente (*"Pagué luz por 80 mil"*) y que el sistema estructure la transacción,
> **Para** registrar gastos sin interrumpir mi flujo de trabajo.

**Criterios de Aceptación** ✅ *Implementados*:
- Botón micrófono graba audio (WebM/Opus) desde el navegador
- Backend envía a Groq Whisper (STT) → texto → Llama 3.3 (estructuración JSON)
- Búsqueda semántica RAG en Supabase pgvector para autocompletar terceros recurrentes
- Transacción se guarda en estado `BORRADOR` con indicador ámbar `[BORRADOR: FALTA NIT]`
- Consola editable: el texto transcrito se puede editar antes de procesar

### Historia 4.2: Confirmación de Borradores en 1 Click
> **Como** Administrador,
> **Quiero** ver la lista de borradores pendientes y confirmarlos con 1 click,
> **Para** oficializar transacciones de voz sin reescribir datos.

**Criterios de Aceptación** ✅ *Implementados*:
- Clic en borrador completo → botón CONFIRMAR directo
- Clic en borrador incompleto → auto-llena formulario resaltando campo faltante
- Sanitización: valores `"null"` o `"None"` de la IA quedan como campo vacío

---

## 5. Módulo 07: Control Tower — Contabilidad Multi-Entidad B2B ✅

### Historia 5.1: Registro e Inicio de Sesión en Control Tower
> **Como** Contador Externo o Socio,
> **Quiero** registrarme con mi propio usuario y contraseña en el módulo Control Tower,
> **Para** acceder a las entidades que me han asignado sin entrar como administrador principal.

**Criterios de Aceptación** ✅ *Implementados*:
- Pantalla de login/registro independiente de la app principal
- `workspace_users` tabla separada de usuarios del portafolio principal
- Credenciales de demo: `andres@finsys.os / admin123`
- 5 roles predefinidos: Super-Contador, Contador, Auditor Senior, Socia Inversora, Administrador

### Historia 5.2: Árbol Jerárquico de Entidades (5 Niveles)
> **Como** Super-Contador,
> **Quiero** organizar mis clientes y negocios en un árbol de entidades con hasta 5 niveles,
> **Para** gestionar holdings, empresas, sub-empresas, proyectos y tareas en una sola vista.

**Criterios de Aceptación** ✅ *Implementados*:
- Niveles soportados: HOLDING → EMPRESA → SUB_EMPRESA → PROYECTO → TAREA
- Árbol expansible/colapsable con indicador de estado (AL DÍA, ALERTA)
- Crear entidad desde cualquier nodo con formulario modal
- Eliminar con confirmación (CASCADE a hijos en BD)
- Cada entidad puede vincularse a un `portfolio_id` del sistema principal

### Historia 5.3: KPIs Consolidados por Entidad
> **Como** Socia Inversora,
> **Quiero** ver los KPIs consolidados (ingresos, egresos, balance, CXC) de una entidad seleccionada incluyendo todas sus sub-entidades,
> **Para** tener una visión financiera de todo mi portafolio sin revisar cada empresa individualmente.

**Criterios de Aceptación** ✅ *Implementados*:
- 5 KPI Cards: Caja Total · ING vs EGR (mini-gráfica) · CXC Pendiente · Aprobaciones · Sub-Entidades
- Query recursiva CTE que suma portfolios de toda la jerarquía descendiente
- KPI del Holding consolidado = $42.222.500 balance neto (dato real verificado)

### Historia 5.4: Cola de Aprobaciones
> **Como** Gerente,
> **Quiero** recibir solicitudes de aprobación de gastos de mis colaboradores y aprobarlas/rechazarlas desde el CT,
> **Para** mantener control sobre desembolsos sin estar en el sistema principal.

**Criterios de Aceptación** ✅ *Implementados*:
- Crear solicitud con descripción y monto desde cualquier entidad
- Filtrar por PENDIENTE / APROBADO / RECHAZADO
- Aprobar o rechazar con nota opcional
- Badge rojo con conteo en el botón de aprobaciones

### Historia 5.5: Inventario de IDs y Documentos Legales
> **Como** Contador Externo,
> **Quiero** registrar los NITs, RUTs, licencias y contratos de cada entidad cliente,
> **Para** tener un inventario centralizado de documentos con alertas de vencimiento.

**Criterios de Aceptación** ✅ *Implementados*:
- Categorías: FISCAL · LEGAL · BANCARIO · COMERCIAL · OTRO
- Campo de fecha de vencimiento con alerta visual (⚠ VENCIDO en rojo, ⏰ próximo a vencer en ámbar)
- Filtro por categoría
- Datos demo: Licencia MEN de Pegasus vencida detectada automáticamente

### Historia 5.6: Gestión de Colaboradores con Permisos Dinámicos
> **Como** Administrador,
> **Quiero** asignar colaboradores a entidades con roles y permisos personalizados,
> **Para** controlar quién puede ver el libro, aprobar gastos o gestionar usuarios.

**Criterios de Aceptación** ✅ *Implementados*:
- Permisos: `ledger` / `reports` / `users` / `approvals` (booleanos independientes)
- Presets: Super-Contador, Contador, Auditor, Colaborador, Cliente
- Matriz visual de permisos al asignar o ver un colaborador
- No se puede asignar un usuario que ya es miembro de esa entidad

### Historia 5.7: Transacciones Rápidas desde Control Tower
> **Como** Contador,
> **Quiero** registrar una transacción de una entidad cliente directamente desde el CT,
> **Para** no tener que cambiar al módulo principal para registrar movimientos de clientes.

**Criterios de Aceptación** ✅ *Implementados*:
- Modal pop-up embebido en CTSidePanel (no nueva pestaña)
- Campos: Entidad, Tipo, Monto, Concepto, Categoría, Método de Pago, Tercero
- Se registra en la tabla `transactions` vinculada al portafolio de la entidad
- Regresa al CT sin perder el contexto de navegación

---

## 6. Módulo 08: Trading / NASDAQ-100 🔵 (Planificado)

### Historia 6.1: Registro de Posiciones de Inversión
> **Como** Inversionista,
> **Quiero** registrar compras y ventas de acciones (LONG/SHORT),
> **Para** calcular mi PnL realizado/flotante y sus impactos contables.

**Criterios de Aceptación** (pendientes):
- Tabla `trading_positions`: ticker, precio_entrada, cantidad, TRM_apertura, tipo (LONG/SHORT)
- Realized PnL genera automáticamente un INGRESO/GASTO en el libro diario bajo categoría "Trading"
- Unrealized PnL desde API externa (Yahoo Finance / Alpha Vantage) — sin impacto contable hasta cierre
- Ingestión por voz: *"Compré 10 acciones de Apple a 180 dólares"*

---

## 7. Módulo 09: Bot IA por Telegram ✅ (en producción — etapas A–G)

> Specs con requisitos, decisiones y criterios verificables: `docs/specs/09-bot-ia/`. Referencia operativa: `docs/bot_ia.md`.
> Regla que gobierna todo el módulo: **el bot no adivina** (Regla 6b) y **nada toca la contabilidad sin confirmación humana**.

### Historia 7.1: Ingestión Móvil por Mensajería ✅
> **Como** Dueño de Negocio móvil,
> **Quiero** enviar un texto, una nota de voz o una foto por Telegram y que se convierta en un borrador de transacción,
> **Para** registrar gastos desde mi teléfono sin abrir la web.

**Criterios de Aceptación** (cumplidos):
- Solo chats vinculados a un usuario operan (`/vincular CODIGO`)
- Voz → Whisper → estructuración con el LLM de `GROQ_MODEL`; lo que no está explícito queda vacío
- Borrador en `transaction_drafts` (estado `BORRADOR`) con resumen y botones en el chat
- `Confirmar #N` o botón ✅ crea la transacción y su asiento por el pipeline oficial; chat y web no pueden confirmar dos veces
- Fotos, ubicación y etiquetas se adjuntan al borrador; bandeja web de borradores

**Pendiente**: WhatsApp (requiere dominio + TLS).

### Historia 7.2: Los SMS del banco se vuelven borradores ✅ (etapa 09.F)
> **Como** usuario que paga con Bancolombia,
> **Quiero** que cada SMS del banco (remitente 85540) llegue solo al bot como borrador,
> **Para** no tener que digitar mis movimientos.

**Criterios de Aceptación** (cumplidos, probado con un SMS real el 30-sep-2026):
- El teléfono reenvía el SMS a `POST /api/webhooks/sms` con un token propio; el poller lo convierte en ≤ 45 s
- Lectura por plantillas, sin IA: transferencia enviada, compra con tarjeta, transferencia recibida (dos variantes) y pago con QR
- Mi cuenta se identifica por id con sus últimos 4 dígitos (cuenta o tarjeta), registrados en 💳 Cuentas
- Un SMS que no es un movimiento no genera nada; uno con dinero y plantilla desconocida genera un borrador "PLANTILLA NUEVA" para revisar
- Sin duplicados si el teléfono reenvía el mismo SMS

**Pendiente**: muestras reales de retiro en cajero y compra por internet; HTTPS permanente (hoy túnel en el PC).

### Historia 7.3: Completar el borrador sin salir del chat ✅ (etapa 09.G)
> **Como** usuario del bot,
> **Quiero** responder al borrador con el concepto y el tercero,
> **Para** dejarlo listo para confirmar desde el teléfono.

**Criterios de Aceptación** (cumplidos):
- Responder (reply) con texto pone el concepto literal; `Tercero: nombre cc 123` asigna el tercero, en el mismo mensaje o en otra línea
- El documento manda: si ya existe se asigna aunque el nombre venga escrito distinto; nunca se duplica un tercero
- Con nombres parecidos el bot muestra botones y decide la persona; `➕ Crear nuevo` es explícito

### Historia 7.4: El bot reconoce a quién le transfiero ✅ (etapa 09.G §10 — falta la prueba real)
> **Como** usuario que le transfiere varias veces a la misma persona, a veces a cuentas distintas,
> **Quiero** que la siguiente transferencia llegue con el tercero ya puesto,
> **Para** solo escribir el concepto y confirmar.

**Criterios de Aceptación** (cumplidos en pruebas; pendiente CA-09G-13 con un SMS real):
- Un tercero es una sola ficha con varios medios de pago: cuentas, celulares, llaves y el nombre con que el banco lo escribe
- Tras asignar el tercero a un borrador de SMS aparece el botón **💾 Guardar**; nada se guarda sin ese toque
- El siguiente SMS con el mismo dato llega con el tercero puesto; otra cuenta de la misma persona se suma a la misma ficha
- Si el dato estaba en la ficha de otro tercero el botón es **🔁 Mover**; 💾 nunca pisa al dueño
- En la web, 👤 Terceros → ✎ abre la ficha completa con la sección "Cuentas, celulares y llaves"

### Historia 7.5: Leer comprobantes con un botón 🔵 (etapa 09.H — planificada)
OCR de recibos y vouchers con un botón dedicado en Telegram, límites de 5 MB por imagen y 50 lecturas diarias. Ver `docs/specs/09-bot-ia/09.H-ocr-comprobantes.md`.

---

## Reglas Transversales (No Negociables)

1. **Zero-Impact Policy**: Nuevas funcionalidades en nuevas rutas/archivos. No destruir lo existente.
2. **Tercero válido**: Ninguna transacción sin NIT/CC asociado (excepción: borradores de voz).
3. **BORRADOR primero**: Voz siempre genera borrador. El humano confirma.
4. **Estética Retro-Brutalista**: Todos los módulos principales usan paleta negro/blanco/mono.
5. **Control Tower**: Paleta ámbar/dorado exclusiva del módulo CT. No mezclar con módulo principal.
6. **Datos sensibles**: Las credenciales reales solo van en `.env` (nunca commiteadas).
