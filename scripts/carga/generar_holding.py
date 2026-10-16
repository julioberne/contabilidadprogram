# -*- coding: utf-8 -*-
"""Genera un HOLDING SINTÉTICO en el Postgres LOCAL del laboratorio de carga.

Estándar de consultas, hito H1 (regla P14). Representa el caso difícil:
- N empresas; la primera es una "ballena" con muchas más transacciones.
- Miles de terceros, 10 % de transferencias y el 40 % de los movimientos
  concentrados en 3 cuentas bancarias (cuentas calientes).

Se niega a correr contra cualquier host que no sea localhost (scripts/carga/
_seguro.py). El esquema lo crea el propio backend al arrancar contra la BD
del laboratorio (DDL de arranque), así que primero corre escenarios.py
--solo-esquema o arranca el backend una vez.

    python scripts\\carga\\generar_holding.py --escala chica      # ~60k TX
    python scripts\\carga\\generar_holding.py --escala grande     # ~2,5M TX
"""
import argparse
import os
import random
import sys
import time
from datetime import date, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _seguro import exigir_local  # noqa: E402

ESCALAS = {
    #          empresas, tx_ballena, tx_otras(min,max), terceros
    "chica":  (10, 20_000, (2_000, 6_000), 3_000),
    "media":  (30, 300_000, (5_000, 30_000), 15_000),
    "grande": (50, 2_000_000, (10_000, 100_000), 50_000),
}

CONCEPTOS = ["Pago proveedor", "Compra insumos", "Nómina quincena", "Arriendo bodega", "Venta contado",
             "Abono cliente", "Transporte obra", "Servicios públicos", "Café reunión", "Honorarios",
             "Mantenimiento equipo", "Publicidad", "Impuesto predial", "Seguro vehículo"]
CATEGORIAS = ["5105 - Gastos de personal", "5120 - Arrendamientos", "5135 - Servicios",
              "4135 - Comercio", "5195 - Diversos", "Otros Gastos", "Ventas"]
ETIQUETAS = ["Bonaire obra", "Oficina", "Mercado", "Transporte", "Recurrente", "Proyecto A", "Proyecto B"]


def conectar(args):
    import psycopg2
    exigir_local(args.host, args.puerto)
    return psycopg2.connect(host=args.host, port=args.puerto, dbname=args.db,
                            user=args.usuario, password=args.clave)


def asegurar_columnas(cur):
    # Columnas que en producción agregaron migraciones y el DDL de arranque no crea.
    cur.execute("ALTER TABLE transactions ADD COLUMN IF NOT EXISTS tags TEXT[]")
    cur.execute("ALTER TABLE transactions ADD COLUMN IF NOT EXISTS note TEXT")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--escala", choices=ESCALAS, default="chica")
    ap.add_argument("--host", default="localhost")
    ap.add_argument("--puerto", default="55432")
    ap.add_argument("--db", default="finsys_carga")
    ap.add_argument("--usuario", default="postgres")
    ap.add_argument("--clave", default="carga")
    ap.add_argument("--semilla", type=int, default=16102026)
    args = ap.parse_args()

    from psycopg2.extras import execute_values
    random.seed(args.semilla)
    n_emp, tx_ballena, (tx_min, tx_max), n_terceros = ESCALAS[args.escala]
    conn = conectar(args)
    cur = conn.cursor()
    asegurar_columnas(cur)
    t0 = time.time()

    execute_values(cur, "INSERT INTO portfolios (name, industry_type) VALUES %s ON CONFLICT DO NOTHING",
                   [(f"CARGA EMPRESA {i:03d}", "ESTANDAR") for i in range(n_emp)])
    cur.execute("SELECT id FROM portfolios WHERE name LIKE 'CARGA EMPRESA %%' ORDER BY name")
    empresas = [r[0] for r in cur.fetchall()]

    execute_values(cur, "INSERT INTO user_accounts (name, type, currency, initial_balance, current_balance) "
                        "VALUES %s ON CONFLICT (name) DO NOTHING",
                   [(f"CARGA CUENTA {i:03d}", "Ahorros", "COP", 10_000_000, 10_000_000) for i in range(40)])
    cur.execute("SELECT id FROM user_accounts WHERE name LIKE 'CARGA CUENTA %%' ORDER BY name")
    cuentas = [r[0] for r in cur.fetchall()]
    calientes = cuentas[:3]

    execute_values(cur, "INSERT INTO third_parties (identification_type, identification_number, name) "
                        "VALUES %s ON CONFLICT (identification_number) DO NOTHING",
                   [("NIT" if i % 3 else "CC", f"CARGA{900000000 + i}", f"Tercero sintético {i:05d}")
                    for i in range(n_terceros)], page_size=5000)
    cur.execute("SELECT id FROM third_parties WHERE identification_number LIKE 'CARGA%%'")
    terceros = [r[0] for r in cur.fetchall()]
    conn.commit()

    hoy = date.today()
    sql_tx = ("INSERT INTO transactions (portfolio_id, third_party_id, type, amount, concept, transaction_date, "
              "payment_method, category, net_value, account_id, dest_account_id, transaction_currency, tags, note) "
              "VALUES %s")
    total = 0
    for idx, emp in enumerate(empresas):
        n = tx_ballena if idx == 0 else random.randint(tx_min, tx_max)
        lote = []
        for _ in range(n):
            r = random.random()
            tipo = "TRANSFERENCIA" if r < 0.10 else ("INGRESO" if r < 0.35 else "GASTO")
            cta = random.choice(calientes) if random.random() < 0.40 else random.choice(cuentas)
            dest = random.choice([c for c in cuentas if c != cta]) if tipo == "TRANSFERENCIA" else None
            monto = round(random.lognormvariate(12, 1.3), 2)          # mediana ~160 mil
            tags = random.sample(ETIQUETAS, random.choice([0, 0, 1, 2])) or None
            lote.append((emp, random.choice(terceros), tipo, monto, random.choice(CONCEPTOS),
                         hoy - timedelta(days=random.randint(0, 3 * 365)), "Banco",
                         random.choice(CATEGORIAS), monto, cta, dest, "COP", tags,
                         "nota" if random.random() < 0.05 else None))
            if len(lote) >= 20_000:
                execute_values(cur, sql_tx, lote, page_size=5000)
                conn.commit()
                total += len(lote)
                lote = []
                print(f"   … {total:,} transacciones ({time.time() - t0:.0f}s)")
        if lote:
            execute_values(cur, sql_tx, lote, page_size=5000)
            conn.commit()
            total += len(lote)
    cur.execute("ANALYZE")
    conn.commit()
    print(f"✅ Holding sintético '{args.escala}': {len(empresas)} empresas, {len(terceros):,} terceros, "
          f"{total:,} transacciones en {time.time() - t0:.0f}s")
    conn.close()


if __name__ == "__main__":
    main()
