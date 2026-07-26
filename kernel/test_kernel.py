# -*- coding: utf-8 -*-
"""
test_kernel.py — Tests HONESTOS del kernel contable.

Reemplaza la versión anterior (prints sin asserts que "pasaban" aunque todo
fallara y dejaban datos en la BD real).

Propiedades verificadas:
  1. Partida doble: asiento descuadrado → PartidaDobleError (tolerancia CERO)
  2. Precisión: 0.1+0.2 con float clásico descuadra; con Decimal cuadra exacto
  3. Cuentas fantasma: código inexistente en COA → CuentaNoExisteError
  4. Idempotencia: re-emitir la misma referencia NO duplica asientos
  5. cuenta_tipo se deriva del PUC cuando viene vacío
  6. El asiento OK inserta exactamente sus líneas, cuadradas

Todo inserta con referencias TEST-KRN-* y se limpia en el finally, pase lo
que pase. Ejecutable sin pytest:  python -m kernel.test_kernel
"""
import os
import sys
import uuid

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)


def _load_env():
    env_path = os.path.join(ROOT, ".env")
    if not os.path.exists(env_path):
        return
    with open(env_path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, val = line.partition("=")
            os.environ.setdefault(key.strip(), val.strip().strip('"').strip("'"))


_load_env()

from kernel.kernel_accounting import (  # noqa: E402
    PartidaDobleError, CuentaNoExisteError, registrar_asiento, derivar_tipo_puc,
)
from fin_sys_core.db_pool import get_conn, put_conn  # noqa: E402

# Sufijo único por corrida: dos corridas simultáneas no chocan entre sí
RUN = uuid.uuid4().hex[:6]
PREFIX = f"TEST-KRN-{RUN}"

# Cuentas válidas en esta BD: 111005 está en chart_of_accounts,
# 5105 está declarada en posting_rules activas (unión = válido)
CTA_BANCO = "111005"
CTA_GASTO = "5105"
CTA_FANTASMA = "999999"  # no existe ni en COA ni en reglas


def _evento(ref, asientos, fecha="2026-01-15"):
    return {
        "fecha": fecha, "modulo_origen": "test_kernel",
        "referencia": ref, "descripcion": "test honesto kernel",
        "asientos": asientos,
    }


def _contar_lineas(ref):
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT COUNT(*), COUNT(DISTINCT entry_group_id) FROM kernel_journal_entries WHERE referencia = %s",
            (ref,),
        )
        n, grupos = cur.fetchone()
        cur.close()
        return n, grupos
    finally:
        put_conn(conn)


def _cleanup():
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute(
            "DELETE FROM kernel_journal_entries WHERE referencia LIKE %s",
            (f"{PREFIX}%",),
        )
        borradas = cur.rowcount
        conn.commit()
        cur.close()
        return borradas
    finally:
        put_conn(conn)


# ── Tests ─────────────────────────────────────────────────────────────────────

def test_descuadre_rechazado():
    try:
        registrar_asiento(_evento(f"{PREFIX}-DESC", [
            {"cuenta_codigo": CTA_GASTO, "debito": 100, "credito": 0},
            {"cuenta_codigo": CTA_BANCO, "debito": 0, "credito": 99.99},
        ]))
        raise AssertionError("Asiento descuadrado por $0.01 fue ACEPTADO (tolerancia debe ser 0)")
    except PartidaDobleError:
        pass  # esperado
    n, _ = _contar_lineas(f"{PREFIX}-DESC")
    assert n == 0, f"El asiento rechazado dejó {n} líneas en BD"


def test_decimal_cuadra_exacto():
    # 0.1 + 0.2 != 0.3 en float — con Decimal el asiento cuadra exacto
    r = registrar_asiento(_evento(f"{PREFIX}-DEC", [
        {"cuenta_codigo": CTA_GASTO, "debito": 0.1, "credito": 0},
        {"cuenta_codigo": CTA_GASTO, "debito": 0.2, "credito": 0},
        {"cuenta_codigo": CTA_BANCO, "debito": 0, "credito": 0.3},
    ]))
    assert r["status"] == "ok", f"Asiento 0.1+0.2=0.3 rechazado: {r}"
    n, grupos = _contar_lineas(f"{PREFIX}-DEC")
    assert n == 3 and grupos == 1, f"Esperaba 3 líneas/1 grupo, hay {n}/{grupos}"


def test_cuenta_fantasma_rechazada():
    try:
        registrar_asiento(_evento(f"{PREFIX}-GHOST", [
            {"cuenta_codigo": CTA_FANTASMA, "debito": 0, "credito": 500},
            {"cuenta_codigo": CTA_BANCO, "debito": 500, "credito": 0},
        ]))
        raise AssertionError(f"Cuenta {CTA_FANTASMA} (inexistente) fue ACEPTADA")
    except CuentaNoExisteError:
        pass  # esperado
    n, _ = _contar_lineas(f"{PREFIX}-GHOST")
    assert n == 0, f"El asiento con cuenta fantasma dejó {n} líneas"


def test_idempotencia():
    ref = f"{PREFIX}-IDEM"
    asientos = [
        {"cuenta_codigo": CTA_GASTO, "debito": 1000, "credito": 0},
        {"cuenta_codigo": CTA_BANCO, "debito": 0, "credito": 1000},
    ]
    r1 = registrar_asiento(_evento(ref, asientos))
    assert r1["status"] == "ok", f"Primera emisión falló: {r1}"
    r2 = registrar_asiento(_evento(ref, asientos))  # re-emit exacto
    assert r2["status"] == "skipped_duplicate", f"Re-emisión NO fue omitida: {r2}"
    assert r2["entry_group_id"] == r1["entry_group_id"]
    n, grupos = _contar_lineas(ref)
    assert n == 2 and grupos == 1, f"Idempotencia rota: {n} líneas / {grupos} grupos"


def test_tipo_derivado_del_puc():
    assert derivar_tipo_puc("111005") == "ACTIVO"
    assert derivar_tipo_puc("2408") == "PASIVO"
    assert derivar_tipo_puc("417505") == "INGRESO"
    assert derivar_tipo_puc("513520") == "GASTO"
    ref = f"{PREFIX}-TIPO"
    registrar_asiento(_evento(ref, [
        # cuenta_tipo ausente a propósito: el kernel debe derivarlo
        {"cuenta_codigo": CTA_GASTO, "debito": 200, "credito": 0},
        {"cuenta_codigo": CTA_BANCO, "debito": 0, "credito": 200},
    ]))
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT cuenta_codigo, cuenta_tipo FROM kernel_journal_entries WHERE referencia = %s ORDER BY linea",
            (ref,),
        )
        tipos = dict(cur.fetchall())
        cur.close()
    finally:
        put_conn(conn)
    assert tipos.get(CTA_GASTO) == "GASTO", f"Tipo no derivado: {tipos}"
    assert tipos.get(CTA_BANCO) == "ACTIVO", f"Tipo no derivado: {tipos}"


TESTS = [
    test_descuadre_rechazado,
    test_decimal_cuadra_exacto,
    test_cuenta_fantasma_rechazada,
    test_idempotencia,
    test_tipo_derivado_del_puc,
]


def main():
    fallos = 0
    try:
        for t in TESTS:
            try:
                t()
                print(f"  PASS  {t.__name__}")
            except Exception as e:
                fallos += 1
                print(f"  FAIL  {t.__name__}: {e}")
    finally:
        borradas = _cleanup()
        print(f"  cleanup: {borradas} líneas de prueba eliminadas")
    print(f"\n{len(TESTS) - fallos}/{len(TESTS)} tests OK")
    sys.exit(1 if fallos else 0)


if __name__ == "__main__":
    main()
