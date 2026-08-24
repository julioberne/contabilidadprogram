# -*- coding: utf-8 -*-
"""FIN-SYS OS v2.0 — Router: Perfil & Cuentas (4 endpoints)
Extracted from contabilidad.py — PURE refactor, zero logic changes."""
from typing import Optional

from fastapi import APIRouter, HTTPException

from routers.schemas import ProfileInput, AccountInput, AccountUpdateInput

router = APIRouter(tags=["Perfil & Cuentas"])


def anotar_portafolio_cuentas(accounts):
    """Anota los vínculos N:M cuenta ↔ portafolio en cada cuenta (dict).

    Modelo (scripts/migrate_account_links.py): una cuenta SIN vínculos es
    compartida GLOBAL (visible en todos los portafolios); con vínculos, solo
    es visible en esos. Se hace aquí para no tocar database_driver.

      portfolio_links → lista de nombres de portafolio vinculados
      portfolio_name  → compat: el nombre si hay exactamente 1 vínculo
    """
    try:
        from db_pool import get_conn, put_conn
        conn = get_conn()
        try:
            cur = conn.cursor()
            cur.execute("""
                SELECT l.account_id, p.name
                FROM account_portfolio_links l JOIN portfolios p ON p.id = l.portfolio_id
                ORDER BY p.name
            """)
            mapa = {}
            for acc_id, pname in cur.fetchall():
                mapa.setdefault(acc_id, []).append(pname)
            cur.close()
        finally:
            put_conn(conn)
        for a in accounts:
            links = mapa.get(a.get("id"), [])
            a["portfolio_links"] = links
            a["portfolio_name"] = links[0] if len(links) == 1 else None
            a["portfolio_id"] = None   # legado 1:1, ya no gobierna
    except Exception:
        # Sin la tabla (instalación sin migrar) todas quedan compartidas
        for a in accounts:
            a.setdefault("portfolio_links", [])
            a.setdefault("portfolio_name", None)
            a.setdefault("portfolio_id", None)
    return accounts


def filtrar_cuentas_por_portafolio(accounts, portfolio):
    """Visibles para un portafolio: las vinculadas a él + las compartidas."""
    if not portfolio:
        return accounts
    return [a for a in accounts
            if not a.get("portfolio_links") or portfolio in a["portfolio_links"]]


def _link_cuenta(account_id, portfolio_name):
    from db_pool import get_conn, put_conn
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO account_portfolio_links (account_id, portfolio_id)
            SELECT %s, id FROM portfolios WHERE name = %s
            ON CONFLICT DO NOTHING
            RETURNING account_id
        """, (account_id, portfolio_name))
        creado = cur.fetchone() is not None
        conn.commit()
        cur.close()
        return creado
    finally:
        put_conn(conn)


def _unlink_cuenta(account_id, portfolio_name):
    from db_pool import get_conn, put_conn
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute("""
            DELETE FROM account_portfolio_links
            WHERE account_id = %s
              AND portfolio_id = (SELECT id FROM portfolios WHERE name = %s)
        """, (account_id, portfolio_name))
        conn.commit()
        cur.close()
    finally:
        put_conn(conn)


def _set_portfolio_cuenta(account_id, portfolio_name):
    """Compat del PUT 1:1: '' = compartida (sin vínculos); nombre = SOLO ese."""
    from db_pool import get_conn, put_conn
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute("DELETE FROM account_portfolio_links WHERE account_id = %s", (account_id,))
        conn.commit()
        cur.close()
    finally:
        put_conn(conn)
    if portfolio_name:
        _link_cuenta(account_id, portfolio_name)


# ==============================================================================
# 🔌 Endpoints — Perfil & Cuentas
# ==============================================================================

@router.get("/api/profile")
def get_profile():
    try:
        from database_driver import obtener_perfil_usuario
        return obtener_perfil_usuario()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/api/profile")
def update_profile(profile: ProfileInput):
    try:
        from database_driver import actualizar_perfil_usuario
        success = actualizar_perfil_usuario(profile.dict())
        if not success:
            raise HTTPException(status_code=500, detail="No se pudo actualizar el perfil.")
        return {"status": "ACTUALIZADO"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/accounts")
def list_accounts(portfolio: Optional[str] = None):
    """Sin ?portfolio= devuelve todas; con él, las del portafolio + compartidas.
    Cada cuenta viene con portfolio_name, tx_delta y expected_balance — lo que
    necesitan las tabs del Pulso de Cuentas para mostrar cualquier empresa."""
    try:
        from database_driver import obtener_cuentas, obtener_transacciones
        from routers.dashboard_data import _agregar_tx_delta
        accounts = anotar_portafolio_cuentas(obtener_cuentas())
        _agregar_tx_delta(accounts, obtener_transacciones(None))
        return filtrar_cuentas_por_portafolio(accounts, portfolio)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/accounts", status_code=201)
def add_account(acc: AccountInput):
    try:
        from database_driver import crear_cuenta
        new_id = crear_cuenta(acc.dict())
        # La cuenta nace en el portafolio activo (crear_cuenta no conoce la
        # columna; se asigna aquí). Sin portfolio → compartida.
        if acc.portfolio:
            try:
                _set_portfolio_cuenta(new_id, acc.portfolio)
            except Exception as e:
                print(f"⚠️ Cuenta {new_id} creada pero sin portafolio asignado: {e}")
        return {"status": "CREADO", "account_id": new_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/api/accounts/{account_id}")
def update_account(account_id: int, acc: AccountUpdateInput):
    try:
        from database_driver import actualizar_cuenta
        if not actualizar_cuenta(account_id, acc.dict()):
            raise HTTPException(status_code=404, detail="Cuenta no encontrada.")
        # Saldo inicial: actualizar_cuenta (driver estable) no lo cubre — se
        # maneja aquí. Editarlo NO recalcula current_balance automáticamente:
        # para eso está ⟳ Reconciliar (inicial + transacciones reales).
        if acc.initial_balance is not None:
            from db_pool import get_conn, put_conn
            conn = get_conn()
            try:
                cur = conn.cursor()
                cur.execute("UPDATE user_accounts SET initial_balance = %s WHERE id = %s",
                            (float(acc.initial_balance), account_id))
                conn.commit()
                cur.close()
            finally:
                put_conn(conn)
        # Reasignación de portafolio: None = no tocar, "" = compartida
        if acc.portfolio_name is not None:
            _set_portfolio_cuenta(account_id, acc.portfolio_name.strip())
        return {"status": "ACTUALIZADO"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/accounts/{account_id}/links")
def link_account(account_id: int, body: dict):
    """Vincula la cuenta a un portafolio más (N:M). body: {portfolio_name}."""
    portfolio_name = (body or {}).get("portfolio_name", "").strip()
    if not portfolio_name:
        raise HTTPException(status_code=422, detail="portfolio_name requerido")
    try:
        _link_cuenta(account_id, portfolio_name)
        return {"status": "VINCULADA", "portfolio_name": portfolio_name}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/api/accounts/{account_id}/links")
def unlink_account(account_id: int, portfolio_name: str):
    """Quita un vínculo. Sin vínculos restantes la cuenta vuelve a ser compartida."""
    try:
        _unlink_cuenta(account_id, portfolio_name.strip())
        return {"status": "DESVINCULADA", "portfolio_name": portfolio_name}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/api/accounts/{account_id}")
def delete_account(account_id: int):
    try:
        from database_driver import eliminar_cuenta
        if not eliminar_cuenta(account_id):
            raise HTTPException(status_code=404, detail="Cuenta no encontrada.")
        return {"status": "ELIMINADO"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
