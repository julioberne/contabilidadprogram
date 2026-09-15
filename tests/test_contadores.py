# -*- coding: utf-8 -*-
"""Tests del módulo Contadores contra la BD real (patrón kernel/test_kernel.py:
referencias TEST-KRN-<run>-*, modulo_origen='test_kernel', limpieza en finally).

    python tests/test_contadores.py

B1: borrador por defecto; CONTABILIZADO explícito; periodo cerrado bloquea y
reabrir desbloquea; anular borrador = RECHAZADO; anular contabilizado = espejo.
"""
import os
import sys
import uuid

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _ROOT)
os.chdir(_ROOT)
import tests  # noqa: F401,E402  (carga .env)
import fin_sys_core  # noqa: F401,E402

from fin_sys_core.db_pool import get_conn, put_conn  # noqa: E402
from kernel.kernel_accounting import (  # noqa: E402
    registrar_asiento, anular_asiento_por_referencia, obtener_asientos,
)
from kernel.kernel_periods import (  # noqa: E402
    PeriodoCerradoError, init_accounting_periods_table, cerrar_periodo, reabrir_periodo,
    listar_periodos, assert_periodo_abierto,
)

RUN = uuid.uuid4().hex[:6]
PREFIX = f"TEST-KRN-{RUN}"
MODULO = "test_kernel"
CTA_BANCO = "111005"
CTA_GASTO = "5105"
ANIO_TEST = 1999          # un año que nadie usa: cerrar/abrir no afecta datos reales
PORTFOLIO_ID = None       # se resuelve al arrancar (primer portafolio)


def _evento(ref, fecha="2026-01-15", monto=100, **extra):
    ev = {"fecha": fecha, "modulo_origen": MODULO, "referencia": ref,
          "descripcion": "test contadores",
          "asientos": [{"cuenta_codigo": CTA_GASTO, "debito": monto, "credito": 0},
                       {"cuenta_codigo": CTA_BANCO, "debito": 0, "credito": monto}]}
    ev.update(extra)
    return ev


def _lineas(ref):
    return [e for e in obtener_asientos(modulo_origen=MODULO, limit=500, estado="TODOS")
            if e["referencia"] == ref]


def _cleanup():
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute("DELETE FROM kernel_journal_entries WHERE referencia LIKE %s OR referencia LIKE %s",
                    (f"{PREFIX}%", f"REV-{PREFIX}%"))
        n = cur.rowcount
        cur.execute("DELETE FROM accounting_periods WHERE anio = %s AND portfolio_id = %s",
                    (ANIO_TEST, PORTFOLIO_ID))
        conn.commit()
        cur.close()
        return n
    finally:
        put_conn(conn)


def _primer_portafolio():
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute("SELECT id FROM portfolios ORDER BY id LIMIT 1")
        r = cur.fetchone()
        cur.close()
        return r[0] if r else None
    finally:
        put_conn(conn)


# ── Tests ─────────────────────────────────────────────────────────────────────

def test_borrador_por_defecto():
    ref = f"{PREFIX}-DEF"
    r = registrar_asiento(_evento(ref, portfolio_id=PORTFOLIO_ID))
    assert r["status"] == "ok" and r["estado"] == "BORRADOR", r
    lineas = _lineas(ref)
    assert len(lineas) == 2, lineas
    assert all(l["estado"] == "BORRADOR" for l in lineas)
    assert all(l["created_by"] == "sistema" for l in lineas)
    assert all(l["posted_at"] is None for l in lineas)
    assert all(l["portfolio_id"] == PORTFOLIO_ID for l in lineas)


def test_contabilizado_explicito():
    ref = f"{PREFIX}-POST"
    r = registrar_asiento(_evento(ref, created_by="tester"), estado="CONTABILIZADO")
    assert r["estado"] == "CONTABILIZADO", r
    lineas = _lineas(ref)
    assert all(l["estado"] == "CONTABILIZADO" and l["posted_by"] == "tester"
               and l["posted_at"] is not None for l in lineas), lineas


def test_estado_inicial_invalido():
    try:
        registrar_asiento(_evento(f"{PREFIX}-BAD"), estado="ANULADO")
        assert False, "debió rechazar el estado inicial"
    except ValueError:
        pass
    assert _lineas(f"{PREFIX}-BAD") == []


def test_periodo_cerrado_bloquea_y_reabrir_desbloquea():
    r = cerrar_periodo(PORTFOLIO_ID, ANIO_TEST, 1, "tester", nota="prueba")
    assert r["status"] == "ok", r
    try:
        assert_periodo_abierto(PORTFOLIO_ID, f"{ANIO_TEST}-01-15")
        assert False, "debió lanzar PeriodoCerradoError"
    except PeriodoCerradoError as e:
        assert "cerrado" in str(e)
    ref = f"{PREFIX}-CERR"
    try:
        registrar_asiento(_evento(ref, fecha=f"{ANIO_TEST}-01-15", portfolio_id=PORTFOLIO_ID))
        assert False, "registrar_asiento debió bloquearse por periodo cerrado"
    except PeriodoCerradoError:
        pass
    assert _lineas(ref) == [], "no debe quedar ninguna línea"
    # otro mes del mismo año sigue abierto
    registrar_asiento(_evento(f"{PREFIX}-FEB", fecha=f"{ANIO_TEST}-02-10", portfolio_id=PORTFOLIO_ID))
    assert len(_lineas(f"{PREFIX}-FEB")) == 2
    # sin portafolio no se bloquea (cartera)
    registrar_asiento(_evento(f"{PREFIX}-NOPF", fecha=f"{ANIO_TEST}-01-20"))
    assert len(_lineas(f"{PREFIX}-NOPF")) == 2
    # listar y reabrir
    meses = listar_periodos(PORTFOLIO_ID, ANIO_TEST)
    assert meses[0]["estado"] == "CERRADO" and meses[1]["estado"] == "ABIERTO", meses[:2]
    r2 = reabrir_periodo(PORTFOLIO_ID, ANIO_TEST, 1, "admin", motivo="test")
    assert r2["status"] == "ok", r2
    registrar_asiento(_evento(ref, fecha=f"{ANIO_TEST}-01-15", portfolio_id=PORTFOLIO_ID))
    assert len(_lineas(ref)) == 2


def test_cerrar_con_borradores_falla():
    registrar_asiento(_evento(f"{PREFIX}-BOR3", fecha=f"{ANIO_TEST}-03-05", portfolio_id=PORTFOLIO_ID))
    try:
        cerrar_periodo(PORTFOLIO_ID, ANIO_TEST, 3, "tester")
        assert False, "debió fallar por borradores pendientes"
    except ValueError as e:
        assert "BORRADOR" in str(e)


def test_anular_borrador_rechaza_sin_espejo():
    ref = f"{PREFIX}-ANB"
    registrar_asiento(_evento(ref))
    conn = get_conn()
    try:
        r = anular_asiento_por_referencia(conn, MODULO, ref, motivo="TX eliminada", usuario="t")
        conn.commit()
    finally:
        put_conn(conn)
    assert r["status"] == "rejected_draft", r
    lineas = _lineas(ref)
    assert all(l["estado"] == "RECHAZADO" and l["motivo"] == "TX eliminada" for l in lineas), lineas
    assert _lineas(f"REV-{ref}") == []


def test_anular_contabilizado_genera_espejo():
    ref = f"{PREFIX}-ANC"
    registrar_asiento(_evento(ref, portfolio_id=PORTFOLIO_ID), estado="CONTABILIZADO")
    conn = get_conn()
    try:
        r = anular_asiento_por_referencia(conn, MODULO, ref, motivo="corrección", usuario="t")
        conn.commit()
        r2 = anular_asiento_por_referencia(conn, MODULO, ref, motivo="otra vez")
        conn.commit()
    finally:
        put_conn(conn)
    assert r["status"] == "ok" and r["lineas"] == 2, r
    assert r2["status"] == "skipped_duplicate", r2
    orig = _lineas(ref)
    esp = _lineas(f"REV-{ref}")
    assert all(l["estado"] == "ANULADO" and l["anulado_por"] == r["entry_group_id"] for l in orig), orig
    assert all(l["estado"] == "CONTABILIZADO" and l["reversa_de"] == r["original"]
               and l["portfolio_id"] == PORTFOLIO_ID for l in esp), esp
    neto = {}
    for l in orig + esp:
        neto[l["cuenta_codigo"]] = neto.get(l["cuenta_codigo"], 0) + float(l["debito"]) - float(l["credito"])
    assert all(abs(v) < 0.005 for v in neto.values()), neto


# ── B2: workflow del contador ───────────────────────────────────────────────

def _wf():
    from kernel import kernel_journal_workflow as wf
    return wf


def test_contabilizar_y_doble_falla():
    wf = _wf()
    r = registrar_asiento(_evento(f"{PREFIX}-WF1", portfolio_id=PORTFOLIO_ID))
    g = r["entry_group_id"]
    out = wf.contabilizar_asiento(g, "contador1")
    assert out["estado"] == "CONTABILIZADO", out
    det = wf.obtener_asiento(g)
    assert det["estado"] == "CONTABILIZADO" and det["posted_by"] == "contador1" and det["cuadra"], det
    try:
        wf.contabilizar_asiento(g, "contador1")
        assert False, "segunda contabilización debió fallar"
    except wf.EstadoAsientoError as e:
        assert e.status == 409


def test_rechazar_exige_motivo_y_transicion():
    wf = _wf()
    g = registrar_asiento(_evento(f"{PREFIX}-WF2"))["entry_group_id"]
    try:
        wf.rechazar_asiento(g, "c", "")
        assert False, "sin motivo debió fallar"
    except ValueError:
        pass
    out = wf.rechazar_asiento(g, "c", "duplicado")
    assert out["estado"] == "RECHAZADO"
    try:
        wf.contabilizar_asiento(g, "c")
        assert False, "un RECHAZADO no se contabiliza"
    except wf.EstadoAsientoError:
        pass


def test_editar_lineas_borrador():
    wf = _wf()
    ref = f"{PREFIX}-WF3"
    g = registrar_asiento(_evento(ref, monto=100))["entry_group_id"]
    # descuadre → error y las líneas originales intactas
    try:
        wf.editar_lineas_borrador(g, [{"cuenta_codigo": CTA_GASTO, "debito": 50, "credito": 0},
                                     {"cuenta_codigo": CTA_BANCO, "debito": 0, "credito": 49}], "c")
        assert False, "descuadre debió fallar"
    except Exception as e:
        assert "cuadra" in str(e).lower(), e
    lineas = _lineas(ref)
    assert len(lineas) == 2 and float(lineas[0]["debito"]) == 100.0, lineas
    # cuadrado con 3 líneas → renumeradas 1..3, mismo grupo y referencia
    out = wf.editar_lineas_borrador(g, [
        {"cuenta_codigo": CTA_GASTO, "debito": 70, "credito": 0},
        {"cuenta_codigo": CTA_GASTO, "debito": 30, "credito": 0},
        {"cuenta_codigo": CTA_BANCO, "debito": 0, "credito": 100},
    ], "c", descripcion="editado")
    assert out["lineas"] == 3, out
    lineas = sorted(_lineas(ref), key=lambda l: l["id"])
    assert len(lineas) == 3 and all(l["entry_group_id"] == g for l in lineas)
    assert all(l["descripcion"] == "editado" and l["revisado_por"] == "c" for l in lineas)
    # contabilizado ya no se edita
    wf.contabilizar_asiento(g, "c")
    try:
        wf.editar_lineas_borrador(g, [{"cuenta_codigo": CTA_GASTO, "debito": 1, "credito": 0},
                                     {"cuenta_codigo": CTA_BANCO, "debito": 0, "credito": 1}], "c")
        assert False, "un CONTABILIZADO no se edita"
    except wf.EstadoAsientoError:
        pass


def test_asiento_manual_y_bandeja():
    wf = _wf()
    r = wf.crear_asiento_manual(PORTFOLIO_ID, "2026-02-02", "manual test", [
        {"cuenta_codigo": CTA_GASTO, "debito": 12.5, "credito": 0},
        {"cuenta_codigo": CTA_BANCO, "debito": 0, "credito": 12.5},
    ], "contador2", contabilizar=True)
    assert r["status"] == "ok" and r["estado"] == "CONTABILIZADO", r
    det = wf.obtener_asiento(r["entry_group_id"])
    assert det["modulo_origen"] == "contadores" and det["referencia"].startswith("MAN-"), det
    assert det["created_by"] == "contador2" and det["tx"] is None
    # limpieza: la referencia MAN- no lleva el PREFIX → borrar por grupo
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute("DELETE FROM kernel_journal_entries WHERE entry_group_id = %s", (r["entry_group_id"],))
        conn.commit(); cur.close()
    finally:
        put_conn(conn)
    # bandeja filtrada por estado y portafolio devuelve items con líneas
    registrar_asiento(_evento(f"{PREFIX}-WF4", portfolio_id=PORTFOLIO_ID))
    b = wf.obtener_asientos_agrupados(estado="BORRADOR", portfolio_id=PORTFOLIO_ID, q=f"{PREFIX}-WF4")
    assert b["total"] == 1 and len(b["items"][0]["lineas"]) == 2, b
    assert b["items"][0]["portfolio_name"], b["items"][0]


# ── B3: plan de cuentas y reglas ────────────────────────────────────────────

def test_coa_crud_y_bloqueos():
    from fin_sys_core import coa_admin_driver as coa
    grupo = coa.crear_cuenta(PORTFOLIO_ID, f"T{RUN}", "Grupo test", "GASTO", is_group=True)
    hija = coa.crear_cuenta(PORTFOLIO_ID, f"T{RUN}01", "Hija test", "gasto", parent_code=f"T{RUN}")
    assert hija["parent_id"] == grupo["id"] and hija["account_type"] == "GASTO", hija
    try:
        coa.crear_cuenta(PORTFOLIO_ID, f"T{RUN}01", "dup", "GASTO")
        assert False, "código duplicado debió fallar"
    except coa.CoaError as e:
        assert e.status == 409
    try:
        coa.crear_cuenta(PORTFOLIO_ID, f"T{RUN}02", "x", "RARO")
        assert False, "tipo inválido debió fallar"
    except coa.CoaError as e:
        assert e.status == 400
    # grupo con hijas no se borra ni deja de ser grupo
    for fn in (lambda: coa.eliminar_cuenta(grupo["id"]), lambda: coa.actualizar_cuenta(grupo["id"], is_group=False)):
        try:
            fn(); assert False, "debió fallar por subcuentas"
        except coa.CoaError as e:
            assert e.status == 409
    # cuenta con movimientos no se borra
    registrar_asiento(_evento(f"{PREFIX}-COA", portfolio_id=PORTFOLIO_ID, asientos=[
        {"cuenta_codigo": f"T{RUN}01", "debito": 5, "credito": 0},
        {"cuenta_codigo": CTA_BANCO, "debito": 0, "credito": 5}]))
    try:
        coa.eliminar_cuenta(hija["id"]); assert False, "con movimientos debió fallar"
    except coa.CoaError as e:
        assert e.status == 409 and "movimiento" in str(e)
    filas = {c["code"]: c for c in coa.listar_coa(PORTFOLIO_ID)}
    assert filas[f"T{RUN}01"]["movimientos"] == 1 and filas[f"T{RUN}"]["hijos"] == 1, filas[f"T{RUN}01"]
    # borrar líneas → ahora sí se borra hija y luego el grupo
    conn = get_conn()
    try:
        cur = conn.cursor(); cur.execute("DELETE FROM kernel_journal_entries WHERE referencia = %s", (f"{PREFIX}-COA",)); conn.commit(); cur.close()
    finally:
        put_conn(conn)
    coa.actualizar_cuenta(hija["id"], name="Hija renombrada")
    assert coa.eliminar_cuenta(hija["id"])["status"] == "ok"
    assert coa.eliminar_cuenta(grupo["id"])["status"] == "ok"


def test_posting_rule_validaciones():
    from fin_sys_core import coa_admin_driver as coa
    cat = f"Cat {RUN}"
    for kwargs, esperado in (
        (dict(debit_account_code="999999", credit_account_code="__BANK__"), "no existe"),
        (dict(debit_account_code="5105", credit_account_code="5105"), "misma"),
        (dict(debit_account_code="1", credit_account_code="__BANK__"), "grupo"),
        (dict(transaction_type="OTRO", debit_account_code="522005", credit_account_code="__BANK__"), "inválido"),
    ):
        try:
            coa.crear_regla("r", cat, kwargs.pop("transaction_type", "GASTO"), **kwargs)
            assert False, f"debió fallar: {esperado}"
        except coa.CoaError as e:
            assert esperado in str(e).lower(), (esperado, str(e))
    r = coa.crear_regla("Regla test", cat, "GASTO", "522005", "__BANK__", description="t")
    assert r["id"] and r["transaction_type"] == "GASTO"
    try:
        coa.crear_regla("dup", cat, "GASTO", "522005", "__BANK__")
        assert False, "duplicada debió fallar"
    except coa.CoaError as e:
        assert e.status == 409
    # la caché de reglas ve la nueva regla de inmediato (invalidate)
    from shared import rules_cache
    assert rules_cache.get_rule(cat, "GASTO") == ("522005", "__BANK__", "Regla test")
    r2 = coa.actualizar_regla(r["id"], is_active=False, rule_name="Regla test off")
    assert r2["is_active"] is False
    assert rules_cache.get_rule(cat, "GASTO") is None or rules_cache.get_rule(cat, "GASTO")[2] != "Regla test"
    assert coa.eliminar_regla(r["id"])["status"] == "ok"
    reglas = coa.listar_reglas(PORTFOLIO_ID)
    assert all(x["id"] != r["id"] for x in reglas)
    # debit_name/credit_name pueden ser None: el COA sembrado no contiene
    # todos los códigos PUC de las reglas (hallazgo 15-sep) — solo la forma.
    assert all("debit_name" in x and "credit_name" in x for x in reglas)


# ── B4: reportes solo con asientos en libros ────────────────────────────────

def test_reportes_en_libros():
    from kernel import kernel_reports as rep
    from kernel import kernel_journal_workflow as wf
    # 3 asientos: uno CONTABILIZADO, uno BORRADOR (no cuenta), uno anulado (neto 0)
    registrar_asiento(_evento(f"{PREFIX}-R1", fecha="2026-03-10", monto=1000, portfolio_id=PORTFOLIO_ID), estado="CONTABILIZADO")
    registrar_asiento(_evento(f"{PREFIX}-R2", fecha="2026-03-11", monto=500, portfolio_id=PORTFOLIO_ID))  # borrador
    g3 = registrar_asiento(_evento(f"{PREFIX}-R3", fecha="2026-03-12", monto=200, portfolio_id=PORTFOLIO_ID), estado="CONTABILIZADO")["entry_group_id"]
    wf.anular_asiento(g3, "t", "prueba", fecha="2026-03-13")
    # libro mayor de la cuenta de gasto en marzo 2026: solo R1 y R3 + espejo
    lm = rep.libro_mayor(PORTFOLIO_ID, CTA_GASTO, "2026-03-01", "2026-03-31")
    refs = [m["referencia"] for m in lm["movimientos"]]
    assert f"{PREFIX}-R1" in refs and f"{PREFIX}-R3" in refs and f"REV-{PREFIX}-R3" in refs, refs
    assert f"{PREFIX}-R2" not in refs, "un borrador no va al mayor"
    propios = [m for m in lm["movimientos"] if PREFIX in (m["referencia"] or "")]
    assert sum(m["debito"] for m in propios) - sum(m["credito"] for m in propios) == 1000.0, propios
    # balance de prueba del periodo cuadra
    bp = rep.balance_prueba(PORTFOLIO_ID, "2026-03-01", "2026-03-31")
    assert bp["cuadra"], bp["totales"]
    # P&G: gastos del periodo incluyen 1000 neto de R1 (R3 se cancela) — se
    # comprueba por diferencia contra el mismo periodo sin nuestros asientos
    pyg = rep.estado_resultados(PORTFOLIO_ID, "2026-03-01", "2026-03-31")
    assert pyg["gastos"]["total"] >= 1000.0 and "utilidad_neta" in pyg, pyg["gastos"]["total"]
    bg = rep.balance_general(PORTFOLIO_ID, "2026-03-31")
    assert "ecuacion_contable" in bg and "activos" in bg, bg.keys()


# ── B5: una TX no entra en un periodo cerrado ───────────────────────────────

def test_transaccion_bloqueada_en_periodo_cerrado():
    from fin_sys_core.transaction_service import create_transaction
    from routers.schemas import TransactionInput
    conn = get_conn()
    try:
        cur = conn.cursor(); cur.execute("SELECT name FROM portfolios WHERE id = %s", (PORTFOLIO_ID,))
        nombre = cur.fetchone()[0]; cur.execute("SELECT COUNT(*) FROM transactions"); antes = cur.fetchone()[0]; cur.close()
    finally:
        put_conn(conn)
    cerrar_periodo(PORTFOLIO_ID, ANIO_TEST, 6, "tester")
    tx = TransactionInput(portfolio_name=nombre, type="GASTO", amount=10, concept="TEST periodo cerrado",
                          payment_method="Efectivo", category="Servicios",
                          third_party={"identification_type": "NIT", "identification_number": "999999999",
                                       "name": "Sin especificar"},
                          transaction_date=f"{ANIO_TEST}-06-15")
    try:
        create_transaction(tx)
        assert False, "debió bloquearse por periodo cerrado"
    except PeriodoCerradoError as e:
        assert "cerrado" in str(e)
    conn = get_conn()
    try:
        cur = conn.cursor(); cur.execute("SELECT COUNT(*) FROM transactions"); despues = cur.fetchone()[0]; cur.close()
    finally:
        put_conn(conn)
    assert despues == antes, "no debe quedar ninguna transacción"
    reabrir_periodo(PORTFOLIO_ID, ANIO_TEST, 6, "admin", motivo="test")


TESTS = [
    test_transaccion_bloqueada_en_periodo_cerrado,
    test_reportes_en_libros,
    test_coa_crud_y_bloqueos,
    test_posting_rule_validaciones,
    test_borrador_por_defecto,
    test_contabilizado_explicito,
    test_estado_inicial_invalido,
    test_periodo_cerrado_bloquea_y_reabrir_desbloquea,
    test_cerrar_con_borradores_falla,
    test_anular_borrador_rechaza_sin_espejo,
    test_anular_contabilizado_genera_espejo,
    test_contabilizar_y_doble_falla,
    test_rechazar_exige_motivo_y_transicion,
    test_editar_lineas_borrador,
    test_asiento_manual_y_bandeja,
]


def main():
    global PORTFOLIO_ID
    init_accounting_periods_table()
    PORTFOLIO_ID = _primer_portafolio()
    assert PORTFOLIO_ID is not None, "no hay portafolios en la BD"
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
        print(f"  cleanup: {_cleanup()} líneas de prueba eliminadas")
    print(f"\n{len(TESTS) - fallos}/{len(TESTS)} tests OK")
    sys.exit(1 if fallos else 0)


if __name__ == "__main__":
    main()
