# -*- coding: utf-8 -*-
"""
FIN-SYS OS — Análisis Inteligente (hito 2, B1): insights automáticos
---------------------------------------------------------------------
Archivo NUEVO (Zero-Impact). Reglas de negocio SOBRE el catálogo: este
módulo no calcula NINGUNA cifra por su cuenta — solo llama
ejecutar_metrica() (criterio inmutable 1) y decide si el resultado
amerita una tarjeta ("el gasto subió 45%", "hay cartera vencida",
"hay datos por limpiar").

Consumidores:
  - GET /api/analytics/insights → tarjetas del HomeDashboard.
  - tick_resumen_telegram(): lo llama el poller del bot cada rato; si ya
    pasaron ANALYTICS_RESUMEN_HORAS (por defecto 24; 0 = apagado) desde
    el último envío, manda el resumen a los chats vinculados ACTIVOS.
    La marca de "ya se envió" vive en bot_messages (kind =
    resumen_analytics): sobrevive reinicios y no necesita scheduler
    (hoy no existe ninguno) — mismo truco de la purga de la bitácora.

Niveles de tarjeta: alerta (requiere acción) · info (dato útil) ·
ok (todo bien). Toda tarjeta lleva su sello de origen (criterio 3) y
los errores son honestos: si una métrica falla, la tarjeta no se
inventa — la falla se reporta en "errores" (criterio 4).
"""
from __future__ import annotations

import datetime as _dt
import os
from typing import Any, Callable, Dict, List, Optional

# Variación mes-a-mes que amerita tarjeta (en %). Debajo de esto, silencio:
# los insights son señales, no ruido.
UMBRAL_VARIACION_PCT = 30.0

# kind del mensaje OUT en bot_messages que marca "resumen ya enviado".
RESUMEN_KIND = "resumen_analytics"


def _ejecutar(metric_id: str, params: Optional[Dict[str, Any]] = None,
              portfolio_id: Optional[int] = None, conn=None) -> Dict[str, Any]:
    """Indirección sobre el catálogo (la ÚNICA fuente de cifras; mockeable)."""
    from metrics_catalog import ejecutar_metrica
    return ejecutar_metrica(metric_id, params, portfolio_id=portfolio_id, conn=conn)


def _cop(v: Any) -> str:
    from analytics_qa import _fmt_cop
    return _fmt_cop(v)


def _tarjeta(id_: str, nivel: str, titulo: str, cifra: str, texto: str,
             r: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "id": id_, "nivel": nivel, "titulo": titulo, "cifra": cifra,
        "texto": texto, "metrica": r.get("metrica"),
        "sello": (r.get("origen") or {}).get("sello", ""),
    }


# ── Las reglas (cada una: métrica del catálogo → tarjeta o None) ──────────

def _insight_pulso(portfolio_id, conn):
    """Pulso del mes en curso: ingresos vs gastos, del catálogo."""
    r = _ejecutar("resumen_periodo", None, portfolio_id, conn)
    v = r.get("valores") or {}
    neto = float(v.get("neto") or 0)
    if not (r.get("origen") or {}).get("n_txs"):
        return None   # sin TXs en el mes: no hay pulso que mostrar
    nivel = "ok" if neto >= 0 else "info"
    texto = (f"Ingresos {_cop(v.get('ingresos'))} vs gastos {_cop(v.get('gastos'))} "
             f"en lo corrido del mes.")
    return _tarjeta("pulso_mes", nivel, "Pulso del mes", _cop(neto), texto, r)


def _insight_variacion(portfolio_id, conn):
    """Gasto del mes vs mes anterior: tarjeta solo si el salto es fuerte."""
    r = _ejecutar("variacion_mensual", {"tipo": "GASTO"}, portfolio_id, conn)
    v = r.get("valores") or {}
    pct = v.get("pct")
    if pct is None or abs(pct) < UMBRAL_VARIACION_PCT:
        return None   # sin base de comparación o dentro de lo normal: silencio
    subio = pct > 0
    texto = (f"{_cop(v.get('total_mes'))} en {v.get('mes')} vs "
             f"{_cop(v.get('total_mes_anterior'))} en {v.get('mes_anterior')} "
             f"({_cop(v.get('delta'))}).")
    return _tarjeta(
        "variacion_gasto", "alerta" if subio else "ok",
        "El gasto subió fuerte" if subio else "El gasto bajó fuerte",
        f"{pct:+.1f}%", texto, r,
    )


def _insight_cartera(portfolio_id, conn):
    r = _ejecutar("cartera_vencida", None, portfolio_id, conn)
    v = r.get("valores") or {}
    vencido = float(v.get("monto_vencido") or 0)
    pendientes = int(v.get("n_pendientes") or 0)
    if vencido > 0:
        pct = v.get("pct_vencida")
        clientes = v.get("clientes") or []
        texto = f"{v.get('n_vencidas')} cuentas por cobrar vencidas"
        if pct is not None:
            texto += f" ({pct}% de lo pendiente)"
        if clientes:
            texto += f". Mayor deudor: {clientes[0]['etiqueta']} ({_cop(clientes[0]['valor'])})"
        return _tarjeta("cartera_vencida", "alerta", "Cartera vencida",
                        _cop(vencido), texto + ".", r)
    if pendientes:
        texto = (f"{_cop(v.get('monto_pendiente_total'))} pendientes en "
                 f"{pendientes} cuentas por cobrar, ninguna vencida.")
        return _tarjeta("cartera_al_dia", "ok", "Cartera al día", "0 vencidas", texto, r)
    return None   # sin cartera: nada que decir


def _insight_calidad(portfolio_id, conn):
    r = _ejecutar("calidad_datos", None, portfolio_id, conn)
    v = r.get("valores") or {}
    if not v.get("txs_total"):
        return None
    pendientes = [
        # (n, singular, plural)
        (v.get("txs_sin_categoria", 0), "TX sin categoría", "TXs sin categoría"),
        (v.get("txs_sin_evidencia", 0), "TX sin evidencia", "TXs sin evidencia"),
        (v.get("terceros_numero_provisional", 0), "tercero provisional", "terceros provisionales"),
        (v.get("terceros_nombres_duplicados", 0), "tercero duplicado", "terceros duplicados"),
    ]
    problemas = [(n, sing, plur) for n, sing, plur in pendientes if n]
    total = sum(n for n, _, _ in problemas)
    if not total:
        return _tarjeta("datos_limpios", "ok", "Datos limpios", "0 pendientes",
                        "Todas las TXs con categoría y evidencia; terceros sin duplicados.", r)
    texto = ", ".join(f"{n} {sing if n == 1 else plur}" for n, sing, plur in problemas) + "."
    return _tarjeta("datos_sucios", "info", "Datos por limpiar", str(total), texto, r)


_REGLAS: List[Callable] = [_insight_pulso, _insight_variacion, _insight_cartera, _insight_calidad]
_ORDEN_NIVEL = {"alerta": 0, "info": 1, "ok": 2}


def generar_insights(portfolio_id: Optional[int] = None, conn=None) -> Dict[str, Any]:
    """Corre todas las reglas. Una regla que falla NO tumba las demás:
    su error queda visible en "errores" (jamás una tarjeta inventada)."""
    insights: List[Dict[str, Any]] = []
    errores: List[str] = []
    for regla in _REGLAS:
        try:
            tarjeta = regla(portfolio_id, conn)
            if tarjeta:
                insights.append(tarjeta)
        except Exception as e:
            msg = str(e).strip().splitlines()[0] if str(e).strip() else "error desconocido"
            errores.append(f"{regla.__name__.replace('_insight_', '')}: {msg[:160]}")
    insights.sort(key=lambda i: _ORDEN_NIVEL.get(i.get("nivel"), 3))
    return {
        "insights": insights,
        "errores": errores,
        "generado": _dt.datetime.now().isoformat(timespec="seconds"),
    }


# ── Resumen para Telegram (hito 2: informativo, criterio 5) ──────────────

_ICONO = {"alerta": "⚠", "info": "•", "ok": "✓"}


def resumen_texto(portfolio_id: Optional[int] = None, conn=None) -> str:
    """El mismo motor de tarjetas, redactado en texto plano para el bot."""
    data = generar_insights(portfolio_id, conn=conn)
    lineas = ["📊 FIN-SYS — resumen automático"]
    for i in data["insights"]:
        linea = f"{_ICONO.get(i['nivel'], '•')} {i['titulo']}: {i['texto']}"
        if i.get("sello"):
            linea += f" — {i['sello']}."
        lineas.append(linea)
    if not data["insights"]:
        lineas.append("Sin datos suficientes para generar insights (no se inventa).")
    if data["errores"]:
        lineas.append("⚠ No se pudo calcular: " + "; ".join(data["errores"]))
    if portfolio_id is None:
        lineas.append("(Consolidado de todas las empresas)")
    return "\n".join(lineas)


def _horas_resumen() -> float:
    """Cada cuántas horas se envía el resumen (0 o negativo = apagado)."""
    try:
        return float(os.environ.get("ANALYTICS_RESUMEN_HORAS", "24"))
    except (TypeError, ValueError):
        return 24.0


def tick_resumen_telegram(send_fn, conn=None) -> bool:
    """Llamado por el poller del bot en cada vuelta (él lo throttlea).

    Reloj en la BD (CURRENT_TIMESTAMP vs MAX(created_at) del último envío):
    inmune a reinicios y a desfases de reloj local. Best-effort SIEMPRE:
    jamás lanza — si algo falla, se reintenta en el próximo tick.
    → True solo si el resumen se envió a al menos un chat.
    """
    cada = _horas_resumen()
    if cada <= 0 or send_fn is None:
        return False
    propia = conn is None
    try:
        if propia:
            from database_driver import get_db_connection
            conn = get_db_connection()
            if conn is None:
                return False
        cur = conn.cursor()
        cur.execute("""
            SELECT EXTRACT(EPOCH FROM (CURRENT_TIMESTAMP - MAX(created_at))) / 3600.0
              FROM bot_messages
             WHERE direction = 'OUT' AND kind = %s;
        """, (RESUMEN_KIND,))
        fila = cur.fetchone()
        horas = fila[0] if fila else None
        if horas is not None and float(horas) < cada:
            cur.close()
            return False

        cur.execute("""
            SELECT chat_id FROM bot_chat_links
             WHERE channel = 'telegram' AND status = 'ACTIVO';
        """)
        chats = [f[0] for f in cur.fetchall()]
        if not chats:
            cur.close()
            return False

        # Consolidado (portfolio None): la misma verdad de la Home.
        texto = resumen_texto(None, conn=conn)
        enviado = False
        for chat in chats:
            if send_fn(str(chat), texto[:4096]) is not None:
                cur.execute("""
                    INSERT INTO bot_messages (raw_chat_id, direction, channel, kind, content)
                    VALUES (%s, 'OUT', 'telegram', %s, %s);
                """, (str(chat), RESUMEN_KIND, texto[:2000]))
                enviado = True
        conn.commit()
        cur.close()
        return enviado
    except Exception as e:
        print(f"⚠️ [INSIGHTS] tick de resumen falló (se reintenta en el próximo): {e}")
        try:
            if conn is not None:
                conn.rollback()
        except Exception:
            pass
        return False
    finally:
        if propia and conn is not None:
            try:
                from database_driver import release_db_connection
                release_db_connection(conn)
            except Exception:
                pass
