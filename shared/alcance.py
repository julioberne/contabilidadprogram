# -*- coding: utf-8 -*-
"""alcance.py — Cada usuario ve solo sus empresas (estándar de consultas, H9.1).

El dueño (rol owner) y el superusuario ven todo: para ellos no se consulta nada
y nada cambia. Admin, contador y miembro ven SOLO las empresas que tengan en
`usuario_empresas` (scripts/migrate_h9_alcance.py), y para ellos rige NEGADO POR
DEFECTO: una ruta que no esté en RUTAS responde 403. Así una ruta nueva nunca
deja ver empresas ajenas por olvido; abrirla a ellos es clasificarla aquí (y
tests/test_alcance_h9.py revisa que la clase cuadre con sus parámetros).

Clases:
    GLOBAL    no expone datos de una empresa: catálogos compartidos (terceros,
              etiquetas, impuestos) o lo propio del usuario.
    EMPRESA   la empresa llega en la query o el body (nombre o id) y es
              obligatoria: para ellos «todas» no existe.
    (REGISTRO, param)  la empresa sale del registro que nombra la ruta.

En toda ruta abierta, cualquier empresa que llegue (query o body) debe ser suya.
Se instala como dependencia de la app (server.py): corre antes que la ruta, con
la query y el body ya leídos. Falla CERRADO para ellos; para el dueño, jamás
bloquea.
"""
import threading
import time
import uuid
from typing import Dict, FrozenSet, Iterable, Optional, Set

from fastapi import HTTPException, Request
from starlette.concurrency import run_in_threadpool

from routers.auth_guard import decode_session_token

CACHE_S = 60.0        # quitar una empresa surte efecto en ≤ 1 min (el token dura 7 días)

# Nombres con que las rutas reciben la empresa, en la query o en el body.
PARAMS_EMPRESA = ("portfolio", "portfolio_id", "portfolio_name", "empresa", "empresas",
                  "from_portfolio_id", "to_portfolio_id")

GLOBAL, EMPRESA, REGISTRO = "global", "empresa", "registro"

# La empresa de un registro: (SQL que devuelve su portfolio_id, ¿sin empresa pasa?).
# Un borrador del bot aún sin empresa es del usuario (las rutas del bot ya filtran
# por dueño del chat); un asiento o archivo sin empresa es terreno del dueño.
RESOLVERES = {
    "tx_id": ("SELECT portfolio_id FROM transactions WHERE id = %s", False),
    "entry_group_id": ("SELECT portfolio_id FROM kernel_journal_entries WHERE entry_group_id = %s LIMIT 1", False),
    "file_id": ("SELECT portfolio_id FROM accounting_files WHERE id = %s", False),
    "cuenta_id": ("SELECT portfolio_id FROM chart_of_accounts WHERE id = %s", False),
    "rule_id": ("SELECT portfolio_id FROM posting_rules WHERE id = %s", False),
    "draft_id": ("SELECT CASE WHEN d.portfolio_name IS NULL THEN -1 ELSE p.id END "
                 "FROM transaction_drafts d LEFT JOIN portfolios p ON p.name = d.portfolio_name "
                 "WHERE d.id = %s", True),
}


def _rutas(clase, *claves):
    return {(m, r): clase for m, r in (c.split(" ", 1) for c in claves)}


def _registro(param, *claves):
    return {(m, r): (REGISTRO, param) for m, r in (c.split(" ", 1) for c in claves)}


RUTAS = {
    **_rutas(GLOBAL,
             "GET /api/portfolios",                     # la ruta filtra la lista
             "GET /api/profile",
             "PUT /api/hub/users/me/password",
             "GET /api/third-parties",
             "GET /api/third-parties/{tp_id}/accounts",
             "GET /api/tags",
             "GET /api/custom-taxes",
             "GET /api/buscar/terceros",
             "GET /api/buscar/etiquetas",
             "GET /api/operaciones/{op_id}",            # la ruta ya filtra por usuario
             "GET /api/module-flags",
             "GET /api/analytics/catalog",
             "GET /api/bot/links",
             "POST /api/bot/link-code",
             "GET /api/bot/drafts",                     # la ruta ya filtra por usuario
             "GET /api/alcance/yo",
             "GET /api/health",
             "GET /api/health/vida",
             "GET /api/health/profundo",
             "GET /health",
             "GET /{full_path:path}"),                  # archivos de la web
    **_rutas(EMPRESA,
             "GET /api/portfolios/balance",
             "GET /api/transactions",
             "POST /api/transactions",
             "POST /api/transactions/voice",
             "POST /api/transactions/structure",
             "GET /api/accounts",
             "GET /api/coa",
             "POST /api/coa/template",
             "POST /api/coa/account",
             "GET /api/dashboard-data",
             "GET /api/dashboard-data/balance",
             "GET /api/dashboard-data/version",
             "GET /api/diario/movimientos",
             "GET /api/diario/seleccion",
             "GET /api/diario/opciones",
             "POST /api/diario/csv",
             "GET /api/cartera",
             "GET /api/journal-entries",
             "GET /api/financial-summary",
             "GET /api/contadores/bandeja",
             "GET /api/contadores/resumen",
             "POST /api/contadores/asientos",
             "GET /api/contadores/coa",
             "POST /api/contadores/coa",
             "POST /api/contadores/coa/copiar",
             "GET /api/contadores/posting-rules",
             "POST /api/contadores/posting-rules",
             "GET /api/contadores/reportes/libro-mayor",
             "GET /api/contadores/reportes/balance-prueba",
             "GET /api/contadores/reportes/balance-general",
             "GET /api/contadores/reportes/pyg",
             "GET /api/contadores/periodos",
             "POST /api/contadores/periodos/cerrar",
             "POST /api/contadores/periodos/reabrir",
             "POST /api/analytics/metric",
             "POST /api/analytics/ask",
             "GET /api/analytics/insights",
             "GET /api/analytics/dataset",
             "GET /api/accounting-files",
             "GET /api/accounting-files/cierres",
             "POST /api/accounting-files/upload"),
    **_registro("tx_id",
                "PUT /api/transactions/{tx_id}",
                "DELETE /api/transactions/{tx_id}",
                "POST /api/transactions/{tx_id}/evidences"),
    **_registro("entry_group_id",
                "GET /api/contadores/asientos/{entry_group_id}",
                "PUT /api/contadores/asientos/{entry_group_id}/lineas",
                "POST /api/contadores/asientos/{entry_group_id}/contabilizar",
                "POST /api/contadores/asientos/{entry_group_id}/rechazar",
                "POST /api/contadores/asientos/{entry_group_id}/anular"),
    **_registro("cuenta_id",
                "PUT /api/contadores/coa/{cuenta_id}",
                "DELETE /api/contadores/coa/{cuenta_id}"),
    **_registro("rule_id",
                "PUT /api/contadores/posting-rules/{rule_id}",
                "DELETE /api/contadores/posting-rules/{rule_id}"),
    **_registro("file_id",
                "GET /api/accounting-files/{file_id}",
                "GET /api/accounting-files/{file_id}/download",
                "GET /api/accounting-files/{file_id}/preview",
                "PATCH /api/accounting-files/{file_id}",
                "POST /api/accounting-files/{file_id}/regenerar",
                "DELETE /api/accounting-files/{file_id}"),
    **_registro("draft_id",
                "GET /api/bot/drafts/{draft_id}",
                "PUT /api/bot/drafts/{draft_id}",
                "POST /api/bot/drafts/{draft_id}/confirm",
                "POST /api/bot/drafts/{draft_id}/discard"),
}

SOLO_DUENO = "Esta función es solo para el dueño de la cuenta."
AJENA = "No tienes acceso a esa empresa."
ELIGE = "Elige una empresa: tu usuario no ve el consolidado de todas."


# ── Quién ve qué ─────────────────────────────────────────────────────────────

def es_dueno(user: Optional[dict]) -> bool:
    return bool(user) and (bool(user.get("su")) or user.get("role") == "owner")


_lock = threading.Lock()
_cache_usuarios: Dict[str, tuple] = {}          # uid → (vence, frozenset de ids)
_cache_portafolios: list = [0.0, {}]            # [vence, {id: nombre}]


def _consultar(sql: str, params: tuple = ()) -> list:
    from fin_sys_core.db_pool import get_conn, put_conn
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute(sql, params)
        return cur.fetchall()
    finally:
        conn.rollback()
        put_conn(conn)


def _empresas_de_bd(uid: str) -> FrozenSet[int]:
    try:
        uuid.UUID(uid)
    except (ValueError, TypeError):
        return frozenset()                       # tokens de servicio sin usuario real
    try:
        filas = _consultar("SELECT portfolio_id FROM usuario_empresas WHERE hub_user_id = %s", (uid,))
    except Exception as e:                       # sin la migración: no ve ninguna (cerrado)
        print(f"[alcance] sin usuario_empresas ({type(e).__name__}): {uid[:8]} no ve empresas")
        return frozenset()
    return frozenset(int(f[0]) for f in filas)


def empresas_permitidas(user: Optional[dict]) -> Optional[FrozenSet[int]]:
    """None = todas (dueño); si no, los ids de sus empresas (puede ser vacío)."""
    if es_dueno(user):
        return None
    uid = str((user or {}).get("uid") or "")
    ahora = time.monotonic()
    with _lock:
        guardado = _cache_usuarios.get(uid)
        if guardado and guardado[0] > ahora:
            return guardado[1]
    ids = _empresas_de_bd(uid)
    with _lock:
        _cache_usuarios[uid] = (ahora + CACHE_S, ids)
    return ids


def portafolios() -> Dict[int, str]:
    """{id: nombre} de todos los portafolios (para comparar por nombre o por id)."""
    ahora = time.monotonic()
    with _lock:
        if _cache_portafolios[0] > ahora:
            return _cache_portafolios[1]
    nombres = {int(i): n for i, n in _consultar("SELECT id, name FROM portfolios")}
    with _lock:
        _cache_portafolios[:] = [ahora + CACHE_S, nombres]
    return nombres


def limpiar_cache(uid: Optional[str] = None) -> None:
    with _lock:
        if uid is None:
            _cache_usuarios.clear()
            _cache_portafolios[:] = [0.0, {}]
        else:
            _cache_usuarios.pop(str(uid), None)


def _id_de(valor, nombres: Dict[int, str]) -> Optional[int]:
    texto = str(valor).strip()
    if texto.lstrip("-").isdigit():
        return int(texto)
    for pid, nombre in nombres.items():
        if nombre == texto:
            return pid
    plegado = texto.casefold()
    for pid, nombre in nombres.items():
        if (nombre or "").casefold() == plegado:
            return pid
    return None


def es_suya(valor, permitidas: FrozenSet[int], nombres: Dict[int, str]) -> bool:
    pid = _id_de(valor, nombres)
    return pid is not None and pid in permitidas


# ── La dependencia de la app ─────────────────────────────────────────────────

def _usuario(request: Request) -> Optional[dict]:
    auth = request.headers.get("authorization") or ""
    if not auth.lower().startswith("bearer "):
        return None
    return decode_session_token(auth[7:].strip())


def _partir(nombre: str, valor) -> Iterable[str]:
    if valor is None or isinstance(valor, (dict, list)) and not valor:
        return []
    if isinstance(valor, list):
        return [str(v) for v in valor]
    texto = str(valor).strip()
    if nombre == "empresas":
        return [v.strip() for v in texto.split(",") if v.strip()]
    return [texto] if texto else []


async def _valores_empresa(request: Request) -> list:
    valores = []
    for nombre in PARAMS_EMPRESA:
        for v in request.query_params.getlist(nombre):
            valores += _partir(nombre, v)
    if request.method in ("POST", "PUT", "PATCH"):
        tipo = (request.headers.get("content-type") or "").lower()
        cuerpo = None
        try:
            if "application/json" in tipo:
                cuerpo = await request.json()
            elif "multipart/form-data" in tipo or "application/x-www-form-urlencoded" in tipo:
                cuerpo = await request.form()
        except Exception:
            cuerpo = None                        # cuerpo inválido: la ruta responde 422
        if cuerpo is not None and hasattr(cuerpo, "get"):
            for nombre in PARAMS_EMPRESA:
                valores += _partir(nombre, cuerpo.get(nombre))
    return valores


def _empresa_del_registro(param: str, valor) -> tuple:
    """(encontrado, portfolio_id o None, sin_empresa_pasa)."""
    sql, vacio_pasa = RESOLVERES[param]
    filas = _consultar(sql, (valor,))
    if not filas:
        return False, None, vacio_pasa
    pid = filas[0][0]
    return True, (None if pid is None else int(pid)), vacio_pasa


async def verificar(request: Request) -> None:
    """Dependencia global (server.py). Sin token válido no hace nada: la ruta
    responde 401 con su propio require_auth."""
    user = _usuario(request)
    if user is None or es_dueno(user):
        return
    ruta = request.scope.get("route")
    metodo = "GET" if request.method == "HEAD" else request.method
    clase = RUTAS.get((metodo, getattr(ruta, "path", "")))
    if clase is None:
        raise HTTPException(status_code=403, detail=SOLO_DUENO)

    valores = await _valores_empresa(request)
    if clase == GLOBAL and not valores:
        return                                   # sin empresa en juego: ni una consulta
    try:
        permitidas = await run_in_threadpool(empresas_permitidas, user)
        nombres = await run_in_threadpool(portafolios) if valores else {}
    except HTTPException:
        raise
    except Exception as e:
        print(f"[alcance] no se pudo verificar {metodo} {getattr(ruta, 'path', '')}: {type(e).__name__}: {e}")
        raise HTTPException(status_code=503, detail="No se pudo verificar tu acceso. Intenta de nuevo.",
                            headers={"Retry-After": "2"})

    for v in valores:
        if not es_suya(v, permitidas, nombres):
            raise HTTPException(status_code=403, detail=AJENA)
    if clase == EMPRESA and not valores:
        raise HTTPException(status_code=403, detail=ELIGE)
    if isinstance(clase, tuple) and clase[0] == REGISTRO:
        param = clase[1]
        try:
            encontrado, pid, vacio_pasa = await run_in_threadpool(
                _empresa_del_registro, param, request.path_params.get(param))
        except Exception as e:
            print(f"[alcance] no se pudo resolver {param}: {type(e).__name__}: {e}")
            raise HTTPException(status_code=503, detail="No se pudo verificar tu acceso. Intenta de nuevo.",
                                headers={"Retry-After": "2"})
        if not encontrado:
            return                               # no existe: la ruta responde 404
        if pid == -1 and vacio_pasa:             # borrador sin empresa todavía
            return
        if pid is None or pid not in permitidas:
            raise HTTPException(status_code=403, detail=AJENA)


def solo_dueno(user: Optional[dict]) -> None:
    if not es_dueno(user):
        raise HTTPException(status_code=403, detail=SOLO_DUENO)


def filtrar_portafolios(user: Optional[dict], lista: list) -> list:
    """Para GET /api/portfolios: el dueño ve todas; los demás, solo las suyas."""
    permitidas = empresas_permitidas(user)
    if permitidas is None:
        return lista
    return [p for p in lista if _id_seguro(p.get("id")) in permitidas]


def _id_seguro(v) -> Optional[int]:
    try:
        return int(v)
    except (TypeError, ValueError):
        return None


def ids_validos(ids: Iterable) -> Set[int]:
    """Los ids que existen como portafolio (para asignar sin basura)."""
    existentes = set(portafolios())
    return {i for i in (_id_seguro(x) for x in ids) if i in existentes}
