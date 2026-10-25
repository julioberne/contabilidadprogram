# -*- coding: utf-8 -*-
"""FIN-SYS OS v2.0 — Bitácora de anomalías del bot (pedido de Andrés, 9-oct-2026).

«Que el bot deje un registro cuando pase una anomalía, para tenerla en cuenta
a futuro, ir mejorando el sistema y saber qué nos falta y qué errores estamos
cometiendo.» Se ve en la pestaña 📓 Bitácora del módulo Bot IA de la web y con
/anomalias en el chat.

Reglas:
  · INFORMATIVA, no restrictiva: registrar jamás frena ni cambia un flujo.
    Lo único que el bot bloquea es lo que ya bloqueaba (confirmar sin cuenta,
    un traslado sin destino) porque dañaría la contabilidad.
  · Registro LITERAL, sin inferencias: qué pasó, con qué texto y qué borrador.
    `detalle` describe el hecho; `texto` guarda el mensaje tal cual llegó.
  · Best-effort: un fallo al registrar (p. ej. la tabla aún no existe antes
    del deploy) se traga y no rompe nada. Conexión propia del pool.
  · Los chats de prueba (`test-…`) no ensucian la bitácora real (la BD es la
    misma en local y en producción).
  · Retención: 180 días (la purga la corre el poller cada hora).

Tabla propia `bot_anomalias` (Zero-Impact): no altera ninguna tabla existente.
Se crea sola al arrancar el server (server._startup → init_table).
"""
import json

DIAS_RETENCION = 180

DDL = """
CREATE TABLE IF NOT EXISTS bot_anomalias (
    id SERIAL PRIMARY KEY,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    tipo TEXT NOT NULL,
    canal TEXT,
    chat_link_id INTEGER,
    draft_id INTEGER,
    detalle TEXT,
    texto TEXT,
    datos JSONB,
    revisada BOOLEAN NOT NULL DEFAULT FALSE,
    revisada_at TIMESTAMPTZ,
    nota TEXT
);
CREATE INDEX IF NOT EXISTS idx_bot_anomalias_fecha ON bot_anomalias(created_at DESC);
"""

# Clave → qué significa (lo que muestra la web). Hechos, no diagnósticos.
TIPOS = {
    "sms_plantilla_nueva": "SMS del banco sin plantilla: monto y fecha leídos tal cual; falta agregar la plantilla",
    "sms_cuenta_no_registrada": "La cuenta o tarjeta del SMS no está registrada en 💳 Cuentas",
    "sms_contraparte_sin_ficha": "El dato de la contraparte del SMS no está en ninguna ficha de tercero",
    "sms_traslado_sin_destino": "Traslado entre cuentas sin cuenta destino (p. ej. ahorro a un bolsillo)",
    "sms_error": "Un SMS no se pudo convertir en borrador",
    "reply_sin_borrador": "Respuesta a un mensaje del bot que no es de ningún borrador (se trató como texto suelto)",
    "reply_borrador_cerrado": "Respuesta a un borrador ya confirmado o descartado (no se cambió)",
    "borrador_descartado": "Borrador descartado",
    "correccion_sms": "Corrección a mano de un borrador de SMS (tipo, monto, fecha o cuenta)",
    "confirmacion_fallida": "Una confirmación no pasó la validación",
    "error_bot": "Error interno del bot al procesar un mensaje",
    "envio_perdido": "Un mensaje a Telegram no salió ni tras los reintentos (H5.4)",
}


def init_table(conn=None) -> None:
    """Crea la tabla si falta (arranque del server)."""
    from db_pool import get_conn, put_conn
    propia = conn is None
    if propia:
        conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute(DDL)
        conn.commit()
        cur.close()
    finally:
        if propia:
            put_conn(conn)


def registrar(tipo, detalle=None, *, draft_id=None, chat_link_id=None, canal=None,
              texto=None, datos=None) -> bool:
    """Anota una anomalía. Jamás lanza. → True si quedó escrita.
    El chat se completa desde el borrador si no se pasa; los chats `test-…`
    se excluyen en la misma sentencia."""
    try:
        from db_pool import get_conn, put_conn
        conn = get_conn()
    except Exception:
        return False
    try:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO bot_anomalias (tipo, canal, chat_link_id, draft_id, detalle, texto, datos)
            SELECT %(tipo)s, %(canal)s, COALESCE(%(link)s, d.chat_link_id), %(draft)s,
                   %(detalle)s, %(texto)s, %(datos)s
              FROM (SELECT 1) AS uno
              LEFT JOIN transaction_drafts d ON d.id = %(draft)s
              LEFT JOIN bot_chat_links l ON l.id = COALESCE(%(link)s, d.chat_link_id)
             WHERE COALESCE(l.chat_id, '') NOT LIKE 'test-%%'
        """, {"tipo": str(tipo)[:60], "canal": canal, "link": chat_link_id, "draft": draft_id,
              "detalle": (str(detalle) if detalle is not None else None),
              "texto": (str(texto)[:2000] if texto else None),
              "datos": json.dumps(datos, ensure_ascii=False, default=str) if datos else None})
        escrita = cur.rowcount == 1
        conn.commit()
        cur.close()
        return escrita
    except Exception as e:
        try:
            conn.rollback()
        except Exception:
            pass
        print(f"⚠️ [BITÁCORA] no se pudo registrar «{tipo}»: {str(e)[:120]}")
        return False
    finally:
        put_conn(conn)


def _fila(r):
    return {"id": r[0], "created_at": str(r[1]), "tipo": r[2], "canal": r[3],
            "chat_link_id": r[4], "draft_id": r[5], "detalle": r[6], "texto": r[7],
            "datos": r[8] if isinstance(r[8], (dict, list)) or r[8] is None else json.loads(r[8]),
            "revisada": bool(r[9]), "revisada_at": str(r[10]) if r[10] else None, "nota": r[11]}


def _filtro_usuario(hub_user_id):
    """Las del usuario (por su chat) y las sin chat (p. ej. errores sin vincular)."""
    if not hub_user_id:
        return "", {}
    return (" AND (a.chat_link_id IS NULL OR a.chat_link_id IN "
            "(SELECT id FROM bot_chat_links WHERE hub_user_id::text = %(uid)s))"), {"uid": str(hub_user_id)}


def listar(cur, dias=30, tipo=None, solo_abiertas=False, hub_user_id=None, limite=500):
    """Registros de los últimos `dias`, más recientes primero."""
    filtro, params = _filtro_usuario(hub_user_id)
    params.update({"dias": int(dias), "limite": int(limite)})
    if tipo:
        filtro += " AND a.tipo = %(tipo)s"
        params["tipo"] = tipo
    if solo_abiertas:
        filtro += " AND NOT a.revisada"
    cur.execute(f"""
        SELECT a.id, a.created_at, a.tipo, a.canal, a.chat_link_id, a.draft_id, a.detalle,
               a.texto, a.datos, a.revisada, a.revisada_at, a.nota
          FROM bot_anomalias a
         WHERE a.created_at >= NOW() - make_interval(days => %(dias)s){filtro}
         ORDER BY a.created_at DESC, a.id DESC
         LIMIT %(limite)s
    """, params)
    return [_fila(r) for r in cur.fetchall()]


def resumen(cur, dias=7, hub_user_id=None):
    """→ {tipo: {"total": n, "abiertas": n}} de los últimos `dias`."""
    filtro, params = _filtro_usuario(hub_user_id)
    params["dias"] = int(dias)
    cur.execute(f"""
        SELECT a.tipo, COUNT(*), COUNT(*) FILTER (WHERE NOT a.revisada)
          FROM bot_anomalias a
         WHERE a.created_at >= NOW() - make_interval(days => %(dias)s){filtro}
         GROUP BY a.tipo
         ORDER BY COUNT(*) DESC
    """, params)
    return {r[0]: {"total": r[1], "abiertas": r[2]} for r in cur.fetchall()}


def marcar(cur, anomalia_id, revisada=True, nota=None):
    """Revisada / pendiente, con nota opcional. → registro o None si no existe."""
    cur.execute("""
        UPDATE bot_anomalias
           SET revisada = %s, revisada_at = CASE WHEN %s THEN NOW() ELSE NULL END,
               nota = COALESCE(%s, nota)
         WHERE id = %s
     RETURNING id, created_at, tipo, canal, chat_link_id, draft_id, detalle, texto, datos,
               revisada, revisada_at, nota
    """, (bool(revisada), bool(revisada), (nota or None) and str(nota)[:500], int(anomalia_id)))
    r = cur.fetchone()
    return _fila(r) if r else None


def purgar(conn=None) -> int:
    """Borra lo que pasó la retención. Jamás lanza. → filas borradas."""
    from db_pool import get_conn, put_conn
    propia = conn is None
    try:
        if propia:
            conn = get_conn()
        cur = conn.cursor()
        cur.execute(f"DELETE FROM bot_anomalias WHERE created_at < NOW() - INTERVAL '{int(DIAS_RETENCION)} days'")
        n = max(cur.rowcount, 0)
        conn.commit()
        return n
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        return 0
    finally:
        if propia and conn is not None:
            put_conn(conn)


def texto_resumen(cur, dias=7, hub_user_id=None) -> str:
    """Lo que responde /anomalias en el chat."""
    datos = resumen(cur, dias, hub_user_id)
    if not datos:
        return f"📓 Bitácora: sin anomalías en los últimos {dias} días. ✨"
    lineas = [f"📓 Bitácora del bot — últimos {dias} días (pendientes / total):"]
    for tipo, n in datos.items():
        lineas.append(f"  · {n['abiertas']} / {n['total']} — {TIPOS.get(tipo, tipo)}")
    lineas.append("\nEl detalle (texto original y borrador de cada una) está en la web: "
                  "Bot IA → 📓 Bitácora.")
    return "\n".join(lineas)
