# -*- coding: utf-8 -*-
"""FIN-SYS OS v2.0 — Router: Contadores (módulo 12, B2).

Bandeja de asientos (borrador → contabilizar / rechazar / anular), asientos
manuales y periodos contables. Todo exige rol contador/owner/admin
(require_contador); reabrir un periodo, admin.
"""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException

from routers.auth_guard import require_admin, require_contador
from routers.contadores_schemas import (
    LineasEditInput, MotivoInput, AnularInput, LoteInput, AsientoManualInput, PeriodoInput,
    CuentaInput, CuentaUpdateInput, CopiarCoaInput, ReglaInput, ReglaUpdateInput,
)

router = APIRouter(prefix="/api/contadores", tags=["Contadores"])


def _quien(user: dict) -> str:
    return (user.get("name") or user.get("uid") or "contador")[:64]


def _http(e: Exception) -> HTTPException:
    """Un solo mapeo de errores del kernel a HTTP."""
    from kernel.kernel_accounting import PartidaDobleError, CuentaNoExisteError
    from kernel.kernel_periods import PeriodoCerradoError
    from kernel.kernel_journal_workflow import EstadoAsientoError
    from fin_sys_core.coa_admin_driver import CoaError
    if isinstance(e, HTTPException):
        return e
    if isinstance(e, CoaError):
        return HTTPException(status_code=e.status, detail=str(e))
    if isinstance(e, (PartidaDobleError, CuentaNoExisteError, ValueError)):
        return HTTPException(status_code=400, detail=str(e))
    if isinstance(e, PeriodoCerradoError):
        return HTTPException(status_code=409, detail=str(e))
    if isinstance(e, EstadoAsientoError):
        return HTTPException(status_code=e.status, detail=str(e))
    return HTTPException(status_code=500, detail=str(e))


# ── Bandeja / asientos ───────────────────────────────────────────────────────

@router.get("/bandeja")
def bandeja(estado: Optional[str] = "BORRADOR", portfolio_id: Optional[int] = None,
            desde: Optional[str] = None, hasta: Optional[str] = None,
            modulo: Optional[str] = None, q: Optional[str] = None,
            sin_portafolio: bool = False, tx_id: Optional[int] = None,
            limit: int = 50, offset: int = 0, _u: dict = Depends(require_contador)):
    try:
        from kernel.kernel_journal_workflow import obtener_asientos_agrupados
        return obtener_asientos_agrupados(
            estado=estado, portfolio_id=portfolio_id, fecha_desde=desde, fecha_hasta=hasta,
            modulo_origen=modulo, q=q, sin_portafolio=sin_portafolio, tx_id=tx_id,
            limit=min(int(limit), 500), offset=int(offset))
    except Exception as e:
        raise _http(e)


@router.get("/resumen")
def resumen(portfolio_id: Optional[int] = None, _u: dict = Depends(require_contador)):
    """Conteo de asientos por estado (para las pestañas)."""
    try:
        from fin_sys_core.db_pool import get_conn, put_conn
        conn = get_conn()
        try:
            cur = conn.cursor()
            if portfolio_id is None:
                cur.execute("""SELECT estado, COUNT(DISTINCT entry_group_id)
                               FROM kernel_journal_entries GROUP BY estado""")
            else:
                cur.execute("""SELECT estado, COUNT(DISTINCT entry_group_id)
                               FROM kernel_journal_entries WHERE portfolio_id = %s GROUP BY estado""",
                            (int(portfolio_id),))
            conteo = {r[0]: int(r[1]) for r in cur.fetchall()}
            cur.execute("SELECT COUNT(DISTINCT entry_group_id) FROM kernel_journal_entries WHERE portfolio_id IS NULL")
            sin_pf = int(cur.fetchone()[0])
            cur.close()
        finally:
            put_conn(conn)
        return {"por_estado": conteo, "sin_portafolio": sin_pf}
    except Exception as e:
        raise _http(e)


@router.get("/asientos/{entry_group_id}")
def asiento(entry_group_id: str, _u: dict = Depends(require_contador)):
    try:
        from kernel.kernel_journal_workflow import obtener_asiento
        item = obtener_asiento(entry_group_id)
        if not item:
            raise HTTPException(status_code=404, detail="Asiento no encontrado")
        return item
    except Exception as e:
        raise _http(e)


@router.put("/asientos/{entry_group_id}/lineas")
def editar_lineas(entry_group_id: str, body: LineasEditInput, user: dict = Depends(require_contador)):
    try:
        from kernel.kernel_journal_workflow import editar_lineas_borrador, obtener_asiento
        editar_lineas_borrador(entry_group_id, [l.model_dump() for l in body.lineas], _quien(user),
                               fecha=body.fecha, descripcion=body.descripcion,
                               portfolio_id=body.portfolio_id)
        return obtener_asiento(entry_group_id)
    except Exception as e:
        raise _http(e)


@router.post("/asientos/{entry_group_id}/contabilizar")
def contabilizar(entry_group_id: str, user: dict = Depends(require_contador)):
    try:
        from kernel.kernel_journal_workflow import contabilizar_asiento, obtener_asiento
        contabilizar_asiento(entry_group_id, _quien(user))
        return obtener_asiento(entry_group_id)
    except Exception as e:
        raise _http(e)


@router.post("/asientos/{entry_group_id}/rechazar")
def rechazar(entry_group_id: str, body: MotivoInput, user: dict = Depends(require_contador)):
    try:
        from kernel.kernel_journal_workflow import rechazar_asiento, obtener_asiento
        rechazar_asiento(entry_group_id, _quien(user), body.motivo)
        return obtener_asiento(entry_group_id)
    except Exception as e:
        raise _http(e)


@router.post("/asientos/{entry_group_id}/anular")
def anular(entry_group_id: str, body: AnularInput, user: dict = Depends(require_contador)):
    try:
        from kernel.kernel_journal_workflow import anular_asiento, obtener_asiento
        res = anular_asiento(entry_group_id, _quien(user), body.motivo, fecha=body.fecha)
        return {"resultado": res, "asiento": obtener_asiento(entry_group_id),
                "espejo": obtener_asiento(res["entry_group_id"]) if res.get("entry_group_id") else None}
    except Exception as e:
        raise _http(e)


@router.post("/asientos/lote")
def lote(body: LoteInput, user: dict = Depends(require_contador)):
    """Contabilizar/rechazar varios: secuencial, resultado por id (patrón bot)."""
    from kernel.kernel_journal_workflow import contabilizar_asiento, rechazar_asiento
    salida = {}
    for gid in body.ids:
        try:
            if body.accion == "contabilizar":
                contabilizar_asiento(gid, _quien(user))
            else:
                rechazar_asiento(gid, _quien(user), body.motivo or "Rechazo masivo")
            salida[gid] = "ok"
        except Exception as e:
            salida[gid] = f"error: {e}"
    return {"resultados": salida, "ok": sum(1 for v in salida.values() if v == "ok"),
            "total": len(salida)}


@router.post("/asientos", status_code=201)
def crear_manual(body: AsientoManualInput, user: dict = Depends(require_contador)):
    try:
        from kernel.kernel_journal_workflow import crear_asiento_manual, obtener_asiento
        res = crear_asiento_manual(body.portfolio_id, body.fecha, body.descripcion or "",
                                   [l.model_dump() for l in body.lineas], _quien(user),
                                   contabilizar=body.contabilizar)
        return {"resultado": res, "asiento": obtener_asiento(res["entry_group_id"])}
    except Exception as e:
        raise _http(e)


# ── Plan de cuentas (B3) ─────────────────────────────────────────────────────

@router.get("/coa")
def coa_listar(portfolio_id: int, _u: dict = Depends(require_contador)):
    try:
        from fin_sys_core.coa_admin_driver import listar_coa
        return listar_coa(portfolio_id)
    except Exception as e:
        raise _http(e)


@router.post("/coa", status_code=201)
def coa_crear(body: CuentaInput, _u: dict = Depends(require_contador)):
    try:
        from fin_sys_core.coa_admin_driver import crear_cuenta
        return crear_cuenta(body.portfolio_id, body.code, body.name, body.account_type,
                            is_group=body.is_group, parent_code=body.parent_code,
                            description=body.description)
    except Exception as e:
        raise _http(e)


@router.put("/coa/{cuenta_id}")
def coa_actualizar(cuenta_id: int, body: CuentaUpdateInput, _u: dict = Depends(require_contador)):
    try:
        from fin_sys_core.coa_admin_driver import actualizar_cuenta
        return actualizar_cuenta(cuenta_id, **body.model_dump())
    except Exception as e:
        raise _http(e)


@router.delete("/coa/{cuenta_id}")
def coa_eliminar(cuenta_id: int, _u: dict = Depends(require_contador)):
    try:
        from fin_sys_core.coa_admin_driver import eliminar_cuenta
        return eliminar_cuenta(cuenta_id)
    except Exception as e:
        raise _http(e)


@router.post("/coa/copiar")
def coa_copiar(body: CopiarCoaInput, _u: dict = Depends(require_admin)):
    try:
        from fin_sys_core.coa_admin_driver import copiar_coa
        return copiar_coa(body.from_portfolio_id, body.to_portfolio_id)
    except Exception as e:
        raise _http(e)


# ── Posting rules (B3) ───────────────────────────────────────────────────────

@router.get("/posting-rules")
def reglas_listar(portfolio_id: Optional[int] = None, _u: dict = Depends(require_contador)):
    try:
        from fin_sys_core.coa_admin_driver import listar_reglas
        return listar_reglas(portfolio_id)
    except Exception as e:
        raise _http(e)


@router.post("/posting-rules", status_code=201)
def reglas_crear(body: ReglaInput, _u: dict = Depends(require_contador)):
    try:
        from fin_sys_core.coa_admin_driver import crear_regla
        return crear_regla(**body.model_dump())
    except Exception as e:
        raise _http(e)


@router.put("/posting-rules/{rule_id}")
def reglas_actualizar(rule_id: int, body: ReglaUpdateInput, _u: dict = Depends(require_contador)):
    try:
        from fin_sys_core.coa_admin_driver import actualizar_regla
        return actualizar_regla(rule_id, **body.model_dump())
    except Exception as e:
        raise _http(e)


@router.delete("/posting-rules/{rule_id}")
def reglas_eliminar(rule_id: int, _u: dict = Depends(require_contador)):
    try:
        from fin_sys_core.coa_admin_driver import eliminar_regla
        return eliminar_regla(rule_id)
    except Exception as e:
        raise _http(e)


# ── Periodos ─────────────────────────────────────────────────────────────────

@router.get("/periodos")
def periodos(portfolio_id: int, anio: int, _u: dict = Depends(require_contador)):
    try:
        from kernel.kernel_periods import listar_periodos
        return listar_periodos(portfolio_id, anio)
    except Exception as e:
        raise _http(e)


@router.post("/periodos/cerrar")
def cerrar(body: PeriodoInput, user: dict = Depends(require_contador)):
    try:
        from kernel.kernel_periods import cerrar_periodo
        return cerrar_periodo(body.portfolio_id, body.anio, body.mes, _quien(user), nota=body.nota)
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except Exception as e:
        raise _http(e)


@router.post("/periodos/reabrir")
def reabrir(body: PeriodoInput, user: dict = Depends(require_admin)):
    try:
        from kernel.kernel_periods import reabrir_periodo
        return reabrir_periodo(body.portfolio_id, body.anio, body.mes, _quien(user), motivo=body.motivo)
    except Exception as e:
        raise _http(e)
