# -*- coding: utf-8 -*-
"""
compendio_driver.py — 🤝 Compendio para el cliente (spec 13.6).
Archivo NUEVO (Zero-Impact). Lo usa routers/compendios.py.

Un compendio es la FOTO (snapshot jsonb) de unas transacciones elegidas,
con folio EXP-AAAA-NNNN (la misma secuencia de 13.5), que el cliente final
ve sin login en /c/<código> mientras el link esté vigente (R-136-01/02).

  prevuelo(datos)          → conteos, totales por moneda y comprobantes, sin crear nada
  crear(datos, usuario)    → snapshot + folio + código; devuelve la ruta /c/<código>
  listar() / actualizar()  → carpeta 🔗 Compendios: ampliar o revocar
  abrir(token)             → lo que ve el cliente (cuenta la visita); NoDisponible si
                             vencido, revocado o inexistente (no se distingue cuál)
  soporte(token, i, j)     → URL del comprobante j de la TX i, leído EN VIVO como el
                             botón [Ver] del Libro Diario (decisión de Andrés 06-oct);
                             el router lo descarga y lo sirve: el cliente nunca ve
                             la URL del bucket público (R-136-03)

El código del link no se guarda: se deriva con la clave del servidor (HMAC)
de un nonce aleatorio y en la BD solo queda su SHA-256. Con la BD sola no se
puede armar un link; con el servidor, sí (📋 Copiar link en cualquier momento).

Las cifras salen de la misma lectura de transacciones que el motor 13.4
(R-136-04); USD jamás se suma al COP (R-136-05).
Errores: ValueError → 400 · NoEncontrado → 404 · Conflicto → 409 ·
NoDisponible → 404 sin detalle · es_tabla_faltante(e) → 503.
"""
import base64
import hashlib
import hmac
import json
import os
import re
import secrets
from datetime import date, datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import unquote, urlparse

from fin_sys_core.accounting_files_driver import (  # noqa: F401  (es_tabla_faltante lo usa el router)
    Conflicto, NoEncontrado, _conexion, _fila, _filas, _iso, _quien, es_tabla_faltante, siguiente_folio,
)

VIGENCIAS = (7, 15, 30, 90)
VIGENCIA_DEFECTO = 15
MAX_TX = 1000                    # una página para el cliente, no un libro (el .xlsx admite 5000)
MAX_NOMBRE = 120
MAX_NOTA = 1000
LIMITE_LISTA = 200

_TOKEN = re.compile(r"^[A-Za-z0-9_-]{40,64}$")
_MAPS = re.compile(r"^(?:[a-z0-9-]+\.)*(?:google\.[a-z.]{2,8}|goo\.gl)$")

TIPO_IMAGEN, TIPO_PDF, TIPO_AUDIO, TIPO_OTRO = "imagen", "pdf", "audio", "otro"
# Solo estos se muestran en la página; cualquier otro (svg incluido) se descarga.
MIME_POR_EXT = {
    "jpg": ("image/jpeg", TIPO_IMAGEN), "jpeg": ("image/jpeg", TIPO_IMAGEN),
    "png": ("image/png", TIPO_IMAGEN), "webp": ("image/webp", TIPO_IMAGEN), "gif": ("image/gif", TIPO_IMAGEN),
    "pdf": ("application/pdf", TIPO_PDF),
    "ogg": ("audio/ogg", TIPO_AUDIO), "oga": ("audio/ogg", TIPO_AUDIO), "opus": ("audio/ogg", TIPO_AUDIO),
    "mp3": ("audio/mpeg", TIPO_AUDIO), "m4a": ("audio/mp4", TIPO_AUDIO), "webm": ("audio/webm", TIPO_AUDIO),
}


class NoDisponible(LookupError):
    """Link vencido, revocado o inexistente: la misma respuesta para los tres."""


# ══ DDL (la corre scripts/migrate_compendios.py; el server NO la ejecuta) ══

DDL = [
    """
    CREATE TABLE IF NOT EXISTS accounting_compendios (
        id SERIAL PRIMARY KEY,
        folio VARCHAR(30) NOT NULL UNIQUE,
        nombre VARCHAR(120) NOT NULL,
        nota TEXT,
        tx_ids INTEGER[] NOT NULL,
        snapshot JSONB NOT NULL,
        opciones JSONB NOT NULL DEFAULT '{}'::jsonb,
        nonce VARCHAR(64) NOT NULL,
        token_hash CHAR(64) NOT NULL UNIQUE,
        expira_en TIMESTAMPTZ NOT NULL,
        revocado_en TIMESTAMPTZ,
        revocado_por VARCHAR(120),
        creado_por VARCHAR(120) NOT NULL,
        creado_en TIMESTAMPTZ NOT NULL DEFAULT now(),
        visitas INTEGER NOT NULL DEFAULT 0,
        ultima_visita TIMESTAMPTZ,
        descargas_pdf INTEGER NOT NULL DEFAULT 0,
        descargas_html INTEGER NOT NULL DEFAULT 0
    )
    """,
    "CREATE INDEX IF NOT EXISTS ix_accounting_compendios_creado ON accounting_compendios (creado_en DESC)",
    # 13.6-c 📈 Seguimiento: qué abrió el cliente y cuándo. Sin IP: el visitante es una huella HMAC.
    """
    CREATE TABLE IF NOT EXISTS accounting_compendio_eventos (
        id BIGSERIAL PRIMARY KEY,
        compendio_id INTEGER NOT NULL REFERENCES accounting_compendios(id) ON DELETE CASCADE,
        tipo VARCHAR(20) NOT NULL CHECK (tipo IN ('abrio', 'tx', 'comprobante', 'pdf', 'html')),
        tx_i INTEGER,
        soporte_j INTEGER,
        visitante CHAR(12) NOT NULL,
        dispositivo VARCHAR(60),
        en TIMESTAMPTZ NOT NULL DEFAULT now()
    )
    """,
    "CREATE INDEX IF NOT EXISTS ix_compendio_eventos_compendio ON accounting_compendio_eventos (compendio_id, en DESC)",
    "CREATE INDEX IF NOT EXISTS ix_compendio_eventos_en ON accounting_compendio_eventos (en DESC)",
]


# ══ Código del link ═══════════════════════════════════════════════════════

def _clave() -> bytes:
    from routers.auth_guard import _secret   # la misma clave que firma las sesiones
    return hashlib.sha256(b"finsys-compendio::" + _secret()).digest()


def token_de(nonce: str) -> str:
    firma = hmac.new(_clave(), f"compendio|{nonce}".encode(), hashlib.sha256).digest()
    return base64.urlsafe_b64encode(firma).rstrip(b"=").decode()


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def ruta_de(fila: Dict[str, Any]) -> Optional[str]:
    """/c/<código> si este servidor puede rearmarlo (otra clave → None)."""
    nonce = fila.get("nonce")
    if not nonce:
        return None
    t = token_de(nonce)
    return f"/c/{t}" if hmac.compare_digest(hash_token(t), str(fila.get("token_hash") or "")) else None


# ══ Utilidades puras ══════════════════════════════════════════════════════

def _ahora() -> datetime:
    return datetime.now(timezone.utc)


def _num(x) -> float:
    try:
        return float(x) if x is not None else 0.0
    except (TypeError, ValueError):
        return 0.0


def _txt(x) -> str:
    if x is None:
        return ""
    if isinstance(x, (list, tuple)):
        return ", ".join(str(i) for i in x if i not in (None, ""))
    return str(x).strip()


def _fecha(v) -> Optional[str]:
    if isinstance(v, datetime):
        return v.date().isoformat()
    if isinstance(v, date):
        return v.isoformat()
    s = str(v or "")[:10]
    return s if re.match(r"^\d{4}-\d{2}-\d{2}$", s) else None


def _limpio(v, campo: str, maximo: int, multilinea: bool = False) -> Optional[str]:
    patron = r"[\x00-\x09\x0b-\x1f\x7f]" if multilinea else r"[\x00-\x1f\x7f]"
    s = re.sub(patron, " ", str(v or "")).strip()
    if not s:
        return None
    if len(s) > maximo:
        raise ValueError(f"'{campo}' admite máximo {maximo} caracteres.")
    return s


def maps_seguro(url) -> Optional[str]:
    """Solo https de Google Maps (el link es editable a mano: nada de javascript: ni otros sitios)."""
    s = str(url or "").strip()
    if not s:
        return None
    u = urlparse(s)
    if u.scheme != "https" or not _MAPS.match((u.hostname or "").lower()):
        return None
    return s


def prefijo_bucket() -> str:
    from fin_sys_core.storage_media import BUCKET, SUPABASE_URL
    return f"{SUPABASE_URL}/storage/v1/object/public/{BUCKET}/"


def describir_soporte(url: str, prefijo: Optional[str] = None) -> Dict[str, Any]:
    """{nombre, tipo, mime, servible}. Servible = vive en NUESTRO bucket (sin SSRF);
    una ruta local antigua (/uploads) o de otro sitio sale como "no disponible"."""
    prefijo = prefijo if prefijo is not None else prefijo_bucket()
    s = str(url or "")
    ruta = s[len(prefijo):] if s.startswith(prefijo) else ""
    servible = bool(ruta) and ".." not in ruta and "?" not in ruta and "#" not in ruta
    nombre = unquote(s.rstrip("/").rsplit("/", 1)[-1])[:80] or "comprobante"
    ext = nombre.rsplit(".", 1)[-1].lower() if "." in nombre else ""
    mime, tipo = MIME_POR_EXT.get(ext, ("application/octet-stream", TIPO_OTRO))
    return {"nombre": nombre, "tipo": tipo, "mime": mime, "servible": servible}


def estado(fila: Dict[str, Any], ahora: Optional[datetime] = None) -> str:
    if fila.get("revocado_en"):
        return "revocado"
    expira = fila.get("expira_en")
    if isinstance(expira, str):
        expira = datetime.fromisoformat(expira)
    return "vencido" if expira is None or expira <= (ahora or _ahora()) else "vigente"


def _opciones(datos: Dict[str, Any]) -> Dict[str, bool]:
    return {"identificacion": bool(datos.get("identificacion", True)),
            "ubicaciones": bool(datos.get("ubicaciones", True))}


def _vigencia(v) -> int:
    try:
        dias = int(v if v not in (None, "") else VIGENCIA_DEFECTO)
    except (TypeError, ValueError):
        dias = -1
    if dias not in VIGENCIAS:
        raise ValueError(f"La vigencia debe ser {', '.join(map(str, VIGENCIAS))} días.")
    return dias


def _tx_ids(v) -> List[int]:
    if not isinstance(v, (list, tuple)) or not v:
        raise ValueError("Elige al menos una transacción.")
    try:
        ids = sorted({int(x) for x in v})
    except (TypeError, ValueError):
        raise ValueError("'tx_ids' debe ser una lista de números.")
    if any(i <= 0 for i in ids):
        raise ValueError("'tx_ids' debe ser una lista de números positivos.")
    if len(ids) > MAX_TX:
        raise ValueError(f"Máximo {MAX_TX} transacciones por compendio ({len(ids)} elegidas).")
    return ids


def armar_snapshot(txs: List[Dict[str, Any]], empresas: Dict[str, Dict[str, str]],
                   opciones: Dict[str, bool], nombre: str, nota: Optional[str]) -> Dict[str, Any]:
    """La foto que ve el cliente (pura). `empresas`: nombre del portafolio → {nombre, nit}.
    Sin asientos: son del contador (decisión de Andrés 06-oct)."""
    orden = sorted(txs, key=lambda t: (_fecha(t.get("transaction_date")) or "", t.get("id") or 0))
    filas, totales, usadas = [], {}, []
    for i, t in enumerate(orden):
        tipo = _txt(t.get("type")).upper()
        moneda = (_txt(t.get("transaction_currency")) or "COP").upper()
        neto = _num(t.get("net_value"))
        tot = totales.setdefault(moneda, {"n": 0, "ingresos": 0.0, "gastos": 0.0, "neto": 0.0})
        tot["n"] += 1
        if tipo == "INGRESO":
            tot["ingresos"] += neto
        elif tipo == "GASTO":
            tot["gastos"] += neto
        tot["neto"] = round(tot["ingresos"] - tot["gastos"], 2)
        portafolio = _txt(t.get("portfolio_name"))
        emp = empresas.get(portafolio) or {}
        if portafolio and portafolio not in usadas:
            usadas.append(portafolio)
        fila = {
            "i": i, "id": t.get("id"), "fecha": _fecha(t.get("transaction_date")), "tipo": tipo,
            "concepto": _txt(t.get("concept")), "categoria": _txt(t.get("category")),
            "tercero": _txt(t.get("third_party_name")), "empresa": emp.get("nombre") or portafolio,
            "cuenta": _txt(t.get("account_name")) or _txt(t.get("payment_method")),
            "moneda": moneda, "neto": round(neto, 2), "bruto": round(_num(t.get("amount")), 2),
            "iva": round(_num(t.get("tax_iva_amount")), 2), "gmf": round(_num(t.get("tax_gmf_amount")), 2),
        }
        if opciones.get("identificacion"):
            fila["identificacion"] = " ".join(x for x in (_txt(t.get("identification_type")),
                                                          _txt(t.get("identification_number"))) if x)
        if opciones.get("ubicaciones"):
            fila["maps"] = maps_seguro(t.get("geo_maps_link"))
        filas.append(fila)
    for tot in totales.values():
        tot["ingresos"], tot["gastos"] = round(tot["ingresos"], 2), round(tot["gastos"], 2)
    fechas = [f["fecha"] for f in filas if f["fecha"]]
    return {
        "nombre": nombre, "nota": nota, "n": len(filas),
        "empresas": [{"nombre": (empresas.get(p) or {}).get("nombre") or p,
                      "nit": (empresas.get(p) or {}).get("nit") or ""} for p in usadas],
        "rango": {"desde": min(fechas) if fechas else None, "hasta": max(fechas) if fechas else None},
        "totales": totales, "opciones": dict(opciones), "txs": filas,
    }


# ══ Lecturas (la misma fuente que el motor 13.4) ═══════════════════════════

def _leer_txs(ids: List[int]) -> Tuple[List[Dict[str, Any]], List[int], Dict[str, Dict[str, str]]]:
    from database_driver import obtener_portafolios, obtener_transacciones
    from fin_sys_core import export_xlsx as ex
    sel = set(ids)
    txs = [t for t in ex._sin_duplicados(obtener_transacciones(None)) if t.get("id") in sel]
    if not txs:
        raise ValueError("Ninguna de las transacciones elegidas existe.")
    faltan = sorted(sel - {t.get("id") for t in txs})
    ident = ex._identidad_empresas()
    empresas = {p["name"]: ident.get(int(p["id"]), {}) for p in (obtener_portafolios() or [])}
    return txs, faltan, empresas


SQL_SOPORTES = """
    SELECT t.id, t.evidence_file_path,
           COALESCE((SELECT json_agg(ev.file_path ORDER BY ev.id) FROM transaction_evidences ev
                      WHERE ev.transaction_id = t.id), '[]'::json)
      FROM transactions t
     WHERE t.id = ANY(%s)
"""


def soportes_vivos(cur, ids: List[int]) -> Dict[int, List[str]]:
    """Los comprobantes de HOY de cada TX, en el orden del botón [Ver] y de la hoja SOPORTES."""
    from fin_sys_core import export_xlsx as ex
    if not ids:
        return {}
    cur.execute(SQL_SOPORTES, (list(ids),))
    out: Dict[int, List[str]] = {}
    for tx_id, legado, evs in cur.fetchall():
        if isinstance(evs, str):
            evs = json.loads(evs)
        out[int(tx_id)] = ex._soportes({"evidences": evs or [], "evidence_file_path": legado})
    return out


# ══ Pre-vuelo y creación ══════════════════════════════════════════════════

def _resumen_soportes(snapshot: Dict[str, Any], vivos: Dict[int, List[str]]) -> Dict[str, Any]:
    prefijo = prefijo_bucket()
    sin, no_legibles, total = [], 0, 0
    for f in snapshot["txs"]:
        urls = vivos.get(f["id"]) or []
        total += len(urls)
        if not urls:
            sin.append(f["id"])
        no_legibles += sum(1 for u in urls if not describir_soporte(u, prefijo)["servible"])
    return {"comprobantes": total, "sin_comprobante": sin, "no_legibles": no_legibles}


def prevuelo(datos: Dict[str, Any], conn=None) -> Dict[str, Any]:
    ids = _tx_ids(datos.get("tx_ids"))
    _vigencia(datos.get("vigencia_dias"))
    txs, faltan, empresas = _leer_txs(ids)
    snap = armar_snapshot(txs, empresas, _opciones(datos), "", None)
    with _conexion(conn) as c:
        cur = c.cursor()
        sop = _resumen_soportes(snap, soportes_vivos(cur, [f["id"] for f in snap["txs"]]))
        cur.close()
    adv = []
    if faltan:
        adv.append("No existen (se omiten): " + ", ".join(f"#{i}" for i in faltan) + ".")
    if sop["sin_comprobante"]:
        adv.append(f"{len(sop['sin_comprobante'])} transacción(es) sin comprobante.")
    if sop["no_legibles"]:
        adv.append(f"{sop['no_legibles']} comprobante(s) guardados fuera del almacenamiento: el cliente los verá como no disponibles.")
    return {"n": snap["n"], "faltantes": faltan, "totales": snap["totales"], "rango": snap["rango"],
            "empresas": snap["empresas"], **sop, "advertencias": adv}


SQL_CREAR = """
    INSERT INTO accounting_compendios (folio, nombre, nota, tx_ids, snapshot, opciones, nonce, token_hash,
                                       expira_en, creado_por)
    VALUES (%s, %s, %s, %s, %s::jsonb, %s::jsonb, %s, %s, %s, %s)
    RETURNING id, creado_en
"""


def crear(datos: Dict[str, Any], usuario: Optional[Dict[str, Any]], conn=None) -> Dict[str, Any]:
    ids = _tx_ids(datos.get("tx_ids"))
    dias = _vigencia(datos.get("vigencia_dias"))
    nota = _limpio(datos.get("nota"), "nota", MAX_NOTA, multilinea=True)
    nombre = _limpio(datos.get("nombre"), "nombre", MAX_NOMBRE)
    opciones = _opciones(datos)
    txs, _faltan, empresas = _leer_txs(ids)
    ahora = _ahora()
    nombre = nombre or f"Compendio de {len(txs)} transacción(es) — {ahora.date().isoformat()}"
    snap = armar_snapshot(txs, empresas, opciones, nombre, nota)
    nonce = secrets.token_hex(16)
    token = token_de(nonce)
    expira = ahora + timedelta(days=dias)
    with _conexion(conn) as c:
        cur = c.cursor()
        folio = siguiente_folio(cur, ahora.year)
        snap["folio"] = folio
        snap["creado_en"] = _iso(ahora)
        cur.execute(SQL_CREAR, (folio, nombre, nota, [f["id"] for f in snap["txs"]],
                                json.dumps(snap, ensure_ascii=False), json.dumps(opciones),
                                nonce, hash_token(token), expira, _quien(usuario)))
        nuevo_id, creado = cur.fetchone()
        _purgar_eventos(cur)
        cur.close()
    return {"id": nuevo_id, "folio": folio, "nombre": nombre, "n": snap["n"], "ruta": f"/c/{token}",
            "expira_en": _iso(expira), "creado_en": _iso(creado), "vigencia_dias": dias}


RETENCION_EVENTOS_DIAS = int(os.getenv("COMPENDIO_RETENCION_EVENTOS_DIAS", "180"))
SQL_PURGA_EVENTOS = """
    DELETE FROM accounting_compendio_eventos e
     USING accounting_compendios c
     WHERE c.id = e.compendio_id AND c.expira_en < now() - make_interval(days => %s)
"""


def _purgar_eventos(cur) -> int:
    """Escalabilidad (06-oct): el detalle de eventos de los compendios vencidos hace más de
    180 días se borra; quedan sus totales (visitas, descargas, última visita) en el compendio.
    Corre al crear uno nuevo (como la purga de 13.5). Sin la tabla de eventos, no hace nada."""
    cur.execute("SAVEPOINT purga_eventos")
    try:
        cur.execute(SQL_PURGA_EVENTOS, (RETENCION_EVENTOS_DIAS,))
        n = max(cur.rowcount or 0, 0)
        cur.execute("RELEASE SAVEPOINT purga_eventos")
        return n
    except Exception as e:
        if not es_tabla_faltante(e):
            raise
        cur.execute("ROLLBACK TO SAVEPOINT purga_eventos")
        return 0


def eliminar(cid: int, conn=None) -> Dict[str, Any]:
    """🗑 Borra un compendio REVOCADO o VENCIDO con toda su actividad (ON DELETE CASCADE).
    Uno vigente no: primero se revoca (el link dejaría de funcionar sin aviso). El folio queda
    como hueco en la secuencia, igual que en la purga de 13.5."""
    with _conexion(conn) as c:
        cur = c.cursor()
        cur.execute(SQL_UNO, (cid,))
        f = _fila(cur, _COLS)
        if not f:
            raise NoEncontrado(f"El compendio {cid} no existe.")
        if estado(f) == "vigente":
            raise Conflicto("Ese compendio sigue vigente: revócalo primero y luego bórralo.")
        cur.execute("DELETE FROM accounting_compendios WHERE id = %s", (cid,))
        cur.close()
    return {"eliminado": True, "id": cid, "folio": f["folio"]}


SQL_BORRAR_INACTIVOS = """
    DELETE FROM accounting_compendios
     WHERE revocado_en IS NOT NULL OR expira_en <= now()
    RETURNING folio
"""


def eliminar_inactivos(conn=None) -> Dict[str, Any]:
    """🗑 Todos los revocados y vencidos de una vez (con su actividad)."""
    with _conexion(conn) as c:
        cur = c.cursor()
        cur.execute(SQL_BORRAR_INACTIVOS)
        folios = [r[0] for r in cur.fetchall()]
        cur.close()
    return {"eliminados": len(folios), "folios": folios}


def borrar_actividad(cid: int, conn=None) -> Dict[str, Any]:
    """🧹 Borra el detalle de actividad de un compendio (libera espacio); quedan sus totales
    (visitas, descargas, última visita) y el compendio sigue igual."""
    with _conexion(conn) as c:
        cur = c.cursor()
        cur.execute("SELECT 1 FROM accounting_compendios WHERE id = %s", (cid,))
        if not cur.fetchone():
            raise NoEncontrado(f"El compendio {cid} no existe.")
        cur.execute("DELETE FROM accounting_compendio_eventos WHERE compendio_id = %s", (cid,))
        n = max(cur.rowcount or 0, 0)
        cur.close()
    return {"borrados": n, "id": cid}


# ══ Carpeta 🔗 Compendios ══════════════════════════════════════════════════

_COLS = ("id", "folio", "nombre", "nota", "n", "creado_por", "creado_en", "expira_en", "revocado_en",
         "revocado_por", "visitas", "ultima_visita", "nonce", "token_hash")
_SELECT = """
    SELECT id, folio, nombre, nota, cardinality(tx_ids), creado_por, creado_en, expira_en, revocado_en,
           revocado_por, visitas, ultima_visita, nonce, token_hash
      FROM accounting_compendios
"""
SQL_LISTAR = _SELECT + f" ORDER BY creado_en DESC LIMIT {LIMITE_LISTA}"
SQL_UNO = _SELECT + " WHERE id = %s FOR UPDATE"


def _publica(f: Dict[str, Any], ahora: datetime, st: Optional[Tuple] = None) -> Dict[str, Any]:
    out = {k: _iso(v) for k, v in f.items() if k not in ("nonce", "token_hash")}
    out["estado"] = estado(f, ahora)
    out["ruta"] = ruta_de(f) if out["estado"] == "vigente" else None
    visitantes, revisadas, primera, ultimo = st or (0, 0, None, None)
    ultimo = _fecha_hora(ultimo)
    out.update(visitantes=int(visitantes or 0), revisadas=int(revisadas or 0), primera_visita=_iso(primera),
               en_vivo=bool(ultimo and (ahora - ultimo).total_seconds() <= VIVO_SEG))
    return out


def listar(conn=None) -> List[Dict[str, Any]]:
    ahora = _ahora()
    with _conexion(conn) as c:
        cur = c.cursor()
        cur.execute(SQL_LISTAR)
        filas = _filas(cur, _COLS)
        stats = _estadisticas(cur, [f["id"] for f in filas])
        cur.close()
    return [_publica(f, ahora, stats.get(f["id"])) for f in filas]


def actualizar(cid: int, cambios: Dict[str, Any], usuario: Optional[Dict[str, Any]], conn=None) -> Dict[str, Any]:
    """{ampliar_dias: 7|15|30|90} suma desde hoy o desde el vencimiento si aún no llega;
    {revocar: true} es definitivo (para volver a compartir, se crea otro compendio)."""
    revocar = bool(cambios.get("revocar"))
    dias = None if revocar else _vigencia(cambios.get("ampliar_dias"))
    ahora = _ahora()
    with _conexion(conn) as c:
        cur = c.cursor()
        cur.execute(SQL_UNO, (cid,))
        f = _fila(cur, _COLS)
        if not f:
            raise NoEncontrado(f"El compendio {cid} no existe.")
        if f["revocado_en"]:
            raise Conflicto("Ese compendio está revocado: crea uno nuevo para volver a compartir.")
        if revocar:
            cur.execute("UPDATE accounting_compendios SET revocado_en = %s, revocado_por = %s WHERE id = %s",
                        (ahora, _quien(usuario), cid))
            f.update(revocado_en=ahora, revocado_por=_quien(usuario))
        else:
            base = max(f["expira_en"], ahora) if f["expira_en"] else ahora
            nueva = base + timedelta(days=dias)
            cur.execute("UPDATE accounting_compendios SET expira_en = %s WHERE id = %s", (nueva, cid))
            f["expira_en"] = nueva
        cur.close()
    return _publica(f, ahora)


# ══ Lo que ve el cliente (sin sesión: token) ═══════════════════════════════

SQL_ABRIR = """
    SELECT id, folio, snapshot, expira_en, revocado_en
      FROM accounting_compendios WHERE token_hash = %s
"""


def _vigente(cur, token: str) -> Dict[str, Any]:
    if not _TOKEN.match(str(token or "")):
        raise NoDisponible()
    cur.execute(SQL_ABRIR, (hash_token(token),))
    f = _fila(cur, ("id", "folio", "snapshot", "expira_en", "revocado_en"))
    if not f or estado(f) != "vigente":
        raise NoDisponible()
    if isinstance(f["snapshot"], str):
        f["snapshot"] = json.loads(f["snapshot"])
    return f


def abrir(token: str, conn=None) -> Dict[str, Any]:
    """La foto + los comprobantes de HOY de cada TX (descritos, nunca su URL).
    Solo lee: la visita la anota el router aparte con anotar() (13.6-c), así un
    fallo del registro jamás tumba la página del cliente. `_id` es para eso."""
    if not _TOKEN.match(str(token or "")):
        raise NoDisponible()
    with _conexion(conn) as c:
        cur = c.cursor()
        f = _vigente(cur, token)
        snap = f["snapshot"]
        vivos = soportes_vivos(cur, [t["id"] for t in snap.get("txs", [])])
        cur.close()
    prefijo = prefijo_bucket()
    for t in snap.get("txs", []):
        t["soportes"] = [{"j": j, **{k: v for k, v in describir_soporte(u, prefijo).items() if k != "mime"}}
                         for j, u in enumerate(vivos.get(t["id"]) or [])]
    snap["expira_en"] = _iso(f["expira_en"])
    snap["_id"] = f["id"]
    return snap


def soporte(token: str, i: int, j: int, conn=None) -> Dict[str, Any]:
    """{url, nombre, mime, tipo} del comprobante j de la TX i. Solo por índice de la foto y
    solo de nuestro bucket: no hay forma de pedir una URL arbitraria (CA-136-04)."""
    if not _TOKEN.match(str(token or "")):
        raise NoDisponible()
    with _conexion(conn) as c:
        cur = c.cursor()
        f = _vigente(cur, token)
        txs = f["snapshot"].get("txs", [])
        if not (0 <= i < len(txs)):
            raise NoDisponible()
        urls = soportes_vivos(cur, [txs[i]["id"]]).get(txs[i]["id"]) or []
        cur.close()
    if not (0 <= j < len(urls)):
        raise NoDisponible()
    d = describir_soporte(urls[j])
    if not d["servible"]:
        raise NoDisponible()
    return {"url": urls[j], **d, "_id": f["id"]}


# ══ 13.6-c 📈 Seguimiento: qué abrió el cliente y cuándo ═══════════════════

TOPE_EVENTOS = 2000              # eventos de detalle por compendio (las aperturas siempre se anotan)
VIVO_SEG = 120                   # "● EN VIVO": hubo actividad en los últimos 2 min
EVENTOS_VISTA = 200

# Vistas previas de enlaces (WhatsApp, Telegram, Facebook…) y robots: NO son el cliente.
# Sin este filtro, mandar el link por WhatsApp contaría como "el cliente lo abrió".
_ROBOT = re.compile(r"\bbot\b|bot/|crawler|spider|preview|facebookexternalhit|whatsapp/|telegrambot|slackbot|"
                    r"discordbot|linkedinbot|skypeuripreview|embedly|curl/|wget/|python-|httpx|go-http|headless",
                    re.I)


def es_robot(ua: str) -> bool:
    return not ua or bool(_ROBOT.search(ua))


def visitante_de(cid: int, quien: str, ua: str) -> str:
    """Huella del visitante SIN guardar nada identificable: HMAC con la clave del servidor (CA-136-13).
    `quien` = la cookie del visor (fsv, un aleatorio por navegador) o, sin ella, la IP. La cookie
    evita que el mismo celular cuente como varios cuando alterna IPv6/IPv4 (06-oct)."""
    return hmac.new(_clave(), f"visitante|{cid}|{quien}|{ua}".encode(), hashlib.sha256).hexdigest()[:12]


def dispositivo_de(ua: str) -> str:
    u = (ua or "").lower()
    if "iphone" in u:
        so, icono = "iPhone", "📱"
    elif "ipad" in u:
        so, icono = "iPad", "📱"
    elif "android" in u:
        so, icono = "Android", "📱"
    elif "windows" in u:
        so, icono = "Windows", "💻"
    elif "macintosh" in u or "mac os x" in u:
        so, icono = "Mac", "💻"
    elif "linux" in u or "cros" in u:
        so, icono = "Linux", "💻"
    else:
        so, icono = "Otro", "🌐"
    for marca, nombre in (("edg", "Edge"), ("opr/", "Opera"), ("samsungbrowser", "Samsung"), ("fban", "Facebook"),
                          ("instagram", "Instagram"), ("crios", "Chrome"), ("fxios", "Firefox"), ("firefox/", "Firefox"),
                          ("chrome/", "Chrome"), ("safari/", "Safari")):
        if marca in u:
            return f"{icono} {so} · {nombre}"[:60]
    return f"{icono} {so}"[:60]


SQL_ANOTAR = """
    INSERT INTO accounting_compendio_eventos (compendio_id, tipo, tx_i, soporte_j, visitante, dispositivo)
    SELECT %(c)s, %(t)s, %(i)s, %(j)s, %(v)s, %(d)s
     WHERE NOT EXISTS (SELECT 1 FROM accounting_compendio_eventos
                        WHERE compendio_id = %(c)s AND visitante = %(v)s AND tipo = %(t)s
                          AND tx_i IS NOT DISTINCT FROM %(i)s AND soporte_j IS NOT DISTINCT FROM %(j)s
                          AND en > now() - interval '10 minutes')
       AND (%(t)s = 'abrio'
            OR (SELECT count(*) FROM accounting_compendio_eventos WHERE compendio_id = %(c)s) < %(tope)s)
    RETURNING id
"""


def _anotar(cur, cid: int, tipo: str, visitante: str, dispositivo: str,
            i: Optional[int] = None, j: Optional[int] = None) -> Dict[str, Any]:
    """Anota un evento (sin repetir el mismo dentro de 10 min). → {nuevo, primera, folio, nombre};
    `primera` = es la PRIMERA apertura del compendio (para el aviso por Telegram)."""
    # Dos peticiones simultáneas del mismo visitante (p. ej. el celular que abre el link dos veces
    # en 30 ms) verían "no está anotado" a la vez: el candado de transacción las pone en fila.
    cur.execute("SELECT pg_advisory_xact_lock(hashtext(%s))", (f"compendio|{cid}|{visitante}|{tipo}|{i}|{j}",))
    cur.execute(SQL_ANOTAR, {"c": cid, "t": tipo, "i": i, "j": j, "v": visitante,
                             "d": (dispositivo or "")[:60], "tope": TOPE_EVENTOS})
    if not cur.fetchone():
        return {"nuevo": False, "primera": False}
    if tipo == "abrio":
        cur.execute("UPDATE accounting_compendios SET visitas = visitas + 1, ultima_visita = now() "
                    "WHERE id = %s RETURNING visitas, folio, nombre", (cid,))
        r = cur.fetchone()
        return {"nuevo": True, "primera": bool(r and r[0] == 1), "folio": r and r[1], "nombre": r and r[2]}
    if tipo in ("pdf", "html"):                                  # 13.6-d/e: descargas del cliente
        cur.execute(f"UPDATE accounting_compendios SET descargas_{tipo} = descargas_{tipo} + 1, "
                    "ultima_visita = now() WHERE id = %s", (cid,))
    else:
        cur.execute("UPDATE accounting_compendios SET ultima_visita = now() WHERE id = %s", (cid,))
    return {"nuevo": True, "primera": False}


def anotar(cid: int, tipo: str, ip: str, ua: str, i: Optional[int] = None, j: Optional[int] = None,
           conn=None) -> Dict[str, Any]:
    """Lo que el router anota al servir la página (abrio) o un comprobante. Los robots no cuentan."""
    if es_robot(ua):
        return {"nuevo": False, "primera": False, "robot": True}
    dispositivo = dispositivo_de(ua)
    with _conexion(conn) as c:
        cur = c.cursor()
        r = _anotar(cur, cid, tipo, visitante_de(cid, ip, ua), dispositivo, i, j)
        cur.close()
    return {**r, "dispositivo": dispositivo}


def evento_publico(token: str, tipo: str, i, ip: str, ua: str, conn=None) -> Dict[str, Any]:
    """Aviso del visor (sendBeacon): el cliente abrió la TX i. Solo 'tx' y solo índices de la foto."""
    if tipo != "tx" or not isinstance(i, int) or isinstance(i, bool) or not _TOKEN.match(str(token or "")):
        raise NoDisponible()
    with _conexion(conn) as c:
        cur = c.cursor()
        f = _vigente(cur, token)
        if not (0 <= i < len(f["snapshot"].get("txs", []))):
            raise NoDisponible()
        r = {"nuevo": False} if es_robot(ua) else _anotar(cur, f["id"], "tx", visitante_de(f["id"], ip, ua),
                                                          dispositivo_de(ua), i, None)
        cur.close()
    return r


def _fecha_hora(v) -> Optional[datetime]:
    if isinstance(v, str):
        v = datetime.fromisoformat(v)
    return v


def resumir(snapshot: Dict[str, Any], eventos: List[Dict[str, Any]], total_comprobantes: Dict[int, int],
            creado_en=None, ahora: Optional[datetime] = None) -> Dict[str, Any]:
    """Pura: eventos (en orden) → KPIs, "qué revisó" por TX y la línea de tiempo (más reciente primero)."""
    ahora = ahora or _ahora()
    txs = snapshot.get("txs", [])
    eventos = sorted(eventos, key=lambda e: _fecha_hora(e["en"]))
    numero: Dict[str, int] = {}
    por_i: Dict[int, Dict[str, Any]] = {}
    for e in eventos:
        numero.setdefault(e["visitante"], len(numero) + 1)
        i = e.get("tx_i")
        if e["tipo"] in ("tx", "comprobante") and isinstance(i, int) and 0 <= i < len(txs):
            d = por_i.setdefault(i, {"aperturas": 0, "vistos": set(), "ultima": None})
            if e["tipo"] == "tx":
                d["aperturas"] += 1
            elif e.get("soporte_j") is not None:
                d["vistos"].add(e["soporte_j"])
            d["ultima"] = e["en"]
    aperturas = [e for e in eventos if e["tipo"] == "abrio"]
    primera = _fecha_hora(aperturas[0]["en"]) if aperturas else None
    ultima = _fecha_hora(eventos[-1]["en"]) if eventos else None
    creado = _fecha_hora(creado_en)
    por_tx = []
    for t in txs:
        d = por_i.get(t["i"])
        por_tx.append({"i": t["i"], "id": t["id"], "fecha": t.get("fecha"), "concepto": t.get("concepto"),
                       "neto": t.get("neto"), "moneda": t.get("moneda"), "revisada": d is not None,
                       "aperturas": d["aperturas"] if d else 0, "comprobantes_vistos": len(d["vistos"]) if d else 0,
                       "comprobantes_total": total_comprobantes.get(t["id"], 0),
                       "ultima": _iso(d["ultima"]) if d else None})

    def concepto(i):
        return txs[i].get("concepto") if isinstance(i, int) and 0 <= i < len(txs) else None

    linea = [{"en": _iso(e["en"]), "tipo": e["tipo"], "i": e.get("tx_i"), "j": e.get("soporte_j"),
              "concepto": concepto(e.get("tx_i")), "visitante": f"Visitante {numero[e['visitante']]}",
              "dispositivo": e.get("dispositivo") or ""} for e in reversed(eventos)][:EVENTOS_VISTA]
    return {
        "resumen": {
            "aperturas": len(aperturas), "visitantes": len(numero), "revisadas": len(por_i), "total": len(txs),
            "primera": _iso(primera), "ultima": _iso(ultima),
            "en_vivo": bool(ultima and (ahora - ultima).total_seconds() <= VIVO_SEG),
            "horas_hasta_primera": round((primera - creado).total_seconds() / 3600, 1) if primera and creado else None,
        },
        "por_tx": por_tx, "eventos": linea,
    }


_COLS_EV = ("tipo", "tx_i", "soporte_j", "visitante", "dispositivo", "en")


def seguimiento(cid: int, conn=None) -> Dict[str, Any]:
    with _conexion(conn) as c:
        cur = c.cursor()
        cur.execute("SELECT id, folio, nombre, snapshot, creado_en, expira_en, revocado_en "
                    "FROM accounting_compendios WHERE id = %s", (cid,))
        f = _fila(cur, ("id", "folio", "nombre", "snapshot", "creado_en", "expira_en", "revocado_en"))
        if not f:
            raise NoEncontrado(f"El compendio {cid} no existe.")
        snap = json.loads(f["snapshot"]) if isinstance(f["snapshot"], str) else f["snapshot"]
        cur.execute("SELECT " + ", ".join(_COLS_EV) + " FROM accounting_compendio_eventos "
                    "WHERE compendio_id = %s ORDER BY en, id LIMIT %s", (cid, TOPE_EVENTOS + 1000))
        eventos = _filas(cur, _COLS_EV)
        vivos = soportes_vivos(cur, [t["id"] for t in snap.get("txs", [])])
        cur.close()
    return {"id": f["id"], "folio": f["folio"], "nombre": f["nombre"], "estado": estado(f),
            "creado_en": _iso(f["creado_en"]), "expira_en": _iso(f["expira_en"]),
            **resumir(snap, eventos, {k: len(v) for k, v in vivos.items()}, f["creado_en"])}


SQL_ACTIVIDAD = """
    SELECT e.en, e.tipo, e.tx_i, e.soporte_j, e.dispositivo, c.id, c.folio, c.nombre,
           c.snapshot->'txs'->e.tx_i->>'concepto'
      FROM accounting_compendio_eventos e
      JOIN accounting_compendios c ON c.id = e.compendio_id
     ORDER BY e.en DESC, e.id DESC
     LIMIT %s
"""


def actividad(limite: int = 10, conn=None) -> List[Dict[str, Any]]:
    """Lo último que hicieron los clientes en TODOS los compendios (arriba del panel 🔗)."""
    limite = max(1, min(int(limite or 10), 50))
    cols = ("en", "tipo", "i", "j", "dispositivo", "compendio_id", "folio", "nombre", "concepto")
    with _conexion(conn) as c:
        cur = c.cursor()
        cur.execute(SQL_ACTIVIDAD, (limite,))
        filas = _filas(cur, cols)
        cur.close()
    return [{k: _iso(v) for k, v in f.items()} for f in filas]


SQL_STATS = """
    SELECT compendio_id, count(DISTINCT visitante),
           count(DISTINCT tx_i) FILTER (WHERE tipo IN ('tx', 'comprobante')),
           min(en) FILTER (WHERE tipo = 'abrio'), max(en)
      FROM accounting_compendio_eventos
     WHERE compendio_id = ANY(%s)
     GROUP BY compendio_id
"""


def _estadisticas(cur, ids: List[int]) -> Dict[int, Tuple]:
    """Por compendio: visitantes, revisadas, 1.ª apertura, último evento. Si la tabla de
    eventos aún no existe (migración pendiente), el panel sigue funcionando sin ellas."""
    if not ids:
        return {}
    cur.execute("SAVEPOINT compendio_stats")
    try:
        cur.execute(SQL_STATS, (list(ids),))
        out = {int(r[0]): tuple(r[1:]) for r in cur.fetchall()}
        cur.execute("RELEASE SAVEPOINT compendio_stats")
        return out
    except Exception as e:
        if not es_tabla_faltante(e):
            raise
        cur.execute("ROLLBACK TO SAVEPOINT compendio_stats")
        return {}


# ══ 13.6-d/e Descargas: la MISMA foto que el link (R-136-06) ═══════════════

def para_descarga(token: Optional[str] = None, cid: Optional[int] = None, conn=None) -> Dict[str, Any]:
    """→ {id, snapshot, urls (por tx_id, en vivo), expira_en}. Por código (cliente: solo si está
    vigente) o por id (contador, desde ⇩ Exportación: aunque esté vencido o revocado)."""
    with _conexion(conn) as c:
        cur = c.cursor()
        if token is not None:
            f = _vigente(cur, token)
        else:
            cur.execute("SELECT id, folio, snapshot, expira_en, revocado_en FROM accounting_compendios WHERE id = %s",
                        (cid,))
            f = _fila(cur, ("id", "folio", "snapshot", "expira_en", "revocado_en"))
            if not f:
                raise NoEncontrado(f"El compendio {cid} no existe.")
            if isinstance(f["snapshot"], str):
                f["snapshot"] = json.loads(f["snapshot"])
        urls = soportes_vivos(cur, [t["id"] for t in f["snapshot"].get("txs", [])])
        cur.close()
    f["snapshot"].setdefault("folio", f["folio"])
    return {"id": f["id"], "snapshot": f["snapshot"], "urls": urls, "expira_en": _iso(f["expira_en"])}


def max_bytes_soporte() -> int:
    from fin_sys_core.storage_media import MAX_BYTES
    return int(os.getenv("COMPENDIO_MAX_BYTES_SOPORTE") or MAX_BYTES)
