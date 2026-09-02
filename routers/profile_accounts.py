# -*- coding: utf-8 -*-
"""FIN-SYS OS v2.0 — Router: Perfil & Cuentas (4 endpoints)
Extracted from contabilidad.py — PURE refactor, zero logic changes."""
from typing import Optional

from fastapi import APIRouter, HTTPException

from routers.schemas import ProfileInput, AccountInput, AccountUpdateInput

router = APIRouter(tags=["Perfil & Cuentas"])


def anotar_portafolio_cuentas(accounts):
    """Anota los vínculos cuenta ↔ EMPRESA (entities del árbol Control Tower).

    Modelo (scripts/migrate_account_entity_links.py): la cuenta pertenece a
    EMPRESAS/proyectos, no a portafolios — los portafolios son presupuestos
    dentro de las empresas. Sin vínculos = compartida GLOBAL.

      entity_links → [{id, name, type}] de las empresas vinculadas
    """
    try:
        from db_pool import get_conn, put_conn
        conn = get_conn()
        try:
            cur = conn.cursor()
            cur.execute("""
                SELECT l.account_id, e.id, e.name, e.type
                FROM account_entity_links l JOIN entities e ON e.id = l.entity_id
                ORDER BY e.name
            """)
            mapa = {}
            for acc_id, eid, ename, etype in cur.fetchall():
                mapa.setdefault(acc_id, []).append({"id": eid, "name": ename, "type": etype})
            cur.close()
        finally:
            put_conn(conn)
        for a in accounts:
            a["entity_links"] = mapa.get(a.get("id"), [])
    except Exception:
        # Sin la tabla (instalación sin migrar) todas quedan compartidas
        for a in accounts:
            a.setdefault("entity_links", [])
    return accounts


def filtrar_cuentas_por_portafolio(accounts, portfolio):
    """Visibles en un portafolio: las de EMPRESAS cuyo presupuesto es ese
    portafolio + las compartidas (sin vínculos). La visibilidad contable se
    DERIVA del árbol: cuenta → empresa → presupuesto (entities.portfolio_id).

    Regla anti-hueco (2026-09-02): una cuenta vinculada SOLO a empresas sin
    presupuesto quedaba invisible en TODAS las vistas — la cuenta y el vínculo
    sí estaban en BD (user_accounts + account_entity_links) pero ningún filtro
    la incluía y parecía "no guardada". Esas cuentas se muestran en todas las
    vistas (como las compartidas, con su chip de empresa); al asignarle
    presupuesto a la empresa recuperan el aislamiento normal."""
    if not portfolio:
        return accounts
    try:
        from db_pool import get_conn, put_conn
        conn = get_conn()
        try:
            cur = conn.cursor()
            cur.execute("""
                SELECT e.id FROM entities e
                JOIN portfolios p ON p.id = e.portfolio_id
                WHERE p.name = %s
            """, (portfolio,))
            entity_ids = {r[0] for r in cur.fetchall()}
            cur.execute("SELECT id FROM entities WHERE portfolio_id IS NOT NULL")
            con_presupuesto = {r[0] for r in cur.fetchall()}
            cur.close()
        finally:
            put_conn(conn)
    except Exception:
        entity_ids = set()
        con_presupuesto = None   # sin BD no hay cómo derivar: no ocultar de más
    return [a for a in accounts
            if not a.get("entity_links")
            or any(l["id"] in entity_ids for l in a["entity_links"])
            or (con_presupuesto is not None
                and all(l["id"] not in con_presupuesto for l in a["entity_links"]))]


def _link_cuenta(account_id, entity_id):
    from db_pool import get_conn, put_conn
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO account_entity_links (account_id, entity_id)
            VALUES (%s, %s) ON CONFLICT DO NOTHING
        """, (account_id, int(entity_id)))
        conn.commit()
        cur.close()
    finally:
        put_conn(conn)


def _unlink_cuenta(account_id, entity_id):
    from db_pool import get_conn, put_conn
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute("""
            DELETE FROM account_entity_links
            WHERE account_id = %s AND entity_id = %s
        """, (account_id, int(entity_id)))
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
        # La cuenta nace vinculada a la(s) EMPRESA(s) cuyo presupuesto es el
        # portafolio activo (el form manda el portafolio; la dueña real es la
        # empresa del árbol). Sin empresa resoluble → compartida.
        if acc.portfolio:
            try:
                from db_pool import get_conn, put_conn
                conn = get_conn()
                try:
                    cur = conn.cursor()
                    cur.execute("""
                        SELECT e.id FROM entities e
                        JOIN portfolios p ON p.id = e.portfolio_id
                        WHERE p.name = %s
                    """, (acc.portfolio,))
                    entity_ids = [r[0] for r in cur.fetchall()]
                    cur.close()
                finally:
                    put_conn(conn)
                for eid in entity_ids:
                    _link_cuenta(new_id, eid)
            except Exception as e:
                print(f"⚠️ Cuenta {new_id} creada pero sin empresa vinculada: {e}")
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
        return {"status": "ACTUALIZADO"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/accounts/{account_id}/links")
def link_account(account_id: int, body: dict):
    """Vincula la cuenta a una EMPRESA del árbol (N:M). body: {entity_id}."""
    entity_id = (body or {}).get("entity_id")
    if not entity_id:
        raise HTTPException(status_code=422, detail="entity_id requerido")
    try:
        _link_cuenta(account_id, entity_id)
        return {"status": "VINCULADA", "entity_id": int(entity_id)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/api/accounts/{account_id}/links")
def unlink_account(account_id: int, entity_id: int):
    """Quita un vínculo. Sin vínculos restantes la cuenta vuelve a ser compartida."""
    try:
        _unlink_cuenta(account_id, entity_id)
        return {"status": "DESVINCULADA", "entity_id": entity_id}
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
