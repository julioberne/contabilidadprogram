# -*- coding: utf-8 -*-
"""
seed_puc.py — Seed PUC Colombiano Básico + Posting Rules (Zero-COA)
====================================================================
Ejecutar una sola vez:  python scripts/seed_puc.py

Inserta:
  1. ~60 cuentas PUC esenciales para MiPyme en chart_of_accounts (portfolio_id=1)
  2. ~15 posting_rules que mapean categorías del usuario a cuentas COA
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Cargar variables de entorno desde .env (parser manual, no requiere python-dotenv)
_env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env')
if os.path.exists(_env_path):
    with open(_env_path, 'r', encoding='utf-8') as _f:
        for _line in _f:
            _line = _line.strip()
            if _line and not _line.startswith('#') and '=' in _line:
                _key, _, _val = _line.partition('=')
                _key = _key.strip()
                _val = _val.strip().strip('"').strip("'")
                if _key and _key not in os.environ:
                    os.environ[_key] = _val

from fin_sys_core.db_pool import get_conn, put_conn

PORTFOLIO_ID = 1  # Negocio A

# ══════════════════════════════════════════════════════════════════════════════
# PUC COLOMBIANO BÁSICO — Cuentas esenciales para MiPyme
# ══════════════════════════════════════════════════════════════════════════════
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

# ══════════════════════════════════════════════════════════════════════════════
# POSTING RULES — Mapeo Categoría → Cuentas COA
# ══════════════════════════════════════════════════════════════════════════════
# El credit_account_code "__BANK__" se resuelve dinámicamente en runtime
# usando el account_id de la transacción → user_accounts.name → código PUC

POSTING_RULES = [
    # Egresos (el usuario gasta dinero)
    # rule_name, category, type, debit_code, credit_code, description
    ("Servicios Públicos",   "Servicios",         "EGRESO", "513520", "__BANK__", "Internet, teléfono, acueducto, energía"),
    ("Suscripciones Tech",   "Suscripciones",     "EGRESO", "513535", "__BANK__", "Software, streaming, SaaS mensual"),
    ("Alimentación",         "Alimentación",      "EGRESO", "519525", "__BANK__", "Restaurantes, mercado, cafetería"),
    ("Infraestructura",      "Infraestructura",   "EGRESO", "522005", "__BANK__", "Arriendo oficina, bodega, coworking"),
    ("Transporte",           "Transporte",        "EGRESO", "513530", "__BANK__", "Uber, taxi, envíos, correo"),
    ("Publicidad",           "Publicidad",        "EGRESO", "519530", "__BANK__", "Diseño, marketing, pauta digital"),
    ("Papelería",            "Papelería",         "EGRESO", "519520", "__BANK__", "Útiles, papelería, impresiones"),
    ("Gastos Bancarios",     "Gastos Bancarios",  "EGRESO", "519505", "__BANK__", "Comisiones, cuota de manejo"),
    ("Nómina",               "Nómina",            "EGRESO", "510506", "__BANK__", "Sueldos y salarios"),
    ("Gastos Diversos",      "Otros Gastos",      "EGRESO", "519515", "__BANK__", "Gastos varios no categorizados"),

    # Ingresos (el usuario recibe dinero)
    ("Venta Productos",      "Ventas",            "INGRESO", "__BANK__", "413505", "Venta de mercancía y productos"),
    ("Ingresos por Servicio","Servicios Prestados","INGRESO", "__BANK__", "417505", "Honorarios, consultoría, freelance"),
    ("Ingresos Financieros", "Intereses",         "INGRESO", "__BANK__", "421005", "Rendimientos, CDT, intereses"),

    # Cartera (CXC/CXP) — códigos fijos, sin __BANK__
    ("Crear CXC",            "__CXC_CREATE__",    "CXC",    "130505", "413505", "Cliente debe → Ingreso devengado"),
    ("Crear CXP",            "__CXP_CREATE__",    "CXP",    "143505", "220505", "Mercancía recibida → Proveedor por pagar"),
    ("Cobrar CXC",           "__CXC_PAYMENT__",   "CXC",    "__BANK__", "130505", "Banco entra → Cliente liquidado"),
    ("Pagar CXP",            "__CXP_PAYMENT__",   "CXP",    "220505", "__BANK__", "Proveedor liquidado → Banco sale"),
]


def seed_puc():
    """Inserta el PUC colombiano básico en chart_of_accounts."""
    conn = get_conn()
    try:
        cur = conn.cursor()

        # Verificar si ya hay cuentas
        cur.execute("SELECT COUNT(*) FROM chart_of_accounts WHERE portfolio_id = %s;", (PORTFOLIO_ID,))
        existing = cur.fetchone()[0]
        if existing > 0:
            print(f"⚠️  PUC ya tiene {existing} cuentas para portfolio {PORTFOLIO_ID}. Saltando seed.")
            return existing

        # Insertar cuentas en orden (padres primero)
        inserted = 0
        for code, name, acct_type, is_group, parent_code in PUC_ACCOUNTS:
            parent_id = None
            if parent_code:
                cur.execute(
                    "SELECT id FROM chart_of_accounts WHERE portfolio_id = %s AND code = %s;",
                    (PORTFOLIO_ID, parent_code)
                )
                row = cur.fetchone()
                if row:
                    parent_id = row[0]

            cur.execute("""
                INSERT INTO chart_of_accounts (portfolio_id, code, name, account_type, is_group, parent_id)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (portfolio_id, code) DO NOTHING;
            """, (PORTFOLIO_ID, code, name, acct_type, is_group, parent_id))
            inserted += 1

        conn.commit()
        print(f"✅ PUC: {inserted} cuentas insertadas para portfolio {PORTFOLIO_ID}")
        return inserted
    except Exception as e:
        conn.rollback()
        print(f"❌ Error insertando PUC: {e}")
        raise
    finally:
        put_conn(conn)


def seed_posting_rules():
    """Inserta las posting_rules que mapean categorías a cuentas COA."""
    conn = get_conn()
    try:
        cur = conn.cursor()

        # Verificar si ya hay reglas
        cur.execute("SELECT COUNT(*) FROM posting_rules;")
        existing = cur.fetchone()[0]
        if existing > 0:
            print(f"⚠️  Posting rules ya tiene {existing} reglas. Saltando seed.")
            return existing

        inserted = 0
        for rule_name, category, tx_type, debit, credit, desc in POSTING_RULES:
            cur.execute("""
                INSERT INTO posting_rules (rule_name, category, transaction_type, debit_account_code, credit_account_code, description, portfolio_id)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT DO NOTHING;
            """, (rule_name, category, tx_type, debit, credit, desc, None))
            inserted += 1

        conn.commit()
        print(f"✅ Posting Rules: {inserted} reglas insertadas")
        return inserted
    except Exception as e:
        conn.rollback()
        print(f"❌ Error insertando posting rules: {e}")
        raise
    finally:
        put_conn(conn)


if __name__ == "__main__":
    print("=" * 60)
    print("  SEED PUC COLOMBIANO + POSTING RULES (Zero-COA)")
    print("=" * 60)
    print()
    seed_puc()
    print()
    seed_posting_rules()
    print()
    print("=" * 60)
    print("  ✅ SEED COMPLETO")
    print("=" * 60)
