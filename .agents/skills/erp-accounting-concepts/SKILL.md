---
name: erp-accounting-concepts
description: >
  Glosario y guía de referencia de conceptos contables, empresariales y ERP para FIN-SYS OS.
  Usar como referencia cuando se desarrollen módulos financieros, se diseñen tablas de BD,
  o se necesite entender la lógica de negocio detrás de una transacción.
  NO es una skill ejecutable — es un documento de conocimiento.
---

# ERP Accounting Concepts — Guía de Referencia FIN-SYS OS

> **Cuándo usar esta skill:** Cuando desarrolles cualquier funcionalidad financiera,
> contable o empresarial y necesites entender la lógica de negocio detrás del código.

---

## 1. Jerarquía Empresarial — Los 5 Niveles

```
NIVEL 1: HOLDING / PORTAFOLIO
  │  Grupo empresarial. Consolida todo. Boundary de reportes macro.
  │  Ejemplo: "Inversiones FIN-SYS"
  │  Tabla: entities (type='HOLDING')
  │
  ├── NIVEL 2: EMPRESA / UNIDAD DE NEGOCIO
  │     │  Entidad legal con NIT propio. Tiene su propia contabilidad,
  │     │  empleados, configuración fiscal y COA independiente.
  │     │  Ejemplo: "Jardín Infantil Pegasus" (NIT 900.123.456-7)
  │     │  Tabla: entities (type='EMPRESA')
  │     │
  │     ├── NIVEL 3: SUB-EMPRESA / CENTRO DE COSTOS
  │     │     │  Sede, sucursal o división. Comparte COA del padre pero
  │     │     │  puede tener P&L (Estado de Resultados) separado.
  │     │     │  Ejemplo: "Sede Norte — Pegasus"
  │     │     │  Tabla: entities (type='SUB_EMPRESA')
  │     │     │
  │     │     ├── NIVEL 4: PROYECTO
  │     │     │     Unidad temporal con presupuesto y alcance definido.
  │     │     │     Se cierra al completar. Tiene fecha de inicio/fin.
  │     │     │     Ejemplo: "Proyecto ERP — Cliente Minero"
  │     │     │     Tabla: entities (type='PROYECTO')
  │     │     │
  │     │     └── NIVEL 5: TAREA / ACTIVIDAD
  │     │           Micro-unidad operativa. Granularidad máxima de tracking.
  │     │           Ejemplo: "Fase 1: Levantamiento de Requisitos"
  │     │           Tabla: entities (type='TAREA')
```

### Reglas de Consolidación
- Las transacciones se registran en CUALQUIER nivel (2-5)
- Los reportes se **consolidan hacia arriba**: las transacciones de una Tarea
  suman al Proyecto, que suma a la Sub-Empresa, que suma a la Empresa, que suma al Holding
- El COA (Plan de Cuentas) se define a nivel de EMPRESA y se hereda hacia abajo
- La configuración fiscal (IVA, GMF) se define a nivel de EMPRESA

---

## 2. Conceptos Contables Fundamentales

### Partida Doble (Double-Entry Accounting)
**Toda transacción tiene DOS movimientos que se compensan:**

| Tipo | Débito (aumenta) | Crédito (aumenta) |
|------|-------------------|---------------------|
| ACTIVO | Débito ↑ | Crédito ↓ |
| PASIVO | Débito ↓ | Crédito ↑ |
| PATRIMONIO | Débito ↓ | Crédito ↑ |
| INGRESO | Débito ↓ | Crédito ↑ |
| GASTO | Débito ↑ | Crédito ↓ |

**Ejemplo práctico — Venta de uniforme a $80.000:**
```
Débito:  1105 Caja/Bancos        +$80.000  (Activo sube)
Crédito: 4135 Ingresos x Ventas  +$80.000  (Ingreso sube)

// Simultáneamente, el costo de venta:
Débito:  6135 Costo de Venta     +$40.000  (Gasto sube)
Crédito: 1435 Inventario         -$40.000  (Activo baja)
```

> En FIN-SYS: El kernel Zero-COA maneja la partida doble automáticamente
> via `posting_rules`. El usuario solo registra la transacción simple.

### Ecuación Contable Fundamental
```
ACTIVOS = PASIVOS + PATRIMONIO

Donde:
  PATRIMONIO = Capital Inicial + (INGRESOS - GASTOS)
```

> En FIN-SYS: El KPI "PATRIMONIO NETO" del header = Activos - Pasivos

---

## 3. Tipos de Cuentas Contables (COA / PUC)

### Estructura del PUC Colombiano (Plan Único de Cuentas)

| Clase | Código | Tipo | Ejemplo | Naturaleza |
|-------|--------|------|---------|------------|
| 1 | 1xxx | ACTIVO | Caja, Bancos, Inventario, CXC | Débito |
| 2 | 2xxx | PASIVO | CXP, Préstamos, Impuestos por Pagar | Crédito |
| 3 | 3xxx | PATRIMONIO | Capital Social, Utilidades Retenidas | Crédito |
| 4 | 4xxx | INGRESO | Ventas, Servicios, Intereses | Crédito |
| 5 | 5xxx | GASTO OPERACIONAL | Nómina, Arriendo, Servicios Públicos | Débito |
| 6 | 6xxx | COSTO DE VENTA | Costo Mercancía, Costo Materiales | Débito |
| 7 | 7xxx | GASTO NO OPERACIONAL | Intereses Bancarios, Pérdidas | Débito |

### Cuentas Clave para FIN-SYS

| Código | Nombre | Cuándo se usa |
|--------|--------|---------------|
| 1105 | Caja | Pagos/cobros en efectivo |
| 1110 | Bancos | Transferencias bancarias |
| 1305 | Clientes (CXC) | Ventas a crédito, pensiones pendientes |
| 1435 | Inventario | Stock de productos vendibles |
| 1520 | Maquinaria y Equipo | Activos fijos (no se venden) |
| 2205 | Proveedores (CXP) | Compras a crédito |
| 4135 | Ingresos x Comercio | Ventas de productos/servicios |
| 5105 | Gastos de Personal | Nómina, prestaciones |
| 6135 | Costo de Venta | Costo de los productos vendidos |

---

## 4. Assets vs Inventario — La Diferencia Crítica

### Assets (Activos Fijos) — Tabla `assets`
- Cosas que la empresa **compra para USAR**, no para vender
- Se **deprecian** con el tiempo (pierden valor contable)
- Ejemplos: computadores, muebles, vehículos, inmuebles, bus escolar
- Cuenta contable: 15xx (Propiedad, Planta y Equipo)
- **NO tienen stock** — son únicos o pocos

### Inventario (Recursos Vendibles) — Tabla `inventory_items`
- Cosas que la empresa **compra para VENDER o consumir**
- Tienen **stock** (entra/sale), **costo** y **precio de venta**
- Generan **Costo de Venta** (cuenta 6xxx) al despacharse
- Ejemplos: uniformes, útiles, materiales de construcción, mercado
- Cuenta contable: 14xx (Inventarios)
- **Tienen stock** — se cuentan, entran y salen

### Tabla de Decisión Rápida

| Pregunta | Si la respuesta es SÍ → |
|----------|-------------------------|
| ¿Se compró para revender? | INVENTARIO |
| ¿Se usa en la operación diaria y no se vende? | ACTIVO FIJO |
| ¿Tiene stock y se despacha a clientes? | INVENTARIO |
| ¿Se deprecia con los años? | ACTIVO FIJO |
| ¿Se consume o transforma? | INVENTARIO |
| ¿El bus del colegio? | ACTIVO FIJO |
| ¿Los uniformes del colegio? | INVENTARIO |

---

## 5. Cuentas por Cobrar (CXC) vs Cartera Vencida

### CXC — Cuentas por Cobrar
- **Definición:** Dinero que NOS deben. Facturas o compromisos emitidos en espera de pago.
- **Estado:** PENDIENTE (la fecha de pago aún no ha llegado)
- **Ejemplo:** Pensión de Junio del Jardín — vence el 5 de Julio. Hoy es 1 de Julio. → Es una CXC normal.
- **Cuenta contable:** 1305 (Clientes)
- **Tabla FIN-SYS:** `cxp_cxc_ledger` (type='CXC', status='PENDIENTE')

### Cartera Vencida
- **Definición:** Subset de CXC cuya **fecha de pago ya expiró** y aún no se ha cobrado.
- **Estado:** VENCIDO (la fecha de pago YA pasó)
- **Ejemplo:** Pensión de Mayo del Jardín — vencía el 5 de Junio. Hoy es 20 de Junio. → Cartera vencida.
- **Impacto:** Afecta el flujo de caja. Se debe gestionar con recordatorios (WhatsApp, Email).
- **Tabla FIN-SYS:** Misma tabla `cxp_cxc_ledger` pero filtrada por `due_date < NOW() AND status = 'PENDIENTE'`

### CXP — Cuentas por Pagar
- **Definición:** Dinero que NOSOTROS debemos. Facturas de proveedores pendientes de pago.
- **Cuenta contable:** 2205 (Proveedores)
- **Tabla FIN-SYS:** `cxp_cxc_ledger` (type='CXP')

### Flujo Visual

```
                    ┌── PAGADA → Se cierra, genera INGRESO en caja
                    │
CXC creada ── ¿Fecha vencida? ─── NO → CXC normal (Pendiente)
                    │
                    └── SÍ → CARTERA VENCIDA → Alerta → Cobrar
                                                  │
                                                  └── Pagada → INGRESO en caja
```

---

## 6. Costo de Venta (COGS — Cost of Goods Sold)

### ¿Qué es?
El costo que tuvo producir o adquirir los productos que se vendieron. Es un GASTO (cuenta 6xxx).

### ¿Por qué importa?
```
UTILIDAD BRUTA = INGRESOS POR VENTAS - COSTO DE VENTA

Si vendo 10 uniformes a $80.000 c/u = $800.000 en ventas
Pero cada uniforme me costó $40.000 = $400.000 en costos
→ UTILIDAD BRUTA = $400.000 (Margen del 50%)
```

### Flujo en FIN-SYS (automático al despachar inventario)

```
Admin despacha 1 uniforme a Mateo Silva ($80.000)
    │
    ├── Movimiento 1: INGRESO (o CXC)
    │   Débito: 1105 Caja +$80.000    (o 1305 CXC si es a crédito)
    │   Crédito: 4135 Ingresos +$80.000
    │
    └── Movimiento 2: COSTO DE VENTA (automático, invisible)
        Débito: 6135 Costo de Venta +$40.000
        Crédito: 1435 Inventario -$40.000

→ Stock baja de 10 a 9
→ Inventario en libros baja $40.000
→ Ingreso registrado por $80.000
→ Utilidad bruta: $40.000
```

---

## 7. Tipos de Transacciones en FIN-SYS

### INGRESO (Entrada de dinero)
- Dinero que ENTRA a la empresa
- Puede venir de: ventas, cobros, servicios, intereses, aportes
- Cuenta contable: Débito a Caja/Bancos (1xxx), Crédito a Ingresos (4xxx)
- **En el formulario:** Botón verde "INGRE"

### GASTO (Salida de dinero)
- Dinero que SALE de la empresa
- Puede ser: nómina, arriendo, servicios públicos, compras, impuestos
- Cuenta contable: Débito a Gastos (5xxx/6xxx), Crédito a Caja/Bancos (1xxx)
- **En el formulario:** Botón rojo "GASTO"

### TRANSFERENCIA (Movimiento interno)
- Dinero que se MUEVE entre cuentas de la misma empresa
- No es ingreso ni gasto — solo cambia de lugar
- Cuenta contable: Débito a Cuenta Destino (1xxx), Crédito a Cuenta Origen (1xxx)
- **En el formulario:** Botón gris "TRANS"
- Requiere: cuenta_origen + cuenta_destino

---

## 8. Modelo de Industrias (Capas Operativas)

### Concepto
Las industrias NO cambian la contabilidad base. Son **capas visuales** que:
1. Renombran labels (Tercero → Estudiante/Acudiente)
2. Personalizan categorías (Gastos → Alimentación, Material Didáctico)
3. Activan widgets especializados (Tablero de Recaudos, Caja Rápida)
4. Definen KPIs específicos (Morosidad, LTV Alumno, Margen/Alumno)

### Principio Fundamental
```
CONTABILIDAD PLANA (Libro Mayor)
     ↑ alimenta
WIDGETS DE INDUSTRIA (operación especializada)
     ↑ consulta/escribe
TABS CORE (Terceros, Inventario, Cartera)
```

Los widgets son **disparadores visuales** que llaman a la misma API del formulario genérico.
El usuario final opera widgets intuitivos; el backend registra transacciones planas.

### Industrias Disponibles

| ID | Nombre | Labels Clave | Widgets Clave |
|----|--------|-------------|---------------|
| ESTANDAR | Estándar Contable | Tercero, CXC, Recurso | Ninguno (base) |
| EDUCACION | Educación (Jardín/Colegio) | Estudiante, Pensión, Uniforme | Recaudos, Pensiones Masivas, Caja Uniformes |
| INMOBILIARIA | Inmobiliaria | Inquilino, Canon, Propiedad | Mapa Ocupación, Cobros Arriendo, Mantenimiento |
| CONSTRUCCION | Construcción | Contratista, Presupuesto, Lote | Avance de Obra, APU, Subcontratos |
| SERVICIOS | Servicios Profesionales | Cliente, Honorarios, Proyecto | Timesheet, Facturación por Horas |
| ENTRETENIMIENTO | Entretenimiento/Apuestas | Participante, Apuesta, Premio | — (por definir) |

### Cómo una Industria Interactúa con los Tabs Core

```
INDUSTRIA: EDUCACIÓN

Tab TERCEROS:
  └── Agrega tipo de contacto "Estudiante" con campos especiales:
      grado, acudiente_nombre, acudiente_documento, acudiente_tel
  └── El Widget "Tablero de Recaudos" LEE de esta tabla filtrando tipo=Estudiante

Tab CARTERA (CXC):
  └── El Widget "Generador Masivo" ESCRIBE aquí 22 registros CXC automáticos
  └── El Widget "Recaudos" LEE para saber quién pagó y quién no

Tab RECURSOS (Inventario):
  └── Se crean los uniformes, útiles, kits como ítems vendibles
  └── El Widget "Caja Rápida" LEE stock y ESCRIBE movimientos de salida

Tab REGISTRO (Libro Mayor):
  └── Los widgets hacen POST automáticos aquí para registrar ingresos/gastos
  └── El usuario también puede registrar manualmente (gastos operativos, etc.)
```

---

## 9. Flujos de Inventario

### Entrada de Stock (Compra de mercancía)
```
Admin compra 10 uniformes a $40.000 c/u = $400.000

Inventario:  +10 unidades
Contabilidad:
  Débito:  1435 Inventario    +$400.000
  Crédito: 1110 Bancos        -$400.000 (si pagó de contado)
      o
  Crédito: 2205 Proveedores   +$400.000 (si fue a crédito → CXP)
```

### Salida de Stock — Venta (Pago inmediato)
```
Admin despacha 1 uniforme a Mateo por $80.000 — pagó en efectivo

Inventario:  -1 unidad
Contabilidad (2 movimientos automáticos):
  1) Ingreso:
     Débito:  1105 Caja          +$80.000
     Crédito: 4135 Ingresos      +$80.000
  2) Costo de Venta:
     Débito:  6135 Costo Venta   +$40.000
     Crédito: 1435 Inventario    -$40.000
```

### Salida de Stock — Venta (A crédito / Fiado)
```
Admin despacha 1 uniforme a Mateo por $80.000 — carga al próximo mes

Inventario:  -1 unidad
Contabilidad (2 movimientos automáticos):
  1) CXC (NO toca caja):
     Débito:  1305 CXC Clientes  +$80.000
     Crédito: 4135 Ingresos      +$80.000
  2) Costo de Venta:
     Débito:  6135 Costo Venta   +$40.000
     Crédito: 1435 Inventario    -$40.000

→ Cuando el padre pague:
     Débito:  1105 Caja          +$80.000
     Crédito: 1305 CXC Clientes -$80.000
     CXC status: PENDIENTE → PAGADO
```

### Ajuste de Inventario (Merma, Daño, Conteo Físico)
```
Inventario:  ±N unidades
Contabilidad:
  Si es pérdida (merma):
    Débito:  5305 Gastos Diversos  +$costo
    Crédito: 1435 Inventario       -$costo
```

---

## 10. Métricas Clave por Industria

### Métricas Universales (todas las industrias)
| Métrica | Fórmula | Significado |
|---------|---------|-------------|
| **Margen Bruto** | (Ingresos - Costo Venta) / Ingresos × 100 | Rentabilidad antes de gastos operativos |
| **Margen Neto** | (Ingresos - Gastos Totales) / Ingresos × 100 | Rentabilidad real |
| **Liquidez** | Activos Corrientes / Pasivos Corrientes | Capacidad de pagar deudas a corto plazo |
| **Rotación CXC** | Ventas a Crédito / Promedio CXC | Velocidad de cobro |

### Métricas EDUCACIÓN (Jardín Infantil)
| Métrica | Fórmula | Significado |
|---------|---------|-------------|
| **Tasa de Recaudo** | CXC pagadas del mes / Total CXC del mes | % de padres que pagaron a tiempo |
| **Morosidad** | CXC vencidas / Total CXC × 100 | % de padres atrasados (>10 días) |
| **LTV Alumno** | Matrícula + (Pensión × 10 meses) + Uniformes | Valor total que aporta un alumno al año |
| **Margen/Alumno** | (Ingresos mensuales - Gastos mensuales) / Total alumnos | Ganancia neta por niño |
| **Costo/Alumno** | Gastos mensuales / Total alumnos | Cuánto cuesta mantener un alumno |

---

## 11. Glosario Rápido

| Término | Definición | En FIN-SYS |
|---------|-----------|-------------|
| **COA / PUC** | Plan de Cuentas — catálogo de todas las cuentas contables | `chart_of_accounts` |
| **Libro Mayor** | Registro cronológico de TODAS las transacciones | `transactions` |
| **Libro de Órdenes** | Registro operativo especializado por industria | Widgets → POST a `transactions` |
| **Tercero** | Persona o empresa con la que se tiene relación comercial | `third_parties` |
| **CXC** | Cuenta por Cobrar — dinero que nos deben | `cxp_cxc_ledger` type='CXC' |
| **CXP** | Cuenta por Pagar — dinero que debemos | `cxp_cxc_ledger` type='CXP' |
| **Cartera** | Conjunto de CXC + CXP de la empresa | `cxp_cxc_ledger` |
| **Cartera Vencida** | CXC donde la fecha de pago ya pasó | `due_date < NOW()` |
| **Activo Fijo** | Bien que se usa, no se vende (se deprecia) | `assets` |
| **Inventario** | Bien que se vende o consume (tiene stock) | `inventory_items` |
| **Costo de Venta** | Lo que costó producir/adquirir lo vendido | Cuenta 6xxx |
| **Partida Doble** | Todo débito tiene un crédito igual | Zero-COA kernel |
| **Balance General** | Foto de la empresa en un momento (A = P + Pat) | KPI "Balance Neto" |
| **Estado de Resultados** | Película del periodo (Ingresos - Gastos = Utilidad) | KPI "Ingresos/Gastos" |
| **Holding** | Grupo empresarial que controla otras empresas | `entities` type='HOLDING' |
| **NIT** | Número de Identificación Tributaria (Colombia) | `entities.nit` o `third_parties.identification_number` |
| **IVA** | Impuesto al Valor Agregado (19% Colombia) | `tax_motor.py` |
| **GMF** | Gravamen a Movimientos Financieros (4x1000) | `tax_motor.py` |
| **TRM** | Tasa Representativa del Mercado (COP/USD) | `transactions.trm` |
