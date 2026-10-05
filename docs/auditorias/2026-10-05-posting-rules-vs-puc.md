# Auditoría: posting_rules vs PUC (Decreto 2650/1993) — 05-oct-2026

> **Solo lectura y propuesta.** No se modificó `posting_rules`, ni asientos, ni esquema, ni código.
> SQL propuesto (no ejecutado): [`2026-10-05-posting-rules-vs-puc.sql`](2026-10-05-posting-rules-vs-puc.sql).
> Relacionado: DT-30 (CHECKLIST), D-134-09 (spec 13.4, rama `claude/project-status-review-5e1694` sin push).

## Fuentes

- `posting_rules` en la BD compartida (SELECT en sesión `readonly`): **22 reglas, todas globales** (`portfolio_id` NULL), creadas el 22-jun-2026 por `scripts/seed_puc.py` (17) y `scripts/add_fallback_rules.py` (5). El módulo Contadores **no ha creado ninguna**.
- Uso real: `kernel_journal_entries` × `transactions` × `user_accounts` × `cxp_cxc_ledger`.
- Nombre oficial de cada código: PUC del Decreto 2650/1993, transcrito de puc.com.co para cada cuenta citada (5105, 5115, 5120, 5135, 5195, 5220, 5235, 5305, 4135, 4155, 4160, 4175, 4210, 4220, 4295, 1105, 1110, 1120, 1380, 1435, 2105, 2335, 2380).

## Causa de fondo

El catálogo del proyecto (`PUC_ACCOUNTS` de `scripts/seed_puc.py`, copiado tal cual a `shared/puc_estandar.py` en la rama del export) **pone nombres corridos a los códigos**: en 5135, 5195 y 5105 el nombre de cada subcuenta es el de la subcuenta vecina. Las reglas se escribieron contra ese catálogo, así que "cuadran" con el seed pero no con el PUC. Por eso "519515 Elementos de Aseo y Cafetería" (nombre del seed) es en el PUC **519515 Música ambiental**, y "513520 Teléfono e Internet" es **513520 Procesamiento electrónico de datos**.

**Consecuencia para el export 13.4 (D-134-09):** `_nombres_puc()` toma esos nombres para todo código que no esté en el plan de la empresa. Hoy eso incluye 519515, 513520, 519525, 522005, 413505 y 417505: el contador vería "Asesoría y Consultoría" en una cuenta que en el PUC es **4175 Devoluciones en ventas (DB)**. Corregir `shared/puc_estandar.py` antes del push de 13.4 (§5).

## 1. Tabla de reglas

Leyenda: ✓ coincide · ◐ coincide en parte · ✗ no coincide · ✗✗ grave (la cuenta pertenece a otra clase de hecho económico).
"Uso" = asientos en el diario al 05-oct (C = contabilizados, B = borradores).

| id | Regla · categoría · tipo | Actual Db / Cr | Nombre PUC del código actual (nombre del seed) | ¿Coincide? | Recomendada | Por qué | Uso |
|---|---|---|---|---|---|---|---|
| 10 | Gastos Diversos · `Otros Gastos` · GASTO | 519515 / BANK | **Música ambiental** (seed: Elementos de aseo y cafetería) | ✗ | **519595** Diversos – Otros | Es la "otros" de 5195. Además es la categoría por defecto del bot para todo gasto | 16 · $3.511.900,50 (9 C + 7 B) |
| 19 | Gasto Genérico · `__FALLBACK__` · GASTO | 5105 / BANK | **5105 Gastos de personal** (cuenta de mayor, no subcuenta) | ✗✗ | **519595** | Todo gasto sin regla terminaba como gasto de PERSONAL | 0 hoy; las categorías de la plantilla Educación caerían aquí |
| 3 | Alimentación · `Alimentación` · GASTO | 519525 / BANK | Elementos de aseo y cafetería (seed: Alimentación y restaurante) | ◐ | **519560** Casino y restaurante | Restaurantes/almuerzos. La cafetería de oficina sí es 519525; comida con clientes, 519520 | 8 · $779.000 (6 C + 1 B) + 1 huérfano $175.000 |
| 4 | Infraestructura · `Infraestructura` · GASTO | 522005 / BANK | **Arrendamientos (gasto de VENTAS) – Terrenos** (seed: Arrendamiento oficina) | ✗ | **512010** Arrendamientos (administración) – Construcciones y edificaciones | Oficina, bodega y coworking son edificaciones; el grupo 52 es gasto de ventas (522010 solo si es local comercial) | 4 · $1.530.000 (3 C + 1 B) |
| 1 | Servicios Públicos · `Servicios` · GASTO | 513520 / BANK | **Procesamiento electrónico de datos** (seed: Teléfono e internet) | ✗ | **513595** Servicios – Otros, y categorías nuevas: 513525 Acueducto · 513530 Energía · 513535 Teléfono/Internet · 513555 Gas | La categoría mezcla cuatro servicios que el PUC separa; la genérica honesta es "Otros" | 4 · $253.200 (3 C + 1 B) |
| 22 | Servicios Públicos · `Servicios Públicos` · GASTO | 513525 / BANK | Acueducto y alcantarillado (seed: Gas) | ◐ solo si es agua | **513595** (o separar como id 1) | "Pago servicios públicos" (factura EPM = agua + energía + gas) | 0 (la usa la plantilla Educación) |
| 2 | Suscripciones Tech · `Suscripciones` · GASTO | 513535 / BANK | **Teléfono** (seed: Software y suscripciones) | ✗ | **513520** Procesamiento electrónico de datos | SaaS, hosting y software como servicio. Las publicaciones van en 519510 | 0 |
| 5 | Transporte · `Transporte` · GASTO | 513530 / BANK | **Energía eléctrica** (seed: Correo y transporte) | ✗ | **519545** Taxis y buses | Uber y taxi. Envíos y fletes → 513550; correo → 513540 (categorías aparte si se usan) | 0 |
| 6 | Publicidad · `Publicidad` · GASTO | 519530 / BANK | **Útiles, papelería y fotocopias** (seed: Publicidad y diseño) | ✗ | **523560** Publicidad, propaganda y promoción | En el PUC la publicidad es gasto de ventas (5235) | 0 |
| 7 | Papelería · `Papelería` · GASTO | 519520 / BANK | **Gastos de representación y relaciones públicas** (seed: Útiles y papelería) | ✗ | **519530** Útiles, papelería y fotocopias | Es literalmente esa subcuenta | 0 |
| 8 | Gastos Bancarios · `Gastos Bancarios` · GASTO | 519505 / BANK | Comisiones, del grupo 51 de administración (seed: Comisiones bancarias) | ◐ | **530505** Gastos bancarios | Cuota de manejo y gastos de banco son financieros no operacionales (5305). Comisión bancaria → 530515; GMF 4×1000 → 511595 Impuestos – Otros | 0 |
| 9 | Nómina · `Nómina` · GASTO | 510506 / BANK | Sueldos | ✓ | mantener | Simplificado: paga directo, sin causar 2505 ni prestaciones | 1 · $100.000 |
| 11 | Venta Productos · `Ventas` · INGRESO | BANK / 413505 | **No existe** (4135 usa pares: 413502…413572, 413595) (seed: Venta de productos) | ◐ intención sí, código no | **413595** Venta de otros productos (o la 41xx de la actividad de la empresa) | Código inexistente en el PUC. También es el ingreso por defecto del bot | 1 · $6.000.000 (ver §3: posible doble conteo) |
| 21 | Venta de Productos · `Venta de Productos` · INGRESO | BANK / 413505 | igual que id 11 | ◐ | **413595** (duplicado: ninguna lista de la web usa esta categoría) | — | 0 |
| 12 | Ingresos por Servicio · `Servicios Prestados` · INGRESO | BANK / 417505 | **4175 Devoluciones en ventas (DB)**: naturaleza débito, RESTA ventas (seed: Asesoría y consultoría) | ✗✗ | **415550** Actividades empresariales de consultoría (o la de la actividad: 416005 si es enseñanza) | Un ingreso acreditado en una cuenta de devoluciones | 0 |
| 20 | Servicios Profesionales · `Servicios Profesionales` · INGRESO | BANK / 417505 | igual que id 12 | ✗✗ | **415550** (duplicado: categoría que ninguna lista usa) | — | 0 |
| 18 | Ingreso Genérico · `__FALLBACK__` · INGRESO | BANK / 417505 | igual que id 12 | ✗✗ | **429595** Diversos – Otros (no operacional) | Un ingreso sin regla no se presume operacional; el contador lo reclasifica | 4 · $4.449.500 (2 C + 1 B + 1 huérfano $1.800.000) |
| 13 | Ingresos Financieros · `Intereses` · INGRESO | BANK / 421005 | Intereses | ✓ | mantener | — | 0 |
| 14 | Crear CXC · `__CXC_CREATE__` · CXC | 130505 / 413505 | Clientes nacionales / **no existe** | ◐ débito sí; el crédito presume venta de mercancía | Crédito = ingreso de la actividad de la empresa (contador). Si la CXC es un préstamo otorgado: Db 138095 Deudores varios – Otros / Cr banco, **sin ingreso** | Las 5 CXC reales son ventas de lotes ("Venta Lote A54"): es ingreso inmobiliario o de construcción, no 4135 | 5 · $141.000.000 (sin portafolio) |
| 15 | Crear CXP · `__CXP_CREATE__` · CXP | 143505 / 220505 | Mercancías no fabricadas (el PUC solo trae 143599; 143505 vale como auxiliar) / Proveedores nacionales | ◐ solo si es compra de mercancía para revender | Débito según lo comprado (gasto de su categoría, activo o 1435). Crédito 220505 (mercancía) o **233595** Costos y gastos por pagar – Otros. Préstamo recibido: Db banco / Cr 2105xx o 238095 | No toda CXP es inventario | 1 · $400.000 (sin concepto) |
| 16 | Cobrar CXC · `__CXC_PAYMENT__` · CXC | BANK / 130505 | Clientes nacionales | ✓ | mantener | Ver bugs en §3 | 9 · $11.850.000 |
| 17 | Pagar CXP · `__CXP_PAYMENT__` · CXP | 220505 / BANK | Proveedores nacionales | ✓ | mantener | **Nunca se usa** (bug en §3) | 0 |
| — | `__BANK__` (16 de las 22 reglas) | 111005 por defecto; 110505 o 110510 solo si el nombre de la cuenta es EXACTO "Efectivo" o "Caja Menor" | 111005 Bancos – Moneda nacional | ✗ para efectivo y ahorros | Resolver por el campo estructurado `user_accounts.type`: Efectivo → 110505 · Ahorros → **112005** Cuentas de ahorro – Bancos · Corriente → 111005 | Ninguna cuenta real se llama exactamente así ("Efectivo Holding", "Efectivo Julian", "Caja Menor constructora blu"), así que TODO cae en 111005. El plan del portafolio 1 ya tiene 112005, 11200501 AHORRO BANCOLOMBIA y 11100501 DAVIVIENDA | Efectivo: neto $5.923.500 C en 111005 · Ahorros: 4 cuentas |

### Categorías sin regla (hoy caen al genérico o no asientan)

| Categoría | Origen | Hoy | Propuesta |
|---|---|---|---|
| `Otros Ingresos` · INGRESO | `shared/categorias.js` | fallback 417505 (2 TX, $1.900.000) | regla propia → 429595 (en el SQL) |
| `Servicios` · INGRESO | `estandar.json` (la regla espera `Servicios Prestados`) | fallback 417505 (1 TX "CURSO", $749.500, B) | regla → 415550 (en el SQL), o 416005 si es enseñanza |
| Plantilla `educacion.json`: Matrículas, Pensiones, Uniformes, Nómina Docente, Arriendo Local, Mantenimiento, Seguros… | Pegasus (jardín infantil) | fallback (5105 / 417505) | reglas propias: 416005 Enseñanza – actividades relacionadas con la educación (matrículas y pensiones), 510506 (nómina), 512010 (arriendo), cuenta 5145 Mantenimiento y reparaciones, cuenta 5130 Seguros (la subcuenta la elige el contador). Pendiente del contador |
| `Transferencia` · TRANSFERENCIA | `shared/categorias.js` | **sin regla → sin asiento** (0 TX hoy) | Necesita código (Db destino / Cr origen), no una regla. Obligatorio antes de separar 110505, 111005 y 112005 |

## 2. Reclasificación de lo histórico

Cambiar una regla solo afecta los asientos **futuros**. Para lo ya registrado:

**a) Borradores (19 asientos, no están en libros):** el contador corrige la cuenta en la bandeja (editar líneas del borrador, `PUT /api/contadores/asientos/{id}/lineas`) y luego contabiliza. No es editar un asiento contabilizado; para eso existe el estado borrador. Son 7 de Gastos Diversos ($1.838.600), 1 de Alimentación, 1 de Infraestructura, 1 de Servicios y 1 de Ingreso Genérico (CURSO).

**b) Contabilizados:** **un asiento manual de reclasificación** por portafolio, creado por el contador en Contadores → Diario (nace borrador y él lo contabiliza), con fecha 30-sep-2026 (no hay periodos cerrados). Nunca se editan las líneas originales. Montos al 05-oct (portafolio 1):

| Débito | Crédito | Monto | Nota |
|---|---|---|---|
| 519595 Diversos – Otros | 519515 | $1.673.300,50 | |
| 519560 Casino y restaurante | 519525 | $771.000 | el contador separa lo que sea cafetería |
| 512010 Arrendamientos – Construcciones | 522005 | $1.420.000 | |
| 513595 (o la subcuenta de cada factura) | 513520 | $197.200 | |
| 417505 | 422010 Arrendamientos – Construcciones y edificios (no operacional) | $1.800.000 | TX 26 "Arrendamiento Apto 201"; 415505 si arrendar es la actividad |
| 417505 | 429595 | $100.000 | TX 15 "prueba de ingreso #2": mejor eliminar la TX de prueba |
| 413505 | ¿413595 o 130505? | $6.000.000 | TX 21 "Separación lote A54": ver doble conteo en §3 |

**Requisito:** las cuentas destino deben existir en el plan de cuentas (el kernel valida contra `chart_of_accounts` ∪ `posting_rules`). Si el SQL de reglas ya corrió, existen por la unión. Lo correcto es que el contador las cree en Plan de cuentas (cierra parte de DT-30).

**c) Caja y bancos:** la reclasificación 111005 → 110505 / 112005 (efectivo neto $5.923.500; Bancolombia 3037 neto +$1.170.000; Davivienda 6552 neto −$1.000.000) **solo después** de corregir `__BANK__` y las transferencias (§4). Si se hace antes, los registros nuevos siguen cayendo mal. Además, 13 líneas sin cuenta (DT-01, $2.355.000,50) no se pueden clasificar.

## 3. Hallazgos colaterales (no son de reglas, pero condicionan la reclasificación)

1. **Los abonos a una CXP se contabilizan como cobro de CXC.** `routers/cartera.py:297-299` emite siempre `__CXC_PAYMENT__`/`CXC`: un pago a proveedor quedaría Db banco / Cr 130505 (al revés y en la cuenta equivocada). La regla 17 "Pagar CXP" nunca se usa. Hoy hay 0 abonos a CXP, así que no hay daño todavía.
2. **Abonos sin asiento: $19.744.000.** El "abono inicial" de `POST /api/cartera` no emite asiento (pagos 1, 5 y 18), y la cuota #1 del ledger 5 (pago 14) tampoco tiene. Por eso **130505 en libros = $129.150.000 vs cartera real $105.006.000** (diferencia $24.144.000 = $19.744.000 + $4.400.000 del ledger 3 borrado, cuyos asientos CXC-3, PAY-3 y PAY-4 siguen vivos).
3. **Posible doble conteo del lote A54:** TX 21 "Separación lote A54" ($6M, `Ventas`) se acreditó a ingreso, y la CXC-8 "Venta Lote A54" ($28M, que ya incluye ese abono inicial de $6M) también. Si es la misma venta, el ingreso está inflado en $6M. El ajuste sería Db 413505 / Cr 130505; lo confirma Andrés.
4. **Asientos de TX borradas:** TX-25 ($1.800.000 Ingreso Genérico) y TX-27 ($175.000 Alimentación) siguen contabilizados sin TX y sin portafolio. Se anulan con el flujo del contador (contra-asiento), si Andrés confirma que se borraron a propósito.
5. **Cartera sin portafolio:** `cxp_cxc_ledger` no tiene `portfolio_id`, así que los $141M de CXC y los cobros quedan fuera de los libros de cada empresa (solo en el consolidado).
6. **El abono no separa el interés** (`interest_part` va todo contra 130505; debería ir a 421005 en CXC o a 530520 en CXP) y no recibe `account_id` (siempre 111005). Hoy el interés es $0 en todos.
7. **`cuenta_nombre` = nombre de la regla** (`shared/helpers.py:93-95` y `:164-166`): es la raíz de D-134-09. Debería guardarse el nombre de la cuenta; la regla ya queda en la descripción ("[Regla] …").
8. Plantillas de COA (`fin_sys_core/coa_templates.py`) con nombres fuera del PUC, ya sembrados en el portafolio 1: **4120 "Ingresos por Alquiler"** (PUC: Industrias manufactureras) y **4150 "Ingresos por Avance de Obra"** (PUC: Actividad financiera; construcción es 4130).

## 4. Correcciones de código (fase 2 — requieren plan y aprobación)

| # | Archivo | Cambio | Prioridad |
|---|---|---|---|
| 1 | `shared/puc_estandar.py` (rama 13.4 sin push) | Nombres oficiales (~24 códigos, §5) y agregar los códigos nuevos | **Alta: antes del push de 13.4** |
| 2 | `shared/helpers.py` | `cuenta_nombre` = nombre COA/PUC del código, no el de la regla | Alta |
| 3 | `shared/rules_cache.py` + `shared/helpers.py` | `__BANK__` por `user_accounts.type`, sin nombres (Regla 6b). A futuro, enlazar cada cuenta con su auxiliar del COA requiere una columna nueva (ALTER, con aprobación) | Media |
| 4 | Transferencias | Asiento Db destino / Cr origen. **Requisito de #3** | Media |
| 5 | `routers/cartera.py` | Abono según el tipo del ledger, interés aparte, asiento del abono inicial, `account_id` y portafolio | Alta (#1 de §3) |
| 6 | Cartera CXC/CXP | Campo estructurado "tipo" (venta a crédito / préstamo / compra de mercancía / gasto a crédito), con una regla por tipo (Regla 6b: no se adivina) | Media, con spec |
| 7 | `scripts/seed_puc.py` | Usar `shared/puc_estandar.py` y POSTING_RULES nuevas (que una BD vacía no repita el error) | Baja |
| 8 | `draft_builder.py:62` | El ingreso por defecto del bot es "Ventas" (venta de mercancía): usar "Otros Ingresos" o no poner valor por defecto | Baja |

## 5. Nombres del catálogo del proyecto que difieren del PUC

| Código | Seed / `puc_estandar.py` | PUC (Decreto 2650) |
|---|---|---|
| 233505 | Costos y gastos por pagar | Gastos financieros |
| 413505 | Venta de productos | *(no existe; 413595 Venta de otros productos)* |
| 417505 / 417510 | Asesoría y consultoría / Servicios técnicos | *(4175 Devoluciones en ventas (DB))* |
| 510533 | Prima de servicios | Intereses sobre cesantías |
| 510536 | Vacaciones | Prima de servicios |
| 510568 | Aportes EPS | Aportes a ARP (ARL) |
| 510569 | Aportes pensión | Aportes a EPS |
| 510570 | Aportes ARL | Aportes a fondos de pensiones y/o cesantías |
| 513510 | Acueducto y alcantarillado | Temporales |
| 513515 | Energía eléctrica | Asistencia técnica |
| 513520 | Teléfono e internet | Procesamiento electrónico de datos |
| 513525 | Gas | Acueducto y alcantarillado |
| 513530 | Correo y transporte | Energía eléctrica |
| 513535 | Software y suscripciones | Teléfono |
| 519505 | Comisiones bancarias | Comisiones (bancarias: 530515) |
| 519510 | GMF (4x1000) | Libros, suscripciones, periódicos y revistas |
| 519515 | Elementos de aseo y cafetería | Música ambiental |
| 519520 | Útiles y papelería | Gastos de representación y relaciones públicas |
| 519525 | Alimentación y restaurante | Elementos de aseo y cafetería |
| 519530 | Publicidad y diseño | Útiles, papelería y fotocopias |
| 522005 | Arrendamiento oficina | Arrendamientos (ventas) – Terrenos |
| 530505 | Intereses bancarios | Gastos bancarios (intereses: 530520) |

Coinciden: 110505, 110510, 111005, 111010, 130505, 152405, 152805, 220505, 236505, 310505, 421005, 510506, 510527, 510530, 513505.

> Bajo NIIF cada empresa puede definir su catálogo, pero si se llama "PUC" y se entrega a un contador, los códigos deben significar lo que dice el Decreto 2650. La última palabra sobre las cuentas de ingreso por actividad (lotes, cursos, arriendos) la tiene el contador.
