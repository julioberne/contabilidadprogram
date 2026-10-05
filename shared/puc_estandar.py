# -*- coding: utf-8 -*-
"""puc_estandar.py — PUC colombiano básico para MiPyme (fuente única).

La usan la siembra del plan de cuentas (scripts/seed_puc.py) y el motor de
libros .xlsx (fin_sys_core/export_xlsx.py, spec 13.4) para poner el nombre
oficial de cada código. Vive en shared/ porque scripts/ no viaja en la imagen
de producción.

Cada cuenta: (código, nombre, tipo, es_grupo, código_padre).
"""

PUC_ACCOUNTS = [
    # ── ACTIVOS (1) ──────────────────────────────────────────────────────────
    # code, name, account_type, is_group, parent_code
    ("1", "ACTIVOS", "ACTIVO", True, None),
    ("11", "DISPONIBLE", "ACTIVO", True, "1"),
    ("1105", "CAJA", "ACTIVO", True, "11"),
    ("110505", "Caja General", "ACTIVO", False, "1105"),
    ("110510", "Caja Menor", "ACTIVO", False, "1105"),
    ("1110", "BANCOS", "ACTIVO", True, "11"),
    ("111005", "Bancos Nacionales", "ACTIVO", False, "1110"),
    ("111010", "Bancos USD", "ACTIVO", False, "1110"),
    ("13", "DEUDORES", "ACTIVO", True, "1"),
    ("1305", "CLIENTES", "ACTIVO", True, "13"),
    ("130505", "Clientes Nacionales", "ACTIVO", False, "1305"),
    ("14", "INVENTARIOS", "ACTIVO", True, "1"),
    ("1435", "MERCANCÍAS", "ACTIVO", True, "14"),
    ("143505", "Mercancías No Fabricadas", "ACTIVO", False, "1435"),
    ("15", "PROPIEDAD PLANTA Y EQUIPO", "ACTIVO", True, "1"),
    ("1524", "EQUIPOS DE OFICINA", "ACTIVO", True, "15"),
    ("152405", "Muebles y Enseres", "ACTIVO", False, "1524"),
    ("1528", "EQUIPO DE CÓMPUTO", "ACTIVO", True, "15"),
    ("152805", "Equipos de Procesamiento de Datos", "ACTIVO", False, "1528"),

    # ── PASIVOS (2) ──────────────────────────────────────────────────────────
    ("2", "PASIVOS", "PASIVO", True, None),
    ("22", "PROVEEDORES", "PASIVO", True, "2"),
    ("2205", "PROVEEDORES NACIONALES", "PASIVO", True, "22"),
    ("220505", "Proveedores Nacionales", "PASIVO", False, "2205"),
    ("23", "CUENTAS POR PAGAR", "PASIVO", True, "2"),
    ("2335", "COSTOS Y GASTOS POR PAGAR", "PASIVO", True, "23"),
    ("233505", "Costos y Gastos por Pagar", "PASIVO", False, "2335"),
    ("2365", "RETENCIÓN EN LA FUENTE", "PASIVO", True, "23"),
    ("236505", "Retención Salarios", "PASIVO", False, "2365"),
    ("24", "IMPUESTOS POR PAGAR", "PASIVO", True, "2"),
    ("2408", "IVA POR PAGAR", "PASIVO", True, "24"),
    ("240805", "IVA Generado en Ventas", "PASIVO", False, "2408"),
    ("25", "OBLIGACIONES LABORALES", "PASIVO", True, "2"),
    ("2505", "SALARIOS POR PAGAR", "PASIVO", True, "25"),
    ("250505", "Salarios por Pagar", "PASIVO", False, "2505"),

    # ── PATRIMONIO (3) ───────────────────────────────────────────────────────
    ("3", "PATRIMONIO", "PATRIMONIO", True, None),
    ("31", "CAPITAL SOCIAL", "PATRIMONIO", True, "3"),
    ("3105", "CAPITAL SUSCRITO Y PAGADO", "PATRIMONIO", True, "31"),
    ("310505", "Capital Autorizado", "PATRIMONIO", False, "3105"),
    ("36", "RESULTADOS DEL EJERCICIO", "PATRIMONIO", True, "3"),
    ("3605", "UTILIDAD DEL EJERCICIO", "PATRIMONIO", True, "36"),
    ("360505", "Utilidad del Ejercicio", "PATRIMONIO", False, "3605"),

    # ── INGRESOS (4) ─────────────────────────────────────────────────────────
    ("4", "INGRESOS", "INGRESO", True, None),
    ("41", "OPERACIONALES", "INGRESO", True, "4"),
    ("4135", "COMERCIO POR MAYOR Y MENOR", "INGRESO", True, "41"),
    ("413505", "Venta de Productos", "INGRESO", False, "4135"),
    ("4175", "SERVICIOS", "INGRESO", True, "41"),
    ("417505", "Asesoría y Consultoría", "INGRESO", False, "4175"),
    ("417510", "Servicios Técnicos", "INGRESO", False, "4175"),
    ("42", "NO OPERACIONALES", "INGRESO", True, "4"),
    ("4210", "FINANCIEROS", "INGRESO", True, "42"),
    ("421005", "Intereses y Rendimientos", "INGRESO", False, "4210"),

    # ── GASTOS (5) ───────────────────────────────────────────────────────────
    ("5", "GASTOS", "GASTO", True, None),
    ("51", "OPERACIONALES DE ADMINISTRACIÓN", "GASTO", True, "5"),
    ("5105", "GASTOS DE PERSONAL", "GASTO", True, "51"),
    ("510506", "Sueldos", "GASTO", False, "5105"),
    ("510527", "Auxilio de Transporte", "GASTO", False, "5105"),
    ("510530", "Cesantías", "GASTO", False, "5105"),
    ("510533", "Prima de Servicios", "GASTO", False, "5105"),
    ("510536", "Vacaciones", "GASTO", False, "5105"),
    ("510568", "Aportes EPS", "GASTO", False, "5105"),
    ("510569", "Aportes Pensión", "GASTO", False, "5105"),
    ("510570", "Aportes ARL", "GASTO", False, "5105"),
    ("5135", "SERVICIOS", "GASTO", True, "51"),
    ("513505", "Aseo y Vigilancia", "GASTO", False, "5135"),
    ("513510", "Acueducto y Alcantarillado", "GASTO", False, "5135"),
    ("513515", "Energía Eléctrica", "GASTO", False, "5135"),
    ("513520", "Teléfono e Internet", "GASTO", False, "5135"),
    ("513525", "Gas", "GASTO", False, "5135"),
    ("513530", "Correo y Transporte", "GASTO", False, "5135"),
    ("513535", "Software y Suscripciones", "GASTO", False, "5135"),
    ("5195", "DIVERSOS", "GASTO", True, "51"),
    ("519505", "Comisiones Bancarias", "GASTO", False, "5195"),
    ("519510", "GMF (4x1000)", "GASTO", False, "5195"),
    ("519515", "Elementos de Aseo y Cafetería", "GASTO", False, "5195"),
    ("519520", "Útiles y Papelería", "GASTO", False, "5195"),
    ("519525", "Alimentación y Restaurante", "GASTO", False, "5195"),
    ("519530", "Publicidad y Diseño", "GASTO", False, "5195"),
    ("52", "OPERACIONALES DE VENTAS", "GASTO", True, "5"),
    ("5220", "ARRENDAMIENTOS", "GASTO", True, "52"),
    ("522005", "Arrendamiento Oficina", "GASTO", False, "5220"),
    ("53", "NO OPERACIONALES", "GASTO", True, "5"),
    ("5305", "FINANCIEROS", "GASTO", True, "53"),
    ("530505", "Intereses Bancarios", "GASTO", False, "5305"),
]
