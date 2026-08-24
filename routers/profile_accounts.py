# -*- coding: utf-8 -*-
"""FIN-SYS OS v2.0 — Router: Perfil & Cuentas (4 endpoints)
Extracted from contabilidad.py — PURE refactor, zero logic changes."""
from typing import Optional

from fastapi import APIRouter, HTTPException

from routers.schemas import ProfileInput, AccountInput, AccountUpdateInput

router = APIRouter(tags=["Perfil & Cuentas"])


def anotar_portafolio_cuentas(accounts):
    """Anota portfolio_id / portfolio_name en cada cuenta (dict).

    Se hace aquí (y no en obtener_cuentas) para no tocar database_driver:
    la columna user_accounts.portfolio_id la agregó
    scripts/migrate_accounts_portfolio.py. NULL = compartida.
    """
    try:
        from db_pool import get_conn, put_conn
        conn = get_conn()
        try:
            cur = conn.cursor()
            cur.execute("""
                SELECT a.id, a.portfolio_id, p.name
                FROM user_accounts a LEFT JOIN portfolios p ON p.id = a.portfolio_id
            """)
            mapa = {r[0]: (r[1], r[2]) for r in cur.fetchall()}
            cur.close()
        finally:
            put_conn(conn)
        for a in accounts:
            pid, pname = mapa.get(a.get("id"), (None, None))
            a["portfolio_id"] = pid
            a["portfolio_name"] = pname
    except Exception:
        # Sin la columna (instalación sin migrar) todas quedan compartidas
        for a in accounts:
            a.setdefault("portfolio_id", None)
            a.setdefault("portfolio_name", None)
    return accounts


def filtrar_cuentas_por_portafolio(accounts, portfolio):
    """Cuentas visibles para un portafolio: las suyas + las compartidas."""
    if not portfolio:
        return accounts
    return [a for a in accounts
            if a.get("portfolio_id") is None or a.get("portfolio_name") == portfolio]


def _set_portfolio_cuenta(account_id, portfolio_name):
    """portfolio_name: '' = compartida (NULL); nombre = asignar."""
    from db_pool import get_conn, put_conn
    conn = get_conn()
    try:
        cur = conn.cursor()
        if not portfolio_name:
            cur.execute("UPDATE user_accounts SET portfolio_id = NULL WHERE id = %s", (account_id,))
        else:
            cur.execute("""
                UPDATE user_accounts
                SET portfolio_id = (SELECT id FROM portfolios WHERE name = %s)
                WHERE id = %s
            """, (portfolio_name, account_id))
        conn.commit()
        cur.close()
    finally:
        put_conn(conn)


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
