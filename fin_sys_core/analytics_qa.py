# -*- coding: utf-8 -*-
"""
FIN-SYS OS — Análisis Inteligente (B3): preguntas en español punto-a-punto
--------------------------------------------------------------------------
Archivo NUEVO (Zero-Impact). Orquesta la cadena completa:

  pregunta → ai_engine.structure_analytics_question (elige del catálogo)
           → metrics_catalog.ejecutar_metrica (la ÚNICA fuente de cifras)
           → texto en español con sello de origen + gráfica PNG (matplotlib Agg)

La empresa (portfolio_id) entra por parámetro desde el backend/sesión —
JAMÁS de la elección del LLM (criterio inmutable 2). El bot de Telegram
(hito 3) llamará responder_pregunta() directo, sin HTTP: misma maquinaria.
"""
from __future__ import annotations

import base64
import io
from typing import Any, Dict, List, Optional


def _fmt_cop(v: Any) -> str:
    """$1.234.567 estilo es-CO (sin decimales: contabilidad en COP)."""
    try:
        n = float(v)
    except (TypeError, ValueError):
        return str(v)
    signo = "-" if n < 0 else ""
    return f"{signo}${abs(n):,.0f}".replace(",", ".")


def _texto_respuesta(r: Dict[str, Any]) -> str:
    """Redacta la respuesta en español SOLO con cifras ya calculadas por el
    catálogo. Siempre cierra con el sello de origen (criterio inmutable 3)."""
    m = r.get("metrica")
    v = r.get("valores")
    partes: List[str] = []

    if m in ("gasto_mes", "ingreso_mes"):
        det = r.get("detalle") or {}
        nombre = "Gasto" if m == "gasto_mes" else "Ingresos"
        partes.append(f"{nombre} de {det.get('mes', 'el mes')}: {_fmt_cop(r.get('valor'))}.")
        if isinstance(v, list) and v:
            top = ", ".join(f"{x['etiqueta']} ({_fmt_cop(x['valor'])})" for x in v[:3])
            partes.append(f"Top por {det.get('agrupar_por', 'categoría')}: {top}.")
    elif m == "resumen_periodo" and isinstance(v, dict):
        partes.append(
            f"Ingresos {_fmt_cop(v.get('ingresos'))} · Gastos {_fmt_cop(v.get('gastos'))} "
            f"· Neto {_fmt_cop(v.get('neto'))}."
        )
    elif m == "variacion_mensual" and isinstance(v, dict):
        tipo = (r.get("detalle") or {}).get("tipo", "GASTO").capitalize()
        pct = v.get("pct")
        pct_txt = f"{'+' if pct > 0 else ''}{pct}%" if pct is not None else "sin base de comparación"
        partes.append(
            f"{tipo} de {v.get('mes')}: {_fmt_cop(v.get('total_mes'))} vs "
            f"{_fmt_cop(v.get('total_mes_anterior'))} en {v.get('mes_anterior')} → {pct_txt} "
            f"({_fmt_cop(v.get('delta'))})."
        )
    elif m == "flujo_mensual" and isinstance(v, list):
        ing = sum(x.get("ingresos", 0) for x in v)
        gas = sum(x.get("gastos", 0) for x in v)
        partes.append(
            f"Últimos {(r.get('detalle') or {}).get('meses', len(v))} meses: ingresos "
            f"{_fmt_cop(ing)}, gastos {_fmt_cop(gas)}, neto {_fmt_cop(ing - gas)}."
        )
    elif m == "balance_cuentas":
        partes.append(f"Balance total en COP: {_fmt_cop(r.get('valor'))} "
                      f"en {len(v) if isinstance(v, list) else 0} cuentas.")
        if isinstance(v, list) and v:
            top = ", ".join(f"{x['etiqueta']} ({_fmt_cop(x['valor'])})" for x in v[:3])
            partes.append(f"Principales: {top}.")
    elif m == "cartera_vencida" and isinstance(v, dict):
        pct = v.get("pct_vencida")
        partes.append(
            f"Cartera vencida: {_fmt_cop(v.get('monto_vencido'))} en {v.get('n_vencidas')} "
            f"cuentas por cobrar"
            + (f" ({pct}% de lo pendiente)." if pct is not None else ".")
        )
        clientes = v.get("clientes") or []
        if clientes:
            top = ", ".join(f"{c['etiqueta']} ({_fmt_cop(c['valor'])})" for c in clientes[:3])
            partes.append(f"Mayores deudores: {top}.")
    elif m == "calidad_datos" and isinstance(v, dict):
        partes.append(
            f"De {v.get('txs_total')} transacciones: {v.get('txs_sin_categoria')} sin categoría "
            f"y {v.get('txs_sin_evidencia')} sin evidencia. Terceros: "
            f"{v.get('terceros_numero_provisional')} con número provisional y "
            f"{v.get('terceros_nombres_duplicados')} nombres duplicados."
        )
    elif r.get("valor") is not None:
        partes.append(f"{r.get('etiqueta', 'Resultado')}: {_fmt_cop(r.get('valor'))}.")
    else:
        partes.append(f"{r.get('etiqueta', 'Resultado')} calculado.")

    if r.get("nota"):
        partes.append(r["nota"])
    origen = r.get("origen") or {}
    if origen.get("sello"):
        sello = origen["sello"]
        if origen.get("usd_excluidas"):
            sello += f" ({origen['usd_excluidas']} TXs en USD excluidas)"
        partes.append(f"— {sello}.")
    return " ".join(partes)


# ── Gráfica (matplotlib backend Agg, sin pyplot: thread-safe con gunicorn) ──

_COLOR_ING = "#16a34a"   # verde brutalista del shell
_COLOR_GAS = "#dc2626"   # rojo
_COLOR_NEU = "#111111"   # negro


def _eje_dinero(ax):
    from matplotlib.ticker import FuncFormatter

    def _fmt(x, _pos):
        ax_abs = abs(x)
        if ax_abs >= 1e9:
            return f"${x / 1e9:.1f}mM"
        if ax_abs >= 1e6:
            return f"${x / 1e6:.1f}M"
        if ax_abs >= 1e3:
            return f"${x / 1e3:.0f}k"
        return f"${x:.0f}"
    return FuncFormatter(_fmt)


def _generar_grafica(r: Dict[str, Any]) -> Optional[str]:
    """PNG base64 de la métrica, o None si la forma no da para gráfica.
    Cualquier error aquí devuelve None: la gráfica jamás tumba la respuesta."""
    try:
        return _generar_grafica_o_falla(r)
    except Exception as e:
        print(f"⚠️ [ANALYTICS] La gráfica falló (se responde sin ella): {e}")
        return None


def _generar_grafica_o_falla(r: Dict[str, Any]) -> Optional[str]:
    m = r.get("metrica")
    v = r.get("valores")

    import matplotlib
    matplotlib.use("Agg", force=False)
    from matplotlib.figure import Figure

    fig = Figure(figsize=(7.2, 4.2), dpi=110)
    ax = fig.subplots()
    titulo = r.get("etiqueta", "")

    if m in ("gasto_mes", "ingreso_mes", "balance_cuentas") and isinstance(v, list) and v:
        filas = [x for x in v if isinstance(x.get("valor"), (int, float))][:10][::-1]
        if not filas:
            return None
        color = _COLOR_GAS if m == "gasto_mes" else _COLOR_ING if m == "ingreso_mes" else _COLOR_NEU
        ax.barh([x["etiqueta"][:28] for x in filas], [x["valor"] for x in filas],
                color=color, edgecolor="black", linewidth=1.2)
        ax.xaxis.set_major_formatter(_eje_dinero(ax))
        det = r.get("detalle") or {}
        if det.get("mes"):
            titulo += f" — {det['mes']} por {det.get('agrupar_por', '')}"
    elif m == "cartera_vencida" and isinstance(v, dict) and (v.get("clientes") or []):
        filas = v["clientes"][:10][::-1]
        ax.barh([c["etiqueta"][:28] for c in filas], [c["valor"] for c in filas],
                color=_COLOR_GAS, edgecolor="black", linewidth=1.2)
        ax.xaxis.set_major_formatter(_eje_dinero(ax))
        titulo += " — top clientes"
    elif m == "flujo_mensual" and isinstance(v, list) and v:
        meses = [x["mes"] for x in v]
        idx = range(len(meses))
        ancho = 0.4
        ax.bar([i - ancho / 2 for i in idx], [x["ingresos"] for x in v], ancho,
               label="Ingresos", color=_COLOR_ING, edgecolor="black", linewidth=1.2)
        ax.bar([i + ancho / 2 for i in idx], [x["gastos"] for x in v], ancho,
               label="Gastos", color=_COLOR_GAS, edgecolor="black", linewidth=1.2)
        ax.set_xticks(list(idx), meses, rotation=45 if len(meses) > 8 else 0)
        ax.yaxis.set_major_formatter(_eje_dinero(ax))
        ax.legend(frameon=False)
    elif m == "resumen_periodo" and isinstance(v, dict):
        ax.bar(["Ingresos", "Gastos", "Neto"],
               [v.get("ingresos", 0), v.get("gastos", 0), v.get("neto", 0)],
               color=[_COLOR_ING, _COLOR_GAS, _COLOR_NEU], edgecolor="black", linewidth=1.2)
        ax.yaxis.set_major_formatter(_eje_dinero(ax))
    elif m == "variacion_mensual" and isinstance(v, dict):
        ax.bar([v.get("mes_anterior", "anterior"), v.get("mes", "actual")],
               [v.get("total_mes_anterior", 0), v.get("total_mes", 0)],
               color=[_COLOR_NEU, _COLOR_GAS], edgecolor="black", linewidth=1.2)
        ax.yaxis.set_major_formatter(_eje_dinero(ax))
        titulo += f" — {(r.get('detalle') or {}).get('tipo', '')}".rstrip(" —")
    elif m == "calidad_datos" and isinstance(v, dict):
        etiquetas = ["Sin categoría", "Sin evidencia", "3ros provisionales", "3ros duplicados"]
        datos = [v.get("txs_sin_categoria", 0), v.get("txs_sin_evidencia", 0),
                 v.get("terceros_numero_provisional", 0), v.get("terceros_nombres_duplicados", 0)]
        ax.bar(etiquetas, datos, color=_COLOR_NEU, edgecolor="black", linewidth=1.2)
    else:
        return None   # métrica escalar o sin datos: el texto basta

    # Estética retro-brutalista: fondo blanco, marcos negros, mono.
    for s in ax.spines.values():
        s.set_linewidth(1.4)
        s.set_color("black")
    ax.set_title(titulo, fontsize=11, fontweight="bold", family="monospace", loc="left")
    sello = (r.get("origen") or {}).get("sello", "")
    if sello:
        fig.text(0.01, 0.01, sello, fontsize=7.5, family="monospace", color="#444444")
    ax.tick_params(labelsize=8)
    fig.set_facecolor("white")
    ax.set_facecolor("white")

    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight")
    return base64.b64encode(buf.getvalue()).decode("ascii")


def responder_pregunta(pregunta: str, portfolio_id: Optional[int] = None) -> Dict[str, Any]:
    """Cadena completa web/bot. Devuelve SIEMPRE un dict con:
      {texto, metrica, datos, grafica_png_base64}
    Los errores de traducción/cálculo se devuelven como texto honesto."""
    from metrics_catalog import catalogo_para_prompt, ejecutar_metrica
    import ai_engine

    eleccion = ai_engine.structure_analytics_question(pregunta, catalogo_para_prompt())
    if not eleccion.get("metrica"):
        motivo = eleccion.get("motivo") or (
            "No encontré una métrica del catálogo que responda esa pregunta."
        )
        return {"texto": motivo, "metrica": None, "datos": None, "grafica_png_base64": None}

    try:
        # portfolio_id viene del backend (selector/sesión) — no de la elección.
        resultado = ejecutar_metrica(eleccion["metrica"], eleccion.get("params"),
                                     portfolio_id=portfolio_id)
    except ValueError as e:
        return {"texto": f"No pude calcularlo: {e}", "metrica": eleccion.get("metrica"),
                "datos": None, "grafica_png_base64": None}

    return {
        "texto": _texto_respuesta(resultado),
        "metrica": resultado["metrica"],
        "datos": resultado,
        "grafica_png_base64": _generar_grafica(resultado),
    }
