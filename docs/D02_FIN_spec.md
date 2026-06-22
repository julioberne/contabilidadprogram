# D02 FIN — Finanzas & Contabilidad · Spec Técnico

> **Versión:** 1.0 — 20 Jun 2026  
> **Estado:** ⚠️ PARCIAL — Funcional pero sin partida doble ni COA activo  
> **Propósito:** Documento de referencia para cualquier agente IA o desarrollador que trabaje en este módulo.  
> **Regla:** Leer este documento COMPLETO antes de modificar cualquier archivo del módulo.

---

## 📋 Resumen Ejecutivo

D02 FIN es el **núcleo contable** del ERP FIN-SYS OS. Toda acción económica de cualquier departamento eventualmente genera un asiento aquí. Hoy funciona como un registrador de gastos/ingresos con dashboard — le falta el motor de partida doble (Debe = Haber) y el COA funcional.

---

## 🗂️ Inventario de Archivos

### Backend

| Archivo | Tamaño | Función | Permiso |
|---------|--------|---------|---------|
| [server.py](file:///c:/Users/andre/OneDrive/Escritorio/programas/contabilidadprogram/server.py) | 88KB, 2176 líneas | Contiene TODOS los endpoints (FIN + CT + HR mezclados). Los de FIN están en líneas ~280-900 | 🟡 Solo agregar al final |
| [database_driver.py](file:///c:/Users/andre/OneDrive/Escritorio/programas/contabilidadprogram/fin_sys_core/database_driver.py) | 53KB, 1283 líneas | Driver de BD contable (CRUD portafolios, TXs, cuentas, COA, terceros) | 🔴 Solo con aprobación |
| [tax_motor.py](file:///c:/Users/andre/OneDrive/Escritorio/programas/contabilidadprogram/fin_sys_core/tax_motor.py) | 3.6KB, 103 líneas | Cálculos: IVA 19%, GMF 4x1000, impuestos custom | 🟢 Estable |
| [ledger_math.py](file:///c:/Users/andre/OneDrive/Escritorio/programas/contabilidadprogram/fin_sys_core/ledger_math.py) | ~2KB | Cálculo de Caja Viva, validación presupuesto pockets | 🟢 Estable |
| [incremental_balance.py](file:///c:/Users/andre/OneDrive/Escritorio/programas/contabilidadprogram/fin_sys_core/incremental_balance.py) | ~3KB | Cálculo incremental O(1) de saldos de cuentas bancarias | 🟢 Estable |
| [db_pool.py](file:///c:/Users/andre/OneDrive/Escritorio/programas/contabilidadprogram/fin_sys_core/db_pool.py) | ~2KB | Connection pool centralizado (psycopg2) | 🟢 Estable |
| [ai_engine.py](file:///c:/Users/andre/OneDrive/Escritorio/programas/contabilidadprogram/fin_sys_core/ai_engine.py) | ~8KB | Transcripción de voz (Groq Whisper) + estructuración IA (Llama/Gemini) | 🟢 Estable |

### Frontend

| Archivo | Tamaño | Función |
|---------|--------|---------|
| [App.jsx](file:///c:/Users/andre/OneDrive/Escritorio/programas/contabilidadprogram/frontend/src/App.jsx) | ~139KB | **TODO** el módulo contable en un archivo: formulario de registro, tabla de TXs, dashboard KPIs, gráficas, cuentas, portafolios, terceros, COA, perfil |
| [index.css](file:///c:/Users/andre/OneDrive/Escritorio/programas/contabilidadprogram/frontend/src/index.css) | ~15KB | Estilos retro-brutalistas del módulo contable |

> [!WARNING]
> `App.jsx` tiene ~139KB en un solo archivo. **Meta de desacoplamiento:** extraer a `frontend/src/modules/D02_FIN/` con sub-componentes.

---

## 📊 Tablas de Base de Datos (propiedad de D02)

| Tabla | Columnas clave | Filas (Jun 2026) | Nota |
|-------|---------------|-----------------|------|
| `portfolios` | id, name, industry_type, sub_industry_type | 4 | Negocio A, Pegasus, Personal, Principal |
| `user_profiles` | id, name, email, role, avatar_style | 1 | Perfil único del admin |
| `user_accounts` | id, name, type, currency, initial_balance, current_balance | 7 | Efectivo, Bancolombia, Nequi, Davivienda, Binance, etc. |
| `third_parties` | id, identification_type, identification_number, name, email, phone | ~10 | NIT/CC de terceros |
| `transactions` | id, portfolio_id, third_party_id, type, amount, concept, transaction_date, payment_method, category, tax_iva_*, tax_gmf_*, net_value, account_id, dest_account_id, trm, transaction_currency | 18 | INGRESO, GASTO, TRANSFERENCIA |
| `pockets` | id, portfolio_id, name, allocated_budget, current_balance | 0 | Sin uso activo |
| `cxp_cxc_ledger` | id, transaction_id, third_party_id, type, original_amount, remaining_balance, due_date, status | ~5 | CXC y CXP |
| `assets` | id, portfolio_id, name, purchase_value, purchase_date, is_passive_income_generator | 0 | Sin uso activo |
| `chart_of_accounts` | id, portfolio_id, code, name, account_type, parent_id, is_group | 0 | **VACÍO — problema crítico** |

> [!CAUTION]
> **`chart_of_accounts` está vacío.** La función `cargar_plantilla_coa()` existe pero nunca ha sido ejecutada por el usuario. Sin COA no hay contabilidad real ni estados financieros.

---

## 🔌 Endpoints HTTP (propiedad de D02)

### Portafolios
| Método | Ruta | Función | Línea |
|--------|------|---------|-------|
| GET | `/portafolios` | `get_portfolios()` | 286 |
| POST | `/portafolios` | `create_portfolio_endpoint()` | 301 |

### Saldos
| Método | Ruta | Función | Línea |
|--------|------|---------|-------|
| GET | `/caja-viva` | `get_caja_viva_balance()` | 314 |

### Transacciones
| Método | Ruta | Función | Línea |
|--------|------|---------|-------|
| GET | `/transacciones` | `list_transactions()` | 349 |
| POST | `/transacciones` | `create_manual_transaction()` | 363 |
| PUT | `/transacciones/{tx_id}` | `update_transaction_endpoint()` | 626 |

### IA / Voz
| Método | Ruta | Función | Línea |
|--------|------|---------|-------|
| POST | `/upload-evidence` | `upload_evidence_endpoint()` | 440 |
| POST | `/upload-voice-transaction` | `upload_voice_transaction()` | 458 |
| POST | `/upload-voice-transcribe` | `upload_voice_transcribe_only()` | 530 |
| POST | `/structure-transcript` | `structure_voice_transcript()` | 559 |

### Perfil
| Método | Ruta | Función | Línea |
|--------|------|---------|-------|
| GET | `/perfil` | `get_profile()` | 762 |
| PUT | `/perfil` | `update_profile()` | 770 |

### Cuentas Bancarias
| Método | Ruta | Función | Línea |
|--------|------|---------|-------|
| GET | `/cuentas` | `list_accounts()` | 784 |
| POST | `/cuentas` | `add_account()` | 792 |

### Plan de Cuentas (COA)
| Método | Ruta | Función | Línea |
|--------|------|---------|-------|
| GET | `/coa/{portfolio}` | `get_coa_tree()` | 801 |
| POST | `/coa/cargar-plantilla` | `load_coa_template()` | 814 |
| POST | `/coa/agregar-cuenta` | `add_coa_account()` | 836 |

### Terceros
| Método | Ruta | Función | Línea |
|--------|------|---------|-------|
| GET | `/terceros` | `get_third_parties()` | 864 |

### Utilidades
| Método | Ruta | Función | Línea |
|--------|------|---------|-------|
| POST | `/seed-synthetic-data` | `seed_synthetic_data()` | 657 |
| POST | `/reset-database` | `reset_database_endpoint()` | 743 |

### Dashboard
| Método | Ruta | Función | Línea |
|--------|------|---------|-------|
| GET | `/api/dashboard-data` | `dashboard_data()` | ~880 |

**Total:** ~20 endpoints de D02 FIN

---

## ⚙️ Funciones del Driver (database_driver.py)

| Función | Línea | Qué hace |
|---------|-------|---------|
| `init_db()` | 186 | Crea tablas si no existen, siembra datos por defecto |
| `registrar_transaccion(tx_data)` | 417 | Registra TX: busca/crea tercero, calcula impuestos, actualiza saldo cuenta |
| `obtener_transacciones(portfolio, limit, offset)` | 581 | Lista TXs con paginación y filtro por portafolio |
| `actualizar_transaccion(tx_id, update_data)` | 696 | Edita TX existente, recalcula saldos |
| `recalcular_saldos_cuentas(conn)` | 796 | Recalculación completa de saldos (fallback) |
| `obtener_perfil_usuario()` | 936 | Lee perfil del admin |
| `actualizar_perfil_usuario(data)` | 954 | Actualiza nombre/email/rol/avatar |
| `obtener_cuentas()` | 979 | Lista todas las cuentas bancarias con saldos |
| `crear_cuenta(data)` | 995 | Crea nueva cuenta bancaria |
| `reset_db()` | 1030 | Resetea TODAS las tablas (dev only) |
| `obtener_coa_tree(portfolio_name)` | 1111 | Retorna árbol COA de un portafolio (hoy: vacío) |
| `cargar_plantilla_coa(portfolio, template)` | 1144 | Inserta plantilla NIIF estándar en COA |
| `agregar_cuenta_coa(portfolio, data)` | 1192 | Agrega una cuenta individual al COA |
| `obtener_portafolios()` | 1216 | Lista portafolios activos |
| `crear_portafolio(name, industry)` | 1232 | Crea nuevo portafolio |
| `obtener_terceros()` | 1260 | Lista terceros registrados |

---

## 🧮 Motor de Impuestos (tax_motor.py)

```
IVA estándar Colombia = 19% (aditivo sobre base)
GMF (4x1000)          = 0.4% (deductivo en egresos bancarios)

Fórmula:
  net_value = base + IVA + custom_additive - GMF - custom_deductive
```

Soporta impuestos personalizados como tasa (%) o monto fijo, clasificados como ADDITIVE o DEDUCTIVE.

---

## 🏦 Flujo de una Transacción (actual)

```
1. Usuario llena formulario (o dicta por voz)
         │
2. Frontend envía POST /transacciones
         │
3. server.py → create_manual_transaction()
         │
4. tax_motor.py → calcula IVA/GMF si aplica
         │
5. database_driver.py → registrar_transaccion()
    ├── Busca o crea tercero en third_parties
    ├── Inserta en transactions
    ├── incremental_balance → actualiza saldo cuenta
    └── Si CXC/CXP → inserta en cxp_cxc_ledger
         │
6. Respuesta 200 → Frontend refresca lista
```

> [!IMPORTANT]
> **Lo que FALTA en este flujo:** El paso 5 debería ADEMÁS generar un asiento de partida doble en `kernel_journal_entries`. Hoy solo inserta la TX plana — no hay Debe/Haber.

---

## 🔴 Gaps Críticos del Módulo

| # | Gap | Impacto | Solución |
|---|-----|---------|----------|
| G1 | **COA vacío** | Sin COA no hay contabilidad real | Cargar plantilla NIIF al inicio, botón en UI |
| G2 | **Sin partida doble** | TXs no generan Debe/Haber | Crear `kernel_journal_entries` + `registrar_asiento()` |
| G3 | **Sin estados financieros** | No hay P&L, Balance General | Generar desde `journal_entries` agrupando por cuenta |
| G4 | **Sin `workspace_id`** | Tablas de FIN no tienen aislamiento tenant | Agregar columna y middleware |
| G5 | **Todo en App.jsx** | Imposible trabajar en paralelo | Extraer a `modules/D02_FIN/` |
| G6 | **Todo en server.py** | Endpoints de FIN mezclados con CT y HR | Extraer a `routers/router_fin.py` |
| G7 | **Terceros no universales** | `third_parties` solo existe en FIN | Migrar a `kernel_contacts` |

---

## 📡 Contrato del Módulo (Futuro)

### 📤 LO QUE EXPONE
```
GET  /api/fin/portafolios
POST /api/fin/portafolios
GET  /api/fin/transacciones
POST /api/fin/transacciones
PUT  /api/fin/transacciones/{id}
GET  /api/fin/cuentas
POST /api/fin/cuentas
GET  /api/fin/coa/{portfolio}
POST /api/fin/coa/cargar-plantilla
GET  /api/fin/terceros
GET  /api/fin/dashboard-data
GET  /api/fin/caja-viva
```

### 📥 LO QUE CONSUME (del Kernel)
```
kernel_contacts      → Tabla unificada de terceros (lectura/escritura)
kernel_accounting    → registrar_asiento() para partida doble
kernel_tenancy       → workspace_id inyectado automáticamente
kernel_event_bus     → Escucha eventos de otros módulos
```

### 📡 LO QUE EMITE (eventos)
```
'fin.transaccion.registrada'  → { tx_id, asientos[] }
'fin.asiento.creado'          → { journal_entry_id }
'fin.coa.actualizado'         → { portfolio_id }
```

### 🚫 LO QUE NO TOCA
```
- control_tower_driver.py (D01 MGMT)
- hr_driver.py (D03 HR)
- hub_driver.py (Project Hub)
- Tablas de workspace_users o hub_users
```

---

## 🎨 Identidad Visual

- **Fuente:** `IBM Plex Mono` (monospaced en todo)
- **Bordes:** `2px solid #000000`
- **Border-radius:** `0px` (absolutamente cuadrado)
- **Sombras:** `3px 3px 0 #000` (duras, no difusas)
- **Paleta:** Negro, blanco, verde HSL (positivos), `#FFB000` ámbar (warnings)
- **NO mezclar** con paleta ámbar del Control Tower

---

## 📝 Notas para Agentes IA

1. **Antes de editar:** Verificar que el cambio NO rompe otros módulos (test de desacoplamiento)
2. **server.py:** Solo agregar al final, nunca modificar endpoints existentes
3. **database_driver.py:** Requiere aprobación explícita del usuario para cualquier cambio
4. **App.jsx:** Preferir extraer componente nuevo antes que modificar inline
5. **Impuestos:** `tax_motor.py` tiene 5/5 tests pasando — no romper
6. **Cache:** El endpoint `/api/dashboard-data` tiene cache TTL con `cachetools` — limpiar al registrar TX
7. **Paginación:** `limit=50&offset=N` ya implementado — no duplicar lógica
8. **COA:** La función `cargar_plantilla_coa()` YA EXISTE pero nunca fue invocada — usarla, no reescribir
