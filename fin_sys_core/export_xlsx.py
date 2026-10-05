# -*- coding: utf-8 -*-
"""
export_xlsx.py — Motor de libros contables .xlsx (Análisis Inteligente, spec 13.4).

Viste de Excel lo que FIN-SYS YA calcula; no inventa cifras (R-13-01):
  · libros oficiales desde el kernel (kernel_reports + kernel_journal_workflow),
    solo asientos "en libros" (CONTABILIZADO + ANULADO — el espejo cancela);
  · hojas de transacciones desde obtener_transacciones (la misma verdad que el
    dataset de Perspective) y la cartera desde listar_cartera.

Tres funciones públicas:
  normalizar_receta(receta)            → receta validada (ValueError = 400)
  recolectar(receta)                   → datos (TODO el acceso a BD vive aquí)
  construir_libro(datos, receta, ...)  → (bytes .xlsx, sello) — pura, sin BD
  armar_libro(receta, usuario)         → (bytes, sello, nombre_de_archivo)

Reglas: una moneda distinta de COP jamás se suma al COP (bloque propio); los
filtros finos solo tocan las hojas de transacciones (D-134-07); los totales son
fórmulas =SUM reales para que el contador audite con un clic (D-134-05).
"""
import io
import re
import unicodedata
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import Any, Callable, Dict, List, Optional, Tuple

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from openpyxl.workbook.properties import CalcProperties
from openpyxl.worksheet.hyperlink import Hyperlink

MIME_XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

MODOS = ("periodo", "transacciones")

HOJAS_PERIODO = {
    "caratula": "CARÁTULA",
    "diario": "LIBRO DIARIO",
    "mayor": "MAYOR",
    "balance_prueba": "BALANCE DE PRUEBA",
    "estado_resultados": "ESTADO DE RESULTADOS",
    "balance_general": "BALANCE GENERAL",
    "movimientos": "MOVIMIENTOS",
    "auxiliar_tercero": "AUXILIAR POR TERCERO",
    "cartera": "CARTERA POR EDADES",
    "impuestos": "IMPUESTOS",
}
HOJAS_TRANSACCIONES = {
    "caratula": "CARÁTULA",
    "relacion": "RELACIÓN",
    "asientos": "ASIENTOS",
    "resumen": "RESUMEN",
    "soportes": "SOPORTES",
}

TIPOS_TX = ("INGRESO", "GASTO", "TRANSFERENCIA")
NIVELES_PUC = {"clase": 1, "grupo": 2, "cuenta": 4, "subcuenta": 6}
CLASES_PUC = {
    "1": "Activo", "2": "Pasivo", "3": "Patrimonio", "4": "Ingresos", "5": "Gastos",
    "6": "Costos de ventas", "7": "Costos de producción",
    "8": "Cuentas de orden deudoras", "9": "Cuentas de orden acreedoras",
}
EN_LIBROS = ("CONTABILIZADO", "ANULADO")
LIMITE_ASIENTOS = 100_000
MAX_TX_IDS = 5000
COLOMBIA = timezone(timedelta(hours=-5))   # Colombia no tiene horario de verano

FMT_NUM = '#,##0.00;[Red](#,##0.00);"-"'
FMT_INT = "0"
FMT_FECHA = "dd/mm/yyyy"

_NEGRO = PatternFill("solid", fgColor="000000")
_PAPEL = PatternFill("solid", fgColor="E9E4D6")
_AMBAR = PatternFill("solid", fgColor="FDF3D7")
_LADO = Side(style="thin", color="000000")
_BORDE = Border(left=_LADO, right=_LADO, top=_LADO, bottom=_LADO)
_F_TITULO = Font(bold=True, size=14)
_F_SUB = Font(italic=True, size=9, color="555555")
_F_ENC = Font(bold=True, color="FFFFFF")
_F_NEGRITA = Font(bold=True)
_F_NOTA = Font(italic=True, color="555555")
_F_LINK = Font(color="1D4ED8", underline="single")


# ══ Receta ═══════════════════════════════════════════════════════════════

def _fecha(v, campo: str) -> Optional[date]:
    if v in (None, ""):
        return None
    if isinstance(v, datetime):
        return v.date()
    if isinstance(v, date):
        return v
    try:
        return date.fromisoformat(str(v).strip()[:10])
    except ValueError:
        raise ValueError(f"Fecha inválida en '{campo}': {v!r} (usa AAAA-MM-DD).")


def _lista_int(v, campo: str) -> List[int]:
    if v in (None, "", []):
        return []
    if isinstance(v, int):
        v = [v]
    if isinstance(v, str):
        v = [x for x in re.split(r"[,\s]+", v) if x]
    out: List[int] = []
    for x in v:
        try:
            n = int(x)
        except (TypeError, ValueError):
            raise ValueError(f"'{campo}' debe ser una lista de números enteros: {x!r} no lo es.")
        if n <= 0:
            raise ValueError(f"'{campo}' solo admite números positivos: {n}.")
        if n not in out:
            out.append(n)
    return out


def _lista_txt(v) -> List[str]:
    if v in (None, "", []):
        return []
    if isinstance(v, str):
        v = v.split(",")
    out: List[str] = []
    for x in v:
        s = str(x).strip()
        if s and s not in out:
            out.append(s)
    return out


def hoy_colombia() -> date:
    return datetime.now(COLOMBIA).date()


def normalizar_receta(receta: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Valida y completa la receta. Cualquier error es del usuario → ValueError."""
    r = dict(receta or {})
    modo = str(r.get("modo") or "periodo").strip().lower()
    if modo not in MODOS:
        raise ValueError(f"Modo desconocido: {modo!r}. Usa 'periodo' o 'transacciones'.")

    portfolios = _lista_int(r.get("portfolios"), "portfolios")
    if r.get("portfolio_id") not in (None, ""):
        portfolios = _lista_int([r["portfolio_id"]] + portfolios, "portfolio_id")

    desde = _fecha(r.get("desde"), "desde")
    hasta = _fecha(r.get("hasta"), "hasta")
    if modo == "periodo" and hasta is None:
        hasta = hoy_colombia()
    if desde and hasta and desde > hasta:
        raise ValueError("La fecha 'desde' no puede ser posterior a 'hasta'.")

    catalogo = HOJAS_PERIODO if modo == "periodo" else HOJAS_TRANSACCIONES
    pedidas = [h.lower() for h in _lista_txt(r.get("hojas"))]
    desconocidas = [h for h in pedidas if h not in catalogo]
    if desconocidas:
        raise ValueError(f"Hojas desconocidas para el modo {modo}: {', '.join(desconocidas)}. "
                         f"Disponibles: {', '.join(catalogo)}.")
    hojas = [h for h in catalogo if h == "caratula" or not pedidas or h in pedidas]

    f_in = r.get("filtros") or {}
    tipos = [t.upper() for t in _lista_txt(f_in.get("tipos"))]
    malos = [t for t in tipos if t not in TIPOS_TX]
    if malos:
        raise ValueError(f"Tipos desconocidos: {', '.join(malos)}. Usa {', '.join(TIPOS_TX)}.")
    moneda = str(f_in.get("moneda") or "").strip().upper() or None
    filtros = {
        "categorias": _lista_txt(f_in.get("categorias")),
        "terceros": _lista_int(f_in.get("terceros"), "terceros"),
        "tipos": tipos,
        "moneda": moneda,
        "cuentas_puc": _lista_txt(f_in.get("cuentas_puc")),
    }

    nivel = str(r.get("nivel_puc") or "").strip().lower() or None
    if nivel and nivel not in NIVELES_PUC:
        raise ValueError(f"Nivel PUC desconocido: {nivel!r}. Usa {', '.join(NIVELES_PUC)}.")

    tx_ids = _lista_int(r.get("tx_ids"), "tx_ids")
    if modo == "transacciones":
        if not tx_ids:
            raise ValueError("Elige al menos una transacción para exportar.")
        if len(tx_ids) > MAX_TX_IDS:
            raise ValueError(f"Máximo {MAX_TX_IDS} transacciones por relación ({len(tx_ids)} elegidas).")
    elif tx_ids:
        raise ValueError("'tx_ids' solo aplica al modo 'transacciones'.")

    return {
        "modo": modo, "portfolios": portfolios, "desde": desde, "hasta": hasta,
        "hojas": hojas, "filtros": filtros, "nivel_puc": nivel, "tx_ids": tx_ids,
        "nombre": (str(r.get("nombre") or "").strip()[:120] or None),
        "folio": (str(r.get("folio") or "").strip()[:30] or None),
    }


# ══ Utilidades de datos ══════════════════════════════════════════════════

def _num(x) -> float:
    if x is None:
        return 0.0
    try:
        return float(x)
    except (TypeError, ValueError):
        return 0.0


def _texto(x) -> str:
    if x is None:
        return ""
    if isinstance(x, (list, tuple)):
        return ", ".join(str(i) for i in x if i not in (None, ""))
    return str(x).strip()


def _a_fecha(v) -> Optional[date]:
    if v in (None, ""):
        return None
    if isinstance(v, datetime):
        return v.date()
    if isinstance(v, date):
        return v
    try:
        return date.fromisoformat(str(v)[:10])
    except ValueError:
        return None


def _moneda(t: Dict[str, Any]) -> str:
    return (_texto(t.get("transaction_currency")) or "COP").upper()


def _orden_codigo(codigo) -> Tuple[bool, str]:
    c = str(codigo or "")
    return (not c.isdigit(), c)


def _soportes(t: Dict[str, Any]) -> List[str]:
    out: List[str] = []
    for u in (t.get("evidences") or []):
        if u and u not in out:
            out.append(str(u))
    legado = _texto(t.get("evidence_file_path"))
    if legado and legado not in out:
        out.insert(0, legado)
    return out


def _sin_duplicados(txs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """obtener_transacciones hace LEFT JOIN con assets/cartera: una TX puede
    venir repetida. El libro la cuenta UNA vez."""
    vistos, out = set(), []
    for t in txs or []:
        k = t.get("id")
        if k in vistos:
            continue
        vistos.add(k)
        out.append(t)
    return out


def aplicar_filtros(txs: List[Dict[str, Any]], filtros: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Filtros finos (D-134-07): solo hojas de transacciones."""
    cats = {c.lower() for c in filtros.get("categorias") or []}
    terceros = set(filtros.get("terceros") or [])
    tipos = set(filtros.get("tipos") or [])
    moneda = filtros.get("moneda")
    out = []
    for t in txs:
        if cats and _texto(t.get("category")).lower() not in cats:
            continue
        if terceros and t.get("third_party_id") not in terceros:
            continue
        if tipos and _texto(t.get("type")).upper() not in tipos:
            continue
        if moneda and _moneda(t) != moneda:
            continue
        out.append(t)
    return out


def _hay_filtros(filtros: Dict[str, Any]) -> bool:
    return any(filtros.get(k) for k in ("categorias", "terceros", "tipos", "moneda"))


# ── Fusión de reportes del kernel (una empresa, varias o consolidado) ─────

def _fusionar_bp(bps: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Suma por cuenta con saldos NETOS (Db − Cr): así una cuenta deudora en una
    empresa y acreedora en otra se compensa como corresponde."""
    por: Dict[str, Dict[str, Any]] = {}
    for bp in bps:
        for c in (bp or {}).get("cuentas", []):
            k = str(c["cuenta_codigo"])
            a = por.setdefault(k, {"codigo": k, "nombre": c.get("cuenta_nombre") or "",
                                   "tipo": c.get("cuenta_tipo") or "", "ini": 0.0, "db": 0.0, "cr": 0.0})
            a["nombre"] = a["nombre"] or c.get("cuenta_nombre") or ""
            a["ini"] += _num(c.get("saldo_inicial_db")) - _num(c.get("saldo_inicial_cr"))
            a["db"] += _num(c.get("mov_debito"))
            a["cr"] += _num(c.get("mov_credito"))
    return [por[k] for k in sorted(por, key=_orden_codigo)]


def _fusionar_seccion(secciones: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    por: Dict[str, Dict[str, Any]] = {}
    for s in secciones:
        for c in (s or {}).get("cuentas", []):
            k = str(c["cuenta_codigo"])
            a = por.setdefault(k, {"codigo": k, "nombre": c.get("cuenta_nombre") or "",
                                   "tipo": c.get("cuenta_tipo") or "", "saldo": 0.0})
            a["saldo"] += _num(c.get("saldo"))
    return [por[k] for k in sorted(por, key=_orden_codigo) if abs(por[k]["saldo"]) >= 0.005]


def _fusionar_er(ers: List[Dict[str, Any]]) -> Dict[str, Any]:
    return {"ingresos": _fusionar_seccion([e.get("ingresos") for e in ers]),
            "gastos": _fusionar_seccion([e.get("gastos") for e in ers])}


def _fusionar_bg(bgs: List[Dict[str, Any]]) -> Dict[str, Any]:
    return {"activos": _fusionar_seccion([b.get("activos") for b in bgs]),
            "pasivos": _fusionar_seccion([b.get("pasivos") for b in bgs]),
            "patrimonio": _fusionar_seccion([b.get("patrimonio") for b in bgs]),
            "utilidad": round(sum(_num(b.get("utilidad_ejercicio")) for b in bgs), 2)}


def _clave_nivel(codigo, n: Optional[int]) -> str:
    c = str(codigo or "")
    return c[:n] if n and c.isdigit() and len(c) > n else c


def agregar_por_nivel(filas: List[Dict[str, Any]], nivel: Optional[str],
                      campos: Tuple[str, ...], nombres: Optional[Dict[str, str]] = None) -> List[Dict[str, Any]]:
    """Agrupa cuentas por prefijo PUC (clase=1 dígito, grupo=2, cuenta=4,
    subcuenta=6). Sin nivel → tal cual. Códigos no numéricos no se agrupan.
    `nombres` (plan de cuentas + PUC) bautiza los prefijos: "11" → DISPONIBLE."""
    n = NIVELES_PUC.get(nivel or "")
    if not n:
        return filas
    propios = {f["codigo"]: f["nombre"] for f in filas}
    nombres = nombres or {}
    out: Dict[str, Dict[str, Any]] = {}
    for f in filas:
        k = _clave_nivel(f["codigo"], n)
        if k not in out:
            if k in propios:
                nombre = propios[k]
            elif k in nombres:
                nombre = nombres[k]
            elif n == 1 and k in CLASES_PUC:
                nombre = CLASES_PUC[k]
            else:
                nombre = f"{'Grupo' if n == 2 else 'Cuenta'} {k}"
            out[k] = {"codigo": k, "nombre": nombre, "tipo": f.get("tipo"), **{c: 0.0 for c in campos}}
        for c in campos:
            out[k][c] += f[c]
    return [out[k] for k in sorted(out, key=_orden_codigo)]


# ══ Recolección (único punto con BD) ═════════════════════════════════════

def _identidad_empresas() -> Dict[int, Dict[str, str]]:
    """portafolio → {nombre visible en Control Tower, NIT}. El NIT vive en
    resource_ids (etiqueta NIT) de la entidad vinculada (D-134-06). Sin CT el
    libro sale igual: nombre interno y NIT en blanco."""
    from fin_sys_core.db_pool import get_conn, put_conn
    try:
        conn = get_conn()
    except Exception:
        return {}
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT e.portfolio_id, e.name,
                   (SELECT r.value FROM resource_ids r
                     WHERE r.entity_id = e.id AND upper(btrim(r.label)) = 'NIT'
                     ORDER BY r.id LIMIT 1) AS nit
              FROM entities e
             WHERE e.portfolio_id IS NOT NULL
             ORDER BY e.id
        """)
        out: Dict[int, Dict[str, str]] = {}
        for pid, nombre, nit in cur.fetchall():
            a = out.setdefault(int(pid), {"nombre": (nombre or "").strip(), "nit": ""})
            if not a["nit"] and nit:
                a["nit"] = str(nit).strip()
        cur.close()
        return out
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        return {}
    finally:
        put_conn(conn)


def _nombres_puc() -> Dict[str, str]:
    try:
        from shared.puc_estandar import PUC_ACCOUNTS
    except Exception:
        return {}
    return {str(c[0]): str(c[1]) for c in PUC_ACCOUNTS}


def _nombres_cuenta(codigos: List[str], portfolio_id: Optional[int]) -> Dict[str, str]:
    """El asiento guarda el nombre de la REGLA que lo emitió ("Crear CXC" en la
    130505); el libro muestra el de la cuenta (D-134-09): primero el plan de
    cuentas de la empresa, luego el PUC estándar; si ninguno, el del asiento."""
    return {**_nombres_puc(), **_nombres_oficiales(codigos, portfolio_id)}


def _nombres_oficiales(codigos: List[str], portfolio_id: Optional[int]) -> Dict[str, str]:
    """código → nombre en chart_of_accounts (prefiere el plan de la empresa)."""
    if not codigos:
        return {}
    from fin_sys_core.db_pool import get_conn, put_conn
    try:
        conn = get_conn()
    except Exception:
        return {}
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT DISTINCT ON (code) code, name
              FROM chart_of_accounts
             WHERE code = ANY(%s) AND COALESCE(btrim(name), '') <> ''
             ORDER BY code, (portfolio_id = %s) DESC NULLS LAST, id
        """, (list(codigos), portfolio_id))
        out = {str(c): str(n).strip() for c, n in cur.fetchall()}
        cur.close()
        return out
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        return {}
    finally:
        put_conn(conn)


def recolectar(r: Dict[str, Any]) -> Dict[str, Any]:
    from database_driver import listar_cartera, obtener_portafolios, obtener_transacciones
    from kernel import kernel_reports as kr
    from kernel.kernel_journal_workflow import obtener_asientos_agrupados

    todas = {int(p["id"]): p["name"] for p in (obtener_portafolios() or [])}
    if not todas:
        raise RuntimeError("No pude leer las empresas (portafolios) de la base de datos.")
    for pid in r["portfolios"]:
        if pid not in todas:
            raise ValueError(f"La empresa {pid} no existe.")

    ident = _identidad_empresas()
    alias = {todas[pid]: v["nombre"] for pid, v in ident.items() if pid in todas and v.get("nombre")}
    empresas = [{"id": pid, "portafolio": todas[pid],
                 "nombre": ident.get(pid, {}).get("nombre") or todas[pid],
                 "nit": ident.get(pid, {}).get("nit") or ""} for pid in r["portfolios"]]
    nombres_sel = {todas[pid] for pid in r["portfolios"]}

    txs_todas = _sin_duplicados(obtener_transacciones(None))
    datos: Dict[str, Any] = {"empresas": empresas, "alias": alias, "advertencias_bd": []}

    if r["modo"] == "transacciones":
        sel = set(r["tx_ids"])
        elegidas = [t for t in txs_todas if t.get("id") in sel]
        if nombres_sel:
            fuera = sorted(t["id"] for t in elegidas if t.get("portfolio_name") not in nombres_sel)
            if fuera:
                raise ValueError("Estas transacciones no pertenecen a las empresas elegidas: "
                                 + ", ".join(f"#{i}" for i in fuera) + ".")
        if not elegidas:
            raise ValueError("Ninguna de las transacciones elegidas existe.")
        d = obtener_asientos_agrupados(estado="TODOS", limit=LIMITE_ASIENTOS, offset=0)
        asientos = [g for g in d["items"] if g.get("tx_id") in sel]
        datos.update(
            txs=elegidas,
            asientos=asientos,
            faltantes=sorted(sel - {t.get("id") for t in elegidas}),
            truncado=d["total"] > len(d["items"]),
            nombres_cuenta=_nombres_cuenta(
                sorted({str(ln.get("cuenta_codigo")) for g in asientos for ln in g.get("lineas") or []}),
                r["portfolios"][0] if len(r["portfolios"]) == 1 else None),
        )
        return datos

    txs = [t for t in txs_todas if not nombres_sel or t.get("portfolio_name") in nombres_sel]
    txs = [t for t in txs
           if (f := _a_fecha(t.get("transaction_date"))) is not None
           and (r["desde"] is None or f >= r["desde"]) and f <= r["hasta"]]

    pids = r["portfolios"] or [None]
    desde_s = r["desde"].isoformat() if r["desde"] else None
    hasta_s = r["hasta"].isoformat()
    bps = [kr.balance_prueba(pid, desde_s, hasta_s) for pid in pids]
    ers = [kr.estado_resultados(pid, desde_s, hasta_s) for pid in pids]
    bgs = [kr.balance_general(pid, hasta_s) for pid in pids]

    asientos, truncado = [], False
    for pid in pids:
        d = obtener_asientos_agrupados(estado="TODOS", portfolio_id=pid, fecha_desde=desde_s,
                                       fecha_hasta=hasta_s, limit=LIMITE_ASIENTOS, offset=0)
        asientos += d["items"]
        truncado = truncado or d["total"] > len(d["items"])

    cartera: List[Dict[str, Any]] = []
    if "cartera" in r["hojas"]:
        if nombres_sel:
            for nombre in sorted(nombres_sel):
                cartera += listar_cartera(nombre) or []
        else:
            cartera = listar_cartera(None) or []

    bp = _fusionar_bp(bps)
    datos.update(txs=txs, asientos=asientos, truncado=truncado, cartera=cartera,
                 bp=bp, er=_fusionar_er(ers), bg=_fusionar_bg(bgs),
                 nombres_cuenta=_nombres_cuenta([c["codigo"] for c in bp],
                                                   r["portfolios"][0] if len(r["portfolios"]) == 1 else None))
    return datos


# ══ Construcción del libro (pura) ═════════════════════════════════════════

def _poner(c, v, tipo: str) -> None:
    if v is None:
        return
    if tipo == "num":
        c.value = round(_num(v), 2) if not isinstance(v, str) else v
        c.number_format = FMT_NUM
    elif tipo == "int":
        c.value = v if isinstance(v, str) else int(v)
        c.number_format = FMT_INT
    elif tipo == "fecha":
        c.value = v
        c.number_format = FMT_FECHA
    elif tipo == "link":
        texto, url = v
        c.value = texto
        if url:
            c.hyperlink = url
            c.font = _F_LINK
    else:
        c.value = str(v)
        if c.value.startswith("="):
            c.data_type = "s"   # un concepto que empiece por "=" jamás se vuelve fórmula


class _Libro:
    def __init__(self, r: Dict[str, Any], datos: Dict[str, Any]):
        self.r = r
        self.datos = datos
        self.wb = Workbook()
        self.wb.calculation = CalcProperties(fullCalcOnLoad=True)
        self.wb.properties.creator = "FIN-SYS OS"
        self.catalogo = HOJAS_PERIODO if r["modo"] == "periodo" else HOJAS_TRANSACCIONES
        self.caratula = self.wb.active
        self.caratula.title = self.catalogo["caratula"]
        self.advertencias: List[str] = []
        self.control: Dict[str, Any] = {}
        multi = r["modo"] == "transacciones" or len(r["portfolios"]) != 1
        self.con_empresa = multi

    def hoja(self, clave: str):
        return self.wb.create_sheet(self.catalogo[clave])

    def alias(self, portafolio: Optional[str]) -> str:
        p = portafolio or ""
        return self.datos.get("alias", {}).get(p, p)

    def subtitulo(self) -> str:
        r = self.r
        if r["modo"] == "transacciones":
            return f"{self.empresas_txt()} · {len(self.datos.get('txs', []))} transacciones elegidas"
        desde = r["desde"].strftime("%d/%m/%Y") if r["desde"] else "desde el inicio"
        return f"{self.empresas_txt()} · {desde} – {r['hasta'].strftime('%d/%m/%Y')}"

    def empresas_txt(self) -> str:
        emp = self.datos.get("empresas") or []
        if emp:
            return ", ".join(e["nombre"] for e in emp)
        if self.r["modo"] == "transacciones":
            nombres = sorted({self.alias(t.get("portfolio_name")) for t in self.datos.get("txs", [])})
            return ", ".join(nombres) or "—"
        return "Todas las empresas (consolidado)"


def _titulo(ws, titulo: str, sub: str) -> int:
    ws["A1"] = titulo
    ws["A1"].font = _F_TITULO
    ws["A2"] = sub
    ws["A2"].font = _F_SUB
    return 4


def _tabla(ws, fila: int, columnas: List[Tuple[str, str, str]], filas: List[Dict[str, Any]],
           totales: Tuple[str, ...] = (), etiqueta_total: str = "TOTAL",
           vacio: str = "Sin datos en el alcance elegido.") -> Dict[str, Any]:
    """Encabezado negro + filas + fila de totales con =SUM reales.
    columnas: [(título, clave, tipo)] con tipo en txt|num|int|fecha|link.
    Un valor puede ser una función (fila, letras) → fórmula, para cálculos por fila."""
    letras: Dict[str, str] = {}
    for j, (titulo, clave, _tipo) in enumerate(columnas, start=1):
        c = ws.cell(row=fila, column=j, value=titulo)
        c.font, c.fill, c.border = _F_ENC, _NEGRO, _BORDE
        c.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        letras[clave] = get_column_letter(j)
    r = fila
    for f in filas:
        r += 1
        for j, (_t, clave, tipo) in enumerate(columnas, start=1):
            c = ws.cell(row=r, column=j)
            v = f.get(clave)
            if callable(v):
                c.value = v(r, letras)
                c.number_format = FMT_NUM
            else:
                _poner(c, v, tipo)
            c.border = _BORDE
    ini, fin = fila + 1, r
    if not filas:
        r += 1
        ws.cell(row=r, column=1, value=vacio).font = _F_NOTA
    total = None
    if totales:
        r += 1
        total = r
        for j, (_t, clave, tipo) in enumerate(columnas, start=1):
            c = ws.cell(row=r, column=j)
            c.border, c.fill = _BORDE, _PAPEL
            if clave in totales:
                L = letras[clave]
                c.value = f"=SUM({L}{ini}:{L}{fin})" if filas else 0
                c.number_format = FMT_INT if tipo == "int" else FMT_NUM
                c.font = _F_NEGRITA
        c0 = ws.cell(row=r, column=1)
        c0.value, c0.font = etiqueta_total, _F_NEGRITA
    return {"enc": fila, "ini": ini, "fin": fin, "total": total, "letras": letras,
            "ultima": r, "n": len(filas)}


def _cuadre(ws, fila: int, col_etiqueta: int, a: str, b: str, ok: str, mal: str) -> None:
    """Fila de verificación: texto ✔/✘ + diferencia numérica (sin TEXT(), que
    depende del idioma de Excel)."""
    ws.cell(row=fila, column=col_etiqueta, value="VERIFICACIÓN").font = _F_NEGRITA
    c = ws.cell(row=fila, column=col_etiqueta + 1, value=f'=IF(ROUND({a}-{b},2)=0,"{ok}","{mal}")')
    c.font = _F_NEGRITA
    d = ws.cell(row=fila, column=col_etiqueta + 2, value=f"={a}-{b}")
    d.number_format = FMT_NUM


def _rematar(ws, enc: Optional[int] = None, filtro: Optional[str] = None) -> None:
    anchos: Dict[int, int] = {}
    for fila in ws.iter_rows(min_row=3):
        for c in fila:
            if c.value is None:
                continue
            v = c.value
            largo = 12 if isinstance(v, str) and v.startswith("=") and c.data_type == "f" else len(str(v))
            if isinstance(v, (int, float)):
                largo = len(f"{v:,.2f}") + 2
            elif isinstance(v, date):
                largo = 11
            anchos[c.column] = max(anchos.get(c.column, 0), largo)
    for col, ancho in anchos.items():
        ws.column_dimensions[get_column_letter(col)].width = max(9, min(55, ancho + 2))
    if enc:
        ws.freeze_panes = f"A{enc + 1}"
        ws.print_title_rows = f"{enc}:{enc}"
    if filtro:
        ws.auto_filter.ref = filtro
    ws.page_setup.orientation = "landscape"
    ws.page_setup.fitToWidth = 1
    ws.page_setup.fitToHeight = 0
    ws.sheet_properties.pageSetUpPr.fitToPage = True


# ── Hojas ────────────────────────────────────────────────────────────────

def _lineas_diario(lib: _Libro, asientos: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    filas = []
    for g in asientos:
        if (g.get("estado") or "").upper() not in EN_LIBROS:
            continue
        tx = g.get("tx") or {}
        for ln in g.get("lineas") or []:
            filas.append({
                "fecha": _a_fecha(g.get("fecha")), "asiento": g.get("entry_group_id") or "",
                "estado": g.get("estado") or "", "empresa": lib.alias(g.get("portfolio_name")),
                "referencia": g.get("referencia") or "", "descripcion": g.get("descripcion") or "",
                "codigo": str(ln.get("cuenta_codigo") or ""), "cuenta": ln.get("cuenta_nombre") or "",
                "debito": _num(ln.get("debito")), "credito": _num(ln.get("credito")),
                "tercero": tx.get("tercero") or "", "tx": g.get("tx_id"),
                "_orden": (ln.get("linea") or 0, ln.get("id") or 0),
            })
    filas.sort(key=lambda f: (f["fecha"] or date.min, f["asiento"], f["_orden"]))
    return filas


def _hoja_diario(lib: _Libro, clave: str, titulo: str) -> None:
    ws = lib.hoja(clave)
    fila = _titulo(ws, titulo, lib.subtitulo() + " · asientos en libros (contabilizados y anulados con su espejo)")
    lineas = lib.control["lineas"]
    cols = [("Fecha", "fecha", "fecha"), ("Asiento", "asiento", "txt"), ("Estado", "estado", "txt")]
    if lib.con_empresa:
        cols.append(("Empresa", "empresa", "txt"))
    cols += [("Referencia", "referencia", "txt"), ("Descripción", "descripcion", "txt"),
             ("Código", "codigo", "txt"), ("Cuenta", "cuenta", "txt"),
             ("Débito", "debito", "num"), ("Crédito", "credito", "num"),
             ("Tercero", "tercero", "txt"), ("TX", "tx", "int")]
    t = _tabla(ws, fila, cols, lineas, totales=("debito", "credito"),
               vacio="Sin asientos en libros en el alcance elegido.")
    L = t["letras"]
    _cuadre(ws, t["total"] + 1, cols.index(("Débito", "debito", "num")),
            f"{L['debito']}{t['total']}", f"{L['credito']}{t['total']}",
            "✔ Débitos = Créditos", "✘ No cuadra")
    _rematar(ws, t["enc"], f"A{t['enc']}:{get_column_letter(len(cols))}{max(t['fin'], t['enc'])}")


def _hoja_mayor(lib: _Libro) -> None:
    ws = lib.hoja("mayor")
    fila = _titulo(ws, "MAYOR", lib.subtitulo() + " · saldo = débitos − créditos")
    prefijos = lib.r["filtros"]["cuentas_puc"]
    cuentas = [c for c in lib.datos.get("bp", [])
               if not prefijos or any(c["codigo"].startswith(p) for p in prefijos)]
    por_cta: Dict[str, List[Dict[str, Any]]] = {}
    for ln in lib.control["lineas"]:
        por_cta.setdefault(ln["codigo"], []).append(ln)
    if prefijos:
        ws.cell(row=3, column=1, value=f"Solo cuentas que empiezan por: {', '.join(prefijos)}").font = _F_NOTA
    if not cuentas:
        ws.cell(row=fila, column=1, value="Sin cuentas con saldo o movimiento en el alcance elegido.").font = _F_NOTA
    descuadres = []
    for c in cuentas:
        cab = ws.cell(row=fila, column=1, value=f"{c['codigo']} · {c['nombre']}")
        cab.font, cab.fill = _F_NEGRITA, _PAPEL
        fila += 1
        ws.cell(row=fila, column=5, value="Saldo anterior").font = _F_NEGRITA
        _poner(ws.cell(row=fila, column=6), c["ini"], "num")
        anterior = f"F{fila}"
        fila += 1
        for j, enc in enumerate(("Fecha", "Asiento", "Descripción", "Débito", "Crédito", "Saldo"), start=1):
            e = ws.cell(row=fila, column=j, value=enc)
            e.font, e.fill, e.border = _F_ENC, _NEGRO, _BORDE
        enc_fila = fila
        movs = por_cta.get(c["codigo"], [])
        sd = sc = 0.0
        for m in movs:
            fila += 1
            _poner(ws.cell(row=fila, column=1), m["fecha"], "fecha")
            _poner(ws.cell(row=fila, column=2), m["asiento"], "txt")
            _poner(ws.cell(row=fila, column=3), m["descripcion"], "txt")
            _poner(ws.cell(row=fila, column=4), m["debito"], "num")
            _poner(ws.cell(row=fila, column=5), m["credito"], "num")
            s = ws.cell(row=fila, column=6, value=f"={anterior}+D{fila}-E{fila}")
            s.number_format = FMT_NUM
            anterior = f"F{fila}"
            sd += m["debito"]
            sc += m["credito"]
        fila += 1
        ws.cell(row=fila, column=3, value="Totales y saldo final" if movs else "Sin movimientos en el período").font = _F_NEGRITA
        for col, L in ((4, "D"), (5, "E")):
            t = ws.cell(row=fila, column=col, value=f"=SUM({L}{enc_fila + 1}:{L}{fila - 1})" if movs else 0)
            t.number_format, t.font = FMT_NUM, _F_NEGRITA
        f = ws.cell(row=fila, column=6, value=f"={anterior}")
        f.number_format, f.font = FMT_NUM, _F_NEGRITA
        if abs((c["ini"] + sd - sc) - (c["ini"] + c["db"] - c["cr"])) >= 0.01:
            descuadres.append(c["codigo"])
        fila += 2
    if descuadres:
        lib.advertencias.append("El Mayor no coincide con el balance de prueba en las cuentas "
                                f"{', '.join(descuadres)} — revisar antes de entregar.")
    _rematar(ws)


def _filas_bp(lib: _Libro) -> List[Dict[str, Any]]:
    filas = agregar_por_nivel(lib.datos.get("bp", []), lib.r["nivel_puc"], ("ini", "db", "cr"), lib.datos.get("nombres_cuenta"))
    out = []
    for f in filas:
        fin = f["ini"] + f["db"] - f["cr"]
        out.append({"codigo": f["codigo"], "nombre": f["nombre"], "tipo": f.get("tipo") or "",
                    "si_db": max(f["ini"], 0), "si_cr": max(-f["ini"], 0),
                    "db": f["db"], "cr": f["cr"], "sf_db": max(fin, 0), "sf_cr": max(-fin, 0)})
    return out


def _hoja_balance_prueba(lib: _Libro) -> None:
    ws = lib.hoja("balance_prueba")
    nivel = f" · nivel PUC: {lib.r['nivel_puc']}" if lib.r["nivel_puc"] else ""
    fila = _titulo(ws, "BALANCE DE PRUEBA", lib.subtitulo() + nivel)
    cols = [("Código", "codigo", "txt"), ("Cuenta", "nombre", "txt"), ("Tipo", "tipo", "txt"),
            ("Saldo anterior débito", "si_db", "num"), ("Saldo anterior crédito", "si_cr", "num"),
            ("Movimiento débito", "db", "num"), ("Movimiento crédito", "cr", "num"),
            ("Saldo final débito", "sf_db", "num"), ("Saldo final crédito", "sf_cr", "num")]
    t = _tabla(ws, fila, cols, _filas_bp(lib), totales=("si_db", "si_cr", "db", "cr", "sf_db", "sf_cr"),
               vacio="Sin cuentas con saldo o movimiento en el alcance elegido.")
    L, tot = t["letras"], t["total"]
    _cuadre(ws, tot + 1, 5, f"{L['db']}{tot}", f"{L['cr']}{tot}", "✔ Movimientos cuadran", "✘ Movimientos no cuadran")
    _cuadre(ws, tot + 2, 5, f"{L['sf_db']}{tot}", f"{L['sf_cr']}{tot}", "✔ Saldos cuadran", "✘ Saldos no cuadran")
    _rematar(ws, t["enc"], f"A{t['enc']}:I{max(t['fin'], t['enc'])}")


def _seccion(ws, fila: int, titulo: str, filas: List[Dict[str, Any]], etiqueta_total: str) -> Tuple[int, int]:
    """Bloque de estado financiero: título + cuentas + total =SUM. → (fila_total, siguiente)"""
    ws.cell(row=fila, column=1, value=titulo).font = _F_NEGRITA
    ini = fila + 1
    r = fila
    for f in filas:
        r += 1
        _poner(ws.cell(row=r, column=1), f["codigo"], "txt")
        _poner(ws.cell(row=r, column=2), f["nombre"], "txt")
        _poner(ws.cell(row=r, column=3), f["saldo"], "num")
    if not filas:
        r += 1
        ws.cell(row=r, column=2, value="(sin saldo)").font = _F_NOTA
    r += 1
    ws.cell(row=r, column=2, value=etiqueta_total).font = _F_NEGRITA
    c = ws.cell(row=r, column=3, value=f"=SUM(C{ini}:C{r - 1})" if filas else 0)
    c.number_format, c.font, c.fill = FMT_NUM, _F_NEGRITA, _PAPEL
    return r, r + 2


def _hoja_estado_resultados(lib: _Libro) -> None:
    ws = lib.hoja("estado_resultados")
    fila = _titulo(ws, "ESTADO DE RESULTADOS", lib.subtitulo())
    er, nivel = lib.datos.get("er", {}), lib.r["nivel_puc"]
    ing = agregar_por_nivel(er.get("ingresos", []), nivel, ("saldo",), lib.datos.get("nombres_cuenta"))
    gas = agregar_por_nivel(er.get("gastos", []), nivel, ("saldo",), lib.datos.get("nombres_cuenta"))
    t_ing, fila = _seccion(ws, fila, "INGRESOS", ing, "TOTAL INGRESOS")
    t_gas, fila = _seccion(ws, fila, "GASTOS", gas, "TOTAL GASTOS")
    ws.cell(row=fila, column=2, value="UTILIDAD (PÉRDIDA) DEL PERÍODO").font = _F_NEGRITA
    u = ws.cell(row=fila, column=3, value=f"=C{t_ing}-C{t_gas}")
    u.number_format, u.font, u.fill = FMT_NUM, _F_NEGRITA, _PAPEL
    _rematar(ws)


def _hoja_balance_general(lib: _Libro) -> None:
    ws = lib.hoja("balance_general")
    corte = lib.r["hasta"].strftime("%d/%m/%Y")
    fila = _titulo(ws, "BALANCE GENERAL", f"{lib.empresas_txt()} · a {corte}")
    bg, nivel = lib.datos.get("bg", {}), lib.r["nivel_puc"]
    t_act, fila = _seccion(ws, fila, "ACTIVO", agregar_por_nivel(bg.get("activos", []), nivel, ("saldo",), lib.datos.get("nombres_cuenta")), "TOTAL ACTIVO")
    t_pas, fila = _seccion(ws, fila, "PASIVO", agregar_por_nivel(bg.get("pasivos", []), nivel, ("saldo",), lib.datos.get("nombres_cuenta")), "TOTAL PASIVO")
    t_pat, fila = _seccion(ws, fila, "PATRIMONIO", agregar_por_nivel(bg.get("patrimonio", []), nivel, ("saldo",), lib.datos.get("nombres_cuenta")), "TOTAL PATRIMONIO")
    ws.cell(row=fila, column=2, value="Utilidad acumulada del ejercicio (sin asiento de cierre)")
    _poner(ws.cell(row=fila, column=3), bg.get("utilidad", 0), "num")
    t_util = fila
    fila += 1
    ws.cell(row=fila, column=2, value="TOTAL PASIVO + PATRIMONIO + UTILIDAD").font = _F_NEGRITA
    tot = ws.cell(row=fila, column=3, value=f"=C{t_pas}+C{t_pat}+C{t_util}")
    tot.number_format, tot.font, tot.fill = FMT_NUM, _F_NEGRITA, _PAPEL
    _cuadre(ws, fila + 2, 1, f"C{t_act}", f"C{fila}", "✔ Activo = Pasivo + Patrimonio", "✘ La ecuación no cuadra")
    _rematar(ws)


def _fila_tx(lib: _Libro, t: Dict[str, Any]) -> Dict[str, Any]:
    tipo = _texto(t.get("type")).upper()
    neto = _num(t.get("net_value"))
    ident = " ".join(x for x in (_texto(t.get("identification_type")), _texto(t.get("identification_number"))) if x)
    return {
        "id": t.get("id"), "fecha": _a_fecha(t.get("transaction_date")),
        "empresa": lib.alias(t.get("portfolio_name")), "tipo": tipo,
        "concepto": _texto(t.get("concept")), "categoria": _texto(t.get("category")) or "(sin categoría)",
        "tercero": _texto(t.get("third_party_name")) or "(sin tercero)", "identificacion": ident,
        "cuenta": _texto(t.get("account_name")) or "(sin cuenta)", "destino": _texto(t.get("dest_account_name")),
        "metodo": _texto(t.get("payment_method")), "monto": _num(t.get("amount")),
        "iva": _num(t.get("tax_iva_amount")), "gmf": _num(t.get("tax_gmf_amount")),
        "ingreso": neto if tipo == "INGRESO" else None, "gasto": neto if tipo == "GASTO" else None,
        "transferencia": neto if tipo == "TRANSFERENCIA" else None,
        "trm": _num(t.get("trm")) or None, "soportes": len(_soportes(t)),
        "etiquetas": _texto(t.get("tags")), "_moneda": _moneda(t),
    }


def _hoja_movimientos(lib: _Libro, clave: str, titulo: str, txs: List[Dict[str, Any]]) -> None:
    ws = lib.hoja(clave)
    fila = _titulo(ws, titulo, lib.subtitulo())
    filas = sorted((_fila_tx(lib, t) for t in txs), key=lambda f: (f["fecha"] or date.min, f["id"] or 0))
    monedas = sorted({f["_moneda"] for f in filas}, key=lambda m: (m != "COP", m)) or ["COP"]
    primera = None
    for moneda in monedas:
        bloque = [f for f in filas if f["_moneda"] == moneda]
        if len(monedas) > 1:
            aviso = "" if moneda == "COP" else " — NO se suman al COP"
            ws.cell(row=fila, column=1, value=f"MOVIMIENTOS EN {moneda}{aviso}").font = _F_NEGRITA
            fila += 1
        cols = [("ID", "id", "int"), ("Fecha", "fecha", "fecha")]
        if lib.con_empresa:
            cols.append(("Empresa", "empresa", "txt"))
        cols += [("Tipo", "tipo", "txt"), ("Concepto", "concepto", "txt"), ("Categoría", "categoria", "txt"),
                 ("Tercero", "tercero", "txt"), ("Identificación", "identificacion", "txt"),
                 ("Cuenta", "cuenta", "txt"), ("Cuenta destino", "destino", "txt"),
                 ("Método de pago", "metodo", "txt"), ("Monto bruto", "monto", "num"),
                 ("IVA", "iva", "num"), ("GMF", "gmf", "num"), ("Ingreso (neto)", "ingreso", "num"),
                 ("Gasto (neto)", "gasto", "num"), ("Transferencia (neto)", "transferencia", "num")]
        if moneda != "COP":
            cols.append(("TRM", "trm", "num"))
        cols += [("Soportes", "soportes", "int"), ("Etiquetas", "etiquetas", "txt")]
        t = _tabla(ws, fila, cols, bloque, totales=("iva", "gmf", "ingreso", "gasto", "transferencia"),
                   etiqueta_total=f"TOTAL {moneda}", vacio="Sin movimientos en el alcance elegido.")
        L = t["letras"]
        n = ws.cell(row=t["total"] + 1, column=cols.index(("Gasto (neto)", "gasto", "num")),
                    value="Neto (ingresos − gastos)")
        n.font = _F_NEGRITA
        v = ws.cell(row=t["total"] + 1, column=cols.index(("Gasto (neto)", "gasto", "num")) + 1,
                    value=f"={L['ingreso']}{t['total']}-{L['gasto']}{t['total']}")
        v.number_format, v.font = FMT_NUM, _F_NEGRITA
        if primera is None:
            primera = (t["enc"], f"A{t['enc']}:{get_column_letter(len(cols))}{max(t['fin'], t['enc'])}")
        fila = t["total"] + 3
    _rematar(ws, *primera)


def _grupos_tercero(lib: _Libro, txs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    por: Dict[Any, Dict[str, Any]] = {}
    for t in txs:
        if _moneda(t) != "COP":
            continue
        nombre = _texto(t.get("third_party_name")) or "(sin tercero)"
        k = t.get("third_party_id") or ("nombre", nombre.lower())
        ident = " ".join(x for x in (_texto(t.get("identification_type")), _texto(t.get("identification_number"))) if x)
        a = por.setdefault(k, {"tercero": nombre, "identificacion": ident, "n": 0, "ingresos": 0.0, "gastos": 0.0})
        a["n"] += 1
        tipo = _texto(t.get("type")).upper()
        if tipo == "INGRESO":
            a["ingresos"] += _num(t.get("net_value"))
        elif tipo == "GASTO":
            a["gastos"] += _num(t.get("net_value"))
    filas = sorted(por.values(), key=lambda a: a["tercero"].lower())
    for a in filas:
        a["neto"] = lambda r, L: f"={L['ingresos']}{r}-{L['gastos']}{r}"
    return filas


_COLS_TERCERO = [("Tercero", "tercero", "txt"), ("Identificación", "identificacion", "txt"),
                 ("Nº de transacciones", "n", "int"), ("Ingresos", "ingresos", "num"),
                 ("Gastos", "gastos", "num"), ("Neto", "neto", "num")]


def _nota_otras_monedas(ws, fila: int, txs: List[Dict[str, Any]]) -> int:
    otras = sum(1 for t in txs if _moneda(t) != "COP")
    if otras:
        ws.cell(row=fila, column=1, value=f"Solo COP. {otras} transacción(es) en otra moneda no se suman "
                                          "(están en la hoja de movimientos).").font = _F_NOTA
        return fila + 1
    return fila


def _hoja_auxiliar(lib: _Libro, txs: List[Dict[str, Any]]) -> None:
    ws = lib.hoja("auxiliar_tercero")
    fila = _titulo(ws, "AUXILIAR POR TERCERO", lib.subtitulo())
    fila = _nota_otras_monedas(ws, fila - 1, txs) + 1
    t = _tabla(ws, fila, _COLS_TERCERO, _grupos_tercero(lib, txs),
               totales=("n", "ingresos", "gastos", "neto"), vacio="Sin movimientos en COP en el alcance elegido.")
    _rematar(ws, t["enc"], f"A{t['enc']}:F{max(t['fin'], t['enc'])}")


_BUCKETS = (("corriente", "Corriente", None, 0), ("d30", "1–30 días", 1, 30), ("d60", "31–60 días", 31, 60),
            ("d90", "61–90 días", 61, 90), ("d90p", "Más de 90 días", 91, None))


def _hoja_cartera(lib: _Libro) -> None:
    ws = lib.hoja("cartera")
    corte = lib.r["hasta"]
    fila = _titulo(ws, "CARTERA POR EDADES", f"{lib.empresas_txt()} · edades al {corte.strftime('%d/%m/%Y')} · "
                                             "saldos pendientes actuales (no reconstruye saldos históricos)")
    terceros = set(lib.r["filtros"]["terceros"])
    vivas = []
    for c in lib.datos.get("cartera", []):
        if _num(c.get("remaining_balance")) <= 0:
            continue
        f_tx = _a_fecha(c.get("transaction_date"))
        if f_tx and f_tx > corte:
            continue
        if terceros and c.get("third_party_id") not in terceros:
            continue
        vence = _a_fecha(c.get("due_date"))
        dias = (corte - vence).days if vence else 0
        fila_c = {"tercero": _texto(c.get("third_party_name")) or "(sin tercero)",
                  "identificacion": _texto(c.get("identification_number")), "concepto": _texto(c.get("concept")),
                  "vence": vence, "dias": max(dias, 0), "original": _num(c.get("original_amount")),
                  "saldo": _num(c.get("remaining_balance")), "_tipo": _texto(c.get("type")).upper()}
        for k, _e, desde, hasta in _BUCKETS:
            dentro = (dias <= 0) if desde is None else (dias >= desde and (hasta is None or dias <= hasta))
            fila_c[k] = fila_c["saldo"] if dentro else None
        vivas.append(fila_c)
    cols = [("Tercero", "tercero", "txt"), ("Identificación", "identificacion", "txt"),
            ("Concepto", "concepto", "txt"), ("Vencimiento", "vence", "fecha"), ("Días vencido", "dias", "int"),
            ("Valor original", "original", "num"), ("Saldo", "saldo", "num")] + \
           [(e, k, "num") for k, e, _d, _h in _BUCKETS]
    enc = None
    for tipo, nombre in (("CXC", "CUENTAS POR COBRAR"), ("CXP", "CUENTAS POR PAGAR")):
        ws.cell(row=fila, column=1, value=nombre).font = _F_NEGRITA
        bloque = sorted((v for v in vivas if v["_tipo"] == tipo), key=lambda v: (v["vence"] or date.min))
        t = _tabla(ws, fila + 1, cols, bloque, totales=("original", "saldo") + tuple(k for k, *_ in _BUCKETS),
                   etiqueta_total=f"TOTAL {tipo}", vacio="Sin saldos pendientes.")
        enc = enc or t["enc"]
        fila = t["total"] + 3
    _rematar(ws, enc)


def _hoja_impuestos(lib: _Libro, txs: List[Dict[str, Any]]) -> None:
    ws = lib.hoja("impuestos")
    fila = _titulo(ws, "IMPUESTOS", lib.subtitulo() + " · IVA y GMF registrados en las transacciones")
    fila = _nota_otras_monedas(ws, fila - 1, txs) + 1
    por: Dict[str, Dict[str, Any]] = {}
    for t in txs:
        if _moneda(t) != "COP":
            continue
        f = _a_fecha(t.get("transaction_date"))
        mes = f.strftime("%Y-%m") if f else "(sin fecha)"
        a = por.setdefault(mes, {"mes": mes, "iva_ing": 0.0, "iva_gas": 0.0, "gmf": 0.0})
        tipo = _texto(t.get("type")).upper()
        if tipo == "INGRESO":
            a["iva_ing"] += _num(t.get("tax_iva_amount"))
        elif tipo == "GASTO":
            a["iva_gas"] += _num(t.get("tax_iva_amount"))
        a["gmf"] += _num(t.get("tax_gmf_amount"))
    filas = [por[k] for k in sorted(por)]
    for a in filas:
        a["iva_neto"] = lambda r, L: f"={L['iva_ing']}{r}-{L['iva_gas']}{r}"
    cols = [("Mes", "mes", "txt"), ("IVA en ingresos (generado)", "iva_ing", "num"),
            ("IVA en gastos (descontable)", "iva_gas", "num"), ("IVA neto", "iva_neto", "num"),
            ("GMF (4×1000)", "gmf", "num")]
    t = _tabla(ws, fila, cols, filas, totales=("iva_ing", "iva_gas", "iva_neto", "gmf"),
               vacio="Sin transacciones en COP en el alcance elegido.")
    _rematar(ws, t["enc"])


def _hoja_resumen(lib: _Libro, txs: List[Dict[str, Any]]) -> None:
    ws = lib.hoja("resumen")
    fila = _titulo(ws, "RESUMEN", lib.subtitulo())
    fila = _nota_otras_monedas(ws, fila - 1, txs) + 1
    por: Dict[str, Dict[str, Any]] = {}
    for t in txs:
        if _moneda(t) != "COP":
            continue
        cat = _texto(t.get("category")) or "(sin categoría)"
        a = por.setdefault(cat.lower(), {"categoria": cat, "n": 0, "ingresos": 0.0, "gastos": 0.0})
        a["n"] += 1
        tipo = _texto(t.get("type")).upper()
        if tipo == "INGRESO":
            a["ingresos"] += _num(t.get("net_value"))
        elif tipo == "GASTO":
            a["gastos"] += _num(t.get("net_value"))
    filas = sorted(por.values(), key=lambda a: a["categoria"].lower())
    for a in filas:
        a["neto"] = lambda r, L: f"={L['ingresos']}{r}-{L['gastos']}{r}"
    ws.cell(row=fila, column=1, value="POR CATEGORÍA").font = _F_NEGRITA
    t = _tabla(ws, fila + 1, [("Categoría", "categoria", "txt"), ("Nº de transacciones", "n", "int"),
                              ("Ingresos", "ingresos", "num"), ("Gastos", "gastos", "num"), ("Neto", "neto", "num")],
               filas, totales=("n", "ingresos", "gastos", "neto"))
    fila = t["total"] + 3
    ws.cell(row=fila, column=1, value="POR TERCERO").font = _F_NEGRITA
    _tabla(ws, fila + 1, _COLS_TERCERO, _grupos_tercero(lib, txs), totales=("n", "ingresos", "gastos", "neto"))
    _rematar(ws)


def _hoja_soportes(lib: _Libro, txs: List[Dict[str, Any]]) -> int:
    ws = lib.hoja("soportes")
    fila = _titulo(ws, "SOPORTES", lib.subtitulo() + " · evidencias adjuntas a cada transacción")
    filas, sin = [], 0
    for t in sorted(txs, key=lambda t: (_a_fecha(t.get("transaction_date")) or date.min, t.get("id") or 0)):
        base = {"tx": t.get("id"), "fecha": _a_fecha(t.get("transaction_date")),
                "concepto": _texto(t.get("concept")), "tercero": _texto(t.get("third_party_name"))}
        urls = _soportes(t)
        if not urls:
            sin += 1
            filas.append({**base, "soporte": "⚠ sin soporte"})
        for i, u in enumerate(urls, start=1):
            filas.append({**base, "soporte": (f"Soporte {i}", u)})
    cols = [("TX", "tx", "int"), ("Fecha", "fecha", "fecha"), ("Concepto", "concepto", "txt"),
            ("Tercero", "tercero", "txt"), ("Soporte", "soporte", "link")]
    for f in filas:
        if isinstance(f["soporte"], str):
            f["soporte"] = (f["soporte"], None)
    t = _tabla(ws, fila, cols, filas)
    for r in range(t["ini"], t["fin"] + 1):
        if ws.cell(row=r, column=5).value == "⚠ sin soporte":
            for c in range(1, 6):
                ws.cell(row=r, column=c).fill = _AMBAR
    _rematar(ws, t["enc"], f"A{t['enc']}:E{max(t['fin'], t['enc'])}")
    return sin


def _hoja_caratula(lib: _Libro, sello: Dict[str, Any]) -> None:
    ws = lib.caratula
    r = lib.r
    titulo = "FIN-SYS OS · LIBRO CONTABLE" if r["modo"] == "periodo" else "FIN-SYS OS · RELACIÓN DE TRANSACCIONES"
    _titulo(ws, titulo, "Las cifras salen del kernel contable y de las transacciones registradas en FIN-SYS; "
                        "ninguna fue calculada por una IA.")
    fila = 4

    def par(etiqueta: str, valor, tipo: str = "txt", relleno=None):
        nonlocal fila
        a = ws.cell(row=fila, column=1, value=etiqueta)
        a.font = _F_NEGRITA
        b = ws.cell(row=fila, column=2)
        _poner(b, valor, tipo)
        b.alignment = Alignment(wrap_text=True, vertical="top")
        if relleno:
            a.fill = b.fill = relleno
        fila += 1

    def seccion(nombre: str):
        nonlocal fila
        fila += 1
        c = ws.cell(row=fila, column=1, value=nombre)
        c.font, c.fill = _F_ENC, _NEGRO
        ws.cell(row=fila, column=2).fill = _NEGRO
        fila += 1

    if r["folio"]:
        par("Folio", r["folio"])
    if r["nombre"]:
        par("Nombre", r["nombre"])
    emp = lib.datos.get("empresas") or []
    if emp:
        for e in emp:
            par("Empresa", e["nombre"] + (f" (portafolio interno: {e['portafolio']})" if e["portafolio"] != e["nombre"] else ""))
            par("NIT", e["nit"] or "— (sin NIT registrado en Control Tower)")
    else:
        par("Empresas", lib.empresas_txt())
    if r["modo"] == "periodo":
        par("Período", lib.subtitulo().split(" · ")[-1])
        par("Fecha de corte", r["hasta"], "fecha")
    par("Generado", sello["generado"].replace("T", " ") + " (hora Colombia)")
    par("Generado por", sello["generado_por"] or "—")

    seccion("CONTENIDO")
    for clave in r["hojas"]:
        if clave == "caratula":
            continue
        nombre = lib.catalogo[clave]
        c = ws.cell(row=fila, column=1, value=nombre)
        c.hyperlink = Hyperlink(ref=c.coordinate, location=f"'{nombre}'!A1", display=nombre)
        c.font = _F_LINK
        fila += 1

    seccion("SELLO DE ORIGEN")
    rango = sello["rango_real"]
    rango_txt = (f" (del {rango['desde']} al {rango['hasta']})" if rango["desde"] else "")
    par("Transacciones en el alcance", f"{sello['n_txs']}{rango_txt}")
    if sello.get("n_txs_filtradas") is not None and sello["n_txs_filtradas"] != sello["n_txs"]:
        par("Transacciones tras los filtros", sello["n_txs_filtradas"], "int")
    par("Asientos en libros", f"{sello['n_asientos']} asientos · {sello['n_lineas']} líneas")
    tc = sello["totales_control"]
    par("Σ débitos", tc["debitos"], "num")
    par("Σ créditos", tc["creditos"], "num")
    par("Partida doble", "✔ Débitos = Créditos" if tc["cuadra"] else "✘ No cuadra — revisar antes de entregar",
        relleno=None if tc["cuadra"] else _AMBAR)
    if r["modo"] == "periodo":
        par("Utilidad del período", tc["utilidad_periodo"], "num")
        par("Ecuación contable al corte",
            "✔ Activo = Pasivo + Patrimonio" if tc["ecuacion_contable"]
            else f"✘ Diferencia de {tc['diferencia_bg']:,.2f}", relleno=None if tc["ecuacion_contable"] else _AMBAR)
    if lib.datos.get("nombres_cuenta"):
        par("Nombres de cuenta", "Del plan de cuentas de la empresa o, si no está, del PUC estándar. "
                                 "El asiento conserva el nombre de la regla que lo emitió.")
    otras = sello["otras_monedas"]
    if otras:
        par("Otras monedas", "; ".join(f"{m}: {n} transacción(es) — nunca sumadas al COP" for m, n in otras.items()))
    if r["modo"] == "periodo":
        f = r["filtros"]
        partes = []
        if f["categorias"]:
            partes.append("categorías: " + ", ".join(f["categorias"]))
        if f["terceros"]:
            partes.append("terceros (id): " + ", ".join(str(x) for x in f["terceros"]))
        if f["tipos"]:
            partes.append("tipos: " + ", ".join(f["tipos"]))
        if f["moneda"]:
            partes.append("moneda: " + f["moneda"])
        if f["cuentas_puc"]:
            partes.append("Mayor solo de cuentas: " + ", ".join(f["cuentas_puc"]))
        par("Filtros", ("; ".join(partes) + ". Los libros oficiales (diario, balance de prueba, estados) "
                        "no se filtran: deben cuadrar.") if partes else "Ninguno")
        if r["nivel_puc"]:
            par("Nivel de detalle PUC", r["nivel_puc"])

    if sello["advertencias"]:
        seccion("ADVERTENCIAS")
        for a in sello["advertencias"]:
            par("⚠", a, relleno=_AMBAR)
    ws.column_dimensions["A"].width = 32
    ws.column_dimensions["B"].width = 90
    ws.page_setup.fitToWidth = 1
    ws.sheet_properties.pageSetUpPr.fitToPage = True


def _con_nombres_oficiales(datos: Dict[str, Any]) -> Dict[str, Any]:
    nombres = datos.get("nombres_cuenta") or {}
    if not nombres:
        return datos

    def cuentas(filas):
        return [{**c, "nombre": nombres.get(c["codigo"], c["nombre"])} for c in filas or []]

    d = dict(datos)
    if "bp" in d:
        d["bp"] = cuentas(d["bp"])
    if "er" in d:
        d["er"] = {k: cuentas(v) for k, v in d["er"].items()}
    if "bg" in d:
        d["bg"] = {k: (cuentas(v) if isinstance(v, list) else v) for k, v in d["bg"].items()}
    d["asientos"] = [{**g, "lineas": [{**ln, "cuenta_nombre": nombres.get(str(ln.get("cuenta_codigo")),
                                                                         ln.get("cuenta_nombre"))}
                                      for ln in g.get("lineas") or []]}
                     for g in d.get("asientos", [])]
    return d


def construir_libro(datos: Dict[str, Any], r: Dict[str, Any],
                    usuario: Optional[Dict[str, Any]] = None,
                    ahora: Optional[datetime] = None) -> Tuple[bytes, Dict[str, Any]]:
    datos = _con_nombres_oficiales(datos)
    lib = _Libro(r, datos)
    txs = datos.get("txs", [])
    asientos = datos.get("asientos", [])
    lib.control["lineas"] = _lineas_diario(lib, asientos)
    en_libros = {g.get("entry_group_id") for g in asientos if (g.get("estado") or "").upper() in EN_LIBROS}
    txs_filtradas = aplicar_filtros(txs, r["filtros"]) if r["modo"] == "periodo" else txs

    if r["modo"] == "periodo":
        constructores: Dict[str, Callable[[], Any]] = {
            "diario": lambda: _hoja_diario(lib, "diario", "LIBRO DIARIO"),
            "mayor": lambda: _hoja_mayor(lib),
            "balance_prueba": lambda: _hoja_balance_prueba(lib),
            "estado_resultados": lambda: _hoja_estado_resultados(lib),
            "balance_general": lambda: _hoja_balance_general(lib),
            "movimientos": lambda: _hoja_movimientos(lib, "movimientos", "MOVIMIENTOS", txs_filtradas),
            "auxiliar_tercero": lambda: _hoja_auxiliar(lib, txs_filtradas),
            "cartera": lambda: _hoja_cartera(lib),
            "impuestos": lambda: _hoja_impuestos(lib, txs_filtradas),
        }
    else:
        constructores = {
            "relacion": lambda: _hoja_movimientos(lib, "relacion", "RELACIÓN DE TRANSACCIONES", txs),
            "asientos": lambda: _hoja_diario(lib, "asientos", "ASIENTOS CONTABLES"),
            "resumen": lambda: _hoja_resumen(lib, txs),
            "soportes": lambda: lib.control.__setitem__("sin_soporte", _hoja_soportes(lib, txs)),
        }
    for clave in r["hojas"]:
        if clave in constructores:
            constructores[clave]()

    # ── Sello y advertencias (honestas: lo que falta se dice) ──
    lineas = lib.control["lineas"]
    debitos = round(sum(ln["debito"] for ln in lineas), 2)
    creditos = round(sum(ln["credito"] for ln in lineas), 2)
    adv = list(datos.get("advertencias_bd", []))
    fechas = sorted(f for f in (_a_fecha(t.get("transaction_date")) for t in txs) if f)
    otras: Dict[str, int] = {}
    for t in txs:
        if _moneda(t) != "COP":
            otras[_moneda(t)] = otras.get(_moneda(t), 0) + 1

    if not txs and not lineas:
        adv.append("No hay transacciones ni asientos en el alcance elegido: el libro sale en cero.")
    sin_cuenta = sum(1 for t in txs if t.get("account_id") in (None, ""))
    if sin_cuenta:
        adv.append(f"{sin_cuenta} transacción(es) sin cuenta bancaria asignada (DT-01).")
    for m, n in otras.items():
        adv.append(f"{n} transacción(es) en {m}: van en su propio bloque y nunca se suman al COP.")
    no_puc = sorted({ln["codigo"] for ln in lineas if not ln["codigo"].isdigit()})
    if no_puc:
        adv.append(f"{len(no_puc)} cuenta(s) sin código PUC numérico: {', '.join(no_puc[:8])} (DT-30).")
    borradores = {g.get("entry_group_id") for g in asientos if (g.get("estado") or "").upper() == "BORRADOR"}
    if borradores:
        adv.append(f"{len(borradores)} asiento(s) en BORRADOR no están en los libros: pendientes de "
                   "contabilizar en el módulo Contadores.")
    con_asiento = {g.get("tx_id") for g in asientos if g.get("entry_group_id") in en_libros}
    sin_asiento = [t.get("id") for t in txs if t.get("id") not in con_asiento]
    if sin_asiento:
        adv.append(f"{len(sin_asiento)} transacción(es) sin asiento contabilizado — no aparecen en los libros "
                   "oficiales (pueden estar en BORRADOR o sin regla contable).")
    if datos.get("truncado"):
        adv.append(f"El diario superó {LIMITE_ASIENTOS:,} asientos y se cortó: pide un período más corto.")
    if datos.get("faltantes"):
        adv.append("Estas transacciones elegidas ya no existen: "
                   + ", ".join(f"#{i}" for i in datos["faltantes"]) + ".")
    if lib.control.get("sin_soporte"):
        adv.append(f"{lib.control['sin_soporte']} transacción(es) sin soporte adjunto.")
    if "cartera" in r["hojas"]:
        adv.append("La cartera muestra los saldos pendientes ACTUALES, con edades calculadas a la fecha de corte.")

    cuadra = abs(debitos - creditos) < 0.01
    control = {"debitos": debitos, "creditos": creditos, "cuadra": cuadra}
    if r["modo"] == "periodo":
        er, bg = datos.get("er", {}), datos.get("bg", {})
        ingresos = sum(c["saldo"] for c in er.get("ingresos", []))
        gastos = sum(c["saldo"] for c in er.get("gastos", []))
        activo = sum(c["saldo"] for c in bg.get("activos", []))
        derecha = (sum(c["saldo"] for c in bg.get("pasivos", []))
                   + sum(c["saldo"] for c in bg.get("patrimonio", [])) + _num(bg.get("utilidad")))
        bp = datos.get("bp", [])
        bp_db = round(sum(c["db"] for c in bp), 2)
        bp_cr = round(sum(c["cr"] for c in bp), 2)
        control.update(utilidad_periodo=round(ingresos - gastos, 2),
                       ecuacion_contable=abs(activo - derecha) < 0.01,
                       diferencia_bg=round(activo - derecha, 2),
                       balance_prueba={"debitos": bp_db, "creditos": bp_cr})
        if not cuadra:
            adv.insert(0, f"El diario NO cuadra: débitos {debitos:,.2f} vs créditos {creditos:,.2f}.")
        if not control["ecuacion_contable"]:
            adv.insert(0, f"La ecuación contable no cuadra al corte (diferencia {control['diferencia_bg']:,.2f}).")
        if not datos.get("truncado") and (abs(bp_db - debitos) >= 0.01 or abs(bp_cr - creditos) >= 0.01):
            adv.insert(0, "El diario no coincide con el balance de prueba del kernel — revisar antes de entregar.")
    adv.extend(lib.advertencias)

    momento = (ahora or datetime.now(COLOMBIA)).replace(microsecond=0)
    u = usuario or {}
    quien = (u.get("name") or "").strip() or (f"usuario {u.get('uid')}" if u.get("uid") else "")
    if quien and u.get("role"):
        quien += f" ({u['role']})"
    sello = {
        "modo": r["modo"], "nombre": r["nombre"], "folio": r["folio"],
        "empresas": [{"id": e["id"], "nombre": e["nombre"], "nit": e["nit"]} for e in datos.get("empresas", [])],
        "consolidado": r["modo"] == "periodo" and not r["portfolios"],
        "desde": r["desde"].isoformat() if r["desde"] else None,
        "hasta": r["hasta"].isoformat() if r["hasta"] else None,
        "generado": momento.replace(tzinfo=None).isoformat(timespec="minutes"),
        "generado_por": quien,
        "hojas": [lib.catalogo[h] for h in r["hojas"]],
        "n_txs": len(txs),
        "n_txs_filtradas": len(txs_filtradas) if r["modo"] == "periodo" else None,
        "rango_real": {"desde": fechas[0].strftime("%d/%m/%Y") if fechas else None,
                       "hasta": fechas[-1].strftime("%d/%m/%Y") if fechas else None},
        "n_asientos": len(en_libros),
        "n_lineas": len(lineas),
        "totales_control": control,
        "otras_monedas": otras,
        "advertencias": adv,
    }
    _hoja_caratula(lib, sello)
    salida = io.BytesIO()
    lib.wb.save(salida)
    return salida.getvalue(), sello


# ══ Orquestación ══════════════════════════════════════════════════════════

def _slug(texto: str) -> str:
    s = unicodedata.normalize("NFKD", texto or "").encode("ascii", "ignore").decode()
    s = re.sub(r"[^A-Za-z0-9]+", "-", s).strip("-").upper()
    return s[:40] or "SIN-NOMBRE"


def nombre_archivo(r: Dict[str, Any], datos: Dict[str, Any]) -> str:
    if r["modo"] == "transacciones":
        base = _slug(r["nombre"]) if r["nombre"] else f"{len(datos.get('txs', []))}-TXS"
        return f"FINSYS_RELACION_{base}_{hoy_colombia().isoformat()}.xlsx"
    emp = datos.get("empresas") or []
    quien = "CONSOLIDADO" if not emp else (_slug(emp[0]["nombre"]) if len(emp) == 1 else f"VARIAS-{len(emp)}")
    desde = r["desde"].isoformat() if r["desde"] else "INICIO"
    return f"FINSYS_{quien}_{desde}_{r['hasta'].isoformat()}.xlsx"


def armar_libro(receta: Optional[Dict[str, Any]],
                usuario: Optional[Dict[str, Any]] = None) -> Tuple[bytes, Dict[str, Any], str]:
    r = normalizar_receta(receta)
    datos = recolectar(r)
    contenido, sello = construir_libro(datos, r, usuario=usuario)
    return contenido, sello, nombre_archivo(r, datos)
