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
from shared.puc_estandar import PUC_ACCOUNTS  # noqa: E402  (fuente única: siembra y libros .xlsx)

# ══════════════════════════════════════════════════════════════════════════════
# POSTING RULES — Mapeo Categoría → Cuentas COA
# ══════════════════════════════════════════════════════════════════════════════
# El credit_account_code "__BANK__" se resuelve dinámicamente en runtime
# usando el account_id de la transacción → user_accounts.name → código PUC

POSTING_RULES = [
    # Gastos (el usuario gasta dinero) — el tipo DEBE ser "GASTO": es el valor
    # que valida TransactionInput y por el que filtra emit_journal_entry
    # rule_name, category, type, debit_code, credit_code, description
    ("Servicios Públicos",   "Servicios",         "GASTO", "513520", "__BANK__", "Internet, teléfono, acueducto, energía"),
    ("Suscripciones Tech",   "Suscripciones",     "GASTO", "513535", "__BANK__", "Software, streaming, SaaS mensual"),
    ("Alimentación",         "Alimentación",      "GASTO", "519525", "__BANK__", "Restaurantes, mercado, cafetería"),
    ("Infraestructura",      "Infraestructura",   "GASTO", "522005", "__BANK__", "Arriendo oficina, bodega, coworking"),
    ("Transporte",           "Transporte",        "GASTO", "513530", "__BANK__", "Uber, taxi, envíos, correo"),
    ("Publicidad",           "Publicidad",        "GASTO", "519530", "__BANK__", "Diseño, marketing, pauta digital"),
    ("Papelería",            "Papelería",         "GASTO", "519520", "__BANK__", "Útiles, papelería, impresiones"),
    ("Gastos Bancarios",     "Gastos Bancarios",  "GASTO", "519505", "__BANK__", "Comisiones, cuota de manejo"),
    ("Nómina",               "Nómina",            "GASTO", "510506", "__BANK__", "Sueldos y salarios"),
    ("Gastos Diversos",      "Otros Gastos",      "GASTO", "519515", "__BANK__", "Gastos varios no categorizados"),

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
