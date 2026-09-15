# -*- coding: utf-8 -*-
"""E2E: POST /api/transactions → asiento Zero-COA en la MISMA transacción.

Requiere un backend vivo (FINSYS_BASE, default http://127.0.0.1:8000) y el
.env del repo (firma el token con el mismo secreto). Crea UNA transacción de
prueba y la elimina al final (limpieza también de sus líneas del diario).

Reescrito 2026-09-15 (plan cimientos A3): la versión anterior consultaba
/api/kernel/* (rutas que ya no existen) y dejaba la TX de prueba en la BD.
"""
import json
import os
import sys
import urllib.parse
import urllib.request

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _REPO)
if os.path.exists(os.path.join(_REPO, ".env")):
    with open(os.path.join(_REPO, ".env"), "r", encoding="utf-8") as _f:
        for _line in _f:
            _line = _line.strip()
            if _line and not _line.startswith("#") and "=" in _line:
                _k, _v = _line.split("=", 1)
                os.environ.setdefault(_k.strip(), _v.strip())

BASE = os.environ.get("FINSYS_BASE", "http://127.0.0.1:8000")

from routers.auth_guard import create_session_token  # noqa: E402

TOKEN = create_session_token({"id": "e2e", "name": "Test E2E", "role": "admin"})
HDRS = {"Content-Type": "application/json", "Authorization": f"Bearer {TOKEN}"}


def post(path, data):
    req = urllib.request.Request(f"{BASE}{path}", data=json.dumps(data).encode(), headers=HDRS)
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read())


def get(path):
    req = urllib.request.Request(f"{BASE}{path}", headers=HDRS)
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read())


def limpiar(tx_id):
    """Elimina la TX de prueba (revierte saldos) y sus líneas del diario."""
    import fin_sys_core  # noqa: F401
    from fin_sys_core.database_driver import eliminar_transaccion
    from fin_sys_core.db_pool import get_conn, put_conn
    try:
        eliminar_transaccion(tx_id)
    except ValueError:
        pass   # ya la borró el paso 5 (DELETE por API)
    except Exception as e:
        print(f"   ⚠️ no se pudo eliminar la TX {tx_id}: {e}")
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute("DELETE FROM kernel_journal_entries WHERE referencia IN (%s, %s)",
                    (f"TX-{tx_id}", f"REV-TX-{tx_id}"))
        n = cur.rowcount
        conn.commit()
        cur.close()
        print(f"   🧹 limpieza: TX {tx_id} eliminada, {n} líneas del diario borradas")
    finally:
        put_conn(conn)


def main():
    print("=" * 65)
    print(f"E2E: TX → asiento atómico  ({BASE})")
    print("=" * 65)
    fallos = []
    tx = post("/api/transactions", {
        "type": "GASTO",
        "amount": 350000,
        "concept": "Pago hosting servidor (TEST KERNEL E2E)",
        "transaction_date": "2026-06-19",
        "payment_method": "Transferencia",
        "category": "Infraestructura",
        "portfolio_name": "Negocio A",
        "third_party": {"identification_type": "NIT",
                        "identification_number": "900.999.001-1",
                        "name": "Cloud Hosting SAS"},
        "apply_iva": False,
        "apply_gmf": True,
        "account_id": 2,
    })
    tx_id = tx.get("transaction_id")
    print(f"1. TX creada: id={tx_id} journal={tx.get('journal')} net={tx.get('net_value')}")
    if tx.get("journal") != "ok":
        fallos.append(f"journal esperado 'ok', llegó {tx.get('journal')!r}")
    try:
        ref = urllib.parse.quote(f"TX-{tx_id}")
        lineas = [e for e in get("/api/journal-entries?modulo_origen=zero_coa&limit=200")
                  if e.get("referencia") == f"TX-{tx_id}"]
        print(f"2. Líneas del diario para TX-{tx_id}: {len(lineas)}")
        for e in lineas:
            print(f"   {e['entry_group_id']} | {e['cuenta_codigo']:>8} | "
                  f"Db={float(e['debito']):>12,.2f} | Cr={float(e['credito']):>12,.2f}")
        if len(lineas) != 2:
            fallos.append(f"esperaba 2 líneas, hay {len(lineas)}")
        else:
            db = sum(float(e["debito"]) for e in lineas)
            cr = sum(float(e["credito"]) for e in lineas)
            print(f"3. Partida doble: Db={db:,.2f} Cr={cr:,.2f} → {'CUADRA' if abs(db - cr) < 0.01 else 'NO CUADRA'}")
            if abs(db - cr) >= 0.01:
                fallos.append("partida doble no cuadra")
            if abs(db - float(tx.get("net_value") or 0)) >= 0.01:
                fallos.append(f"el débito {db} no coincide con net_value {tx.get('net_value')}")
        resumen = get("/api/financial-summary")
        print(f"4. financial-summary: ecuación contable = {resumen.get('ecuacion_contable')}")

        # 5. (opcional) Borrado por API → contra-asiento REV-TX-{id} (plan A4).
        # Exige la clave admin real: FINSYS_ADMIN_PASSWORD (no va en el repo).
        clave = os.environ.get("FINSYS_ADMIN_PASSWORD")
        if clave and tx_id:
            req = urllib.request.Request(f"{BASE}/api/transactions/{tx_id}",
                                         data=json.dumps({"password": clave}).encode(),
                                         headers=HDRS, method="DELETE")
            with urllib.request.urlopen(req, timeout=60) as r:
                borrado = json.loads(r.read())
            print(f"5. DELETE por API: {borrado.get('status')} journal={borrado.get('journal')}")
            if borrado.get("journal", {}).get(f"TX-{tx_id}") != "ok":
                fallos.append(f"el borrado no generó contra-asiento: {borrado.get('journal')}")
            todas = [e for e in get("/api/journal-entries?modulo_origen=zero_coa&limit=200")
                     if e.get("referencia") in (f"TX-{tx_id}", f"REV-TX-{tx_id}")]
            neto = {}
            for e in todas:
                neto[e["cuenta_codigo"]] = neto.get(e["cuenta_codigo"], 0.0) + float(e["debito"]) - float(e["credito"])
            print(f"   líneas TX+REV: {len(todas)} | neto por cuenta: {neto}")
            if len(todas) != 4 or any(abs(v) >= 0.01 for v in neto.values()):
                fallos.append(f"contra-asiento incompleto: {len(todas)} líneas, neto {neto}")
        else:
            print("5. DELETE por API omitido (define FINSYS_ADMIN_PASSWORD para probarlo)")
    finally:
        if tx_id:
            limpiar(tx_id)
    print("=" * 65)
    if fallos:
        print("❌ FALLOS:")
        for f in fallos:
            print("   -", f)
        sys.exit(1)
    print("✅ E2E OK")


if __name__ == "__main__":
    main()
