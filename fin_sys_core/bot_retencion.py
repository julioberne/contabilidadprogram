# -*- coding: utf-8 -*-
"""FIN-SYS OS v2.0 — Retención de datos temporales del bot (Regla 6b, etapa 09.F).

Política (docs/reglas_proyecto.md, Regla 6b):
  1. DESCARTADO con más de 30 días sin actividad → se borra (y sus evidencias
     del bucket, best-effort).
  2. BORRADOR / ERROR con más de 60 días sin actividad → DESCARTADO, con aviso
     💤 al chat (D-09F-05: ERROR se trata como BORRADOR). Al entrar en
     DESCARTADO vuelven a empezar los 30 días de la regla 1.
  3. bot_messages con más de 90 días y sin borrador vivo → se borra.
  4. CONFIRMADO jamás se toca: es la trazabilidad del asiento.

Patrón analytics_log: sin scheduler — lo llama el poller una vez por hora y
todo es idempotente (la BD manda). Kill-switch: BOT_RETENCION_ACTIVA=0.
`purgar()` jamás lanza.
"""
import json
import os

DIAS_DESCARTADO = 30
DIAS_BORRADOR = 60
DIAS_MENSAJES = 90


def activa() -> bool:
    return os.environ.get("BOT_RETENCION_ACTIVA", "1").strip() != "0"


def _urls_evidencia(media_path, media_paths):
    lista = media_paths if isinstance(media_paths, list) else json.loads(media_paths or "[]")
    urls = [u for u in lista if u]
    if media_path and media_path not in urls:
        urls.append(media_path)
    return urls


def purgar(send_fn=None, conn=None) -> dict:
    """→ {"descartados_borrados", "borradores_vencidos", "mensajes_borrados"}."""
    res = {"descartados_borrados": 0, "borradores_vencidos": 0, "mensajes_borrados": 0}
    if not activa():
        return res
    from db_pool import get_conn, put_conn
    propia = conn is None
    try:
        if propia:
            conn = get_conn()
        cur = conn.cursor()

        # 1. DESCARTADO > 30 días → borrar (evidencias best-effort)
        cur.execute("""
            SELECT id, media_path, media_paths FROM transaction_drafts
             WHERE status = 'DESCARTADO'
               AND COALESCE(updated_at, created_at) < NOW() - INTERVAL '%s days'
        """ % int(DIAS_DESCARTADO))
        viejos = cur.fetchall()
        if viejos:
            try:
                from storage_media import eliminar_evidencia
            except Exception:
                eliminar_evidencia = None
            for _id, mp, mps in viejos:
                if eliminar_evidencia:
                    for url in _urls_evidencia(mp, mps):
                        eliminar_evidencia(url)
            ids = [r[0] for r in viejos]
            cur.execute("DELETE FROM transaction_drafts WHERE id = ANY(%s)", (ids,))
            res["descartados_borrados"] = cur.rowcount

        # 2. BORRADOR/ERROR > 60 días → DESCARTADO + aviso por chat
        cur.execute("""
            UPDATE transaction_drafts
               SET status = 'DESCARTADO',
                   error = 'Vencido: %s días sin actividad (retención Regla 6b)',
                   updated_at = NOW()
             WHERE status IN ('BORRADOR', 'ERROR')
               AND COALESCE(updated_at, created_at) < NOW() - INTERVAL '%s days'
            RETURNING id, chat_link_id
        """ % (int(DIAS_BORRADOR), int(DIAS_BORRADOR)))
        vencidos = cur.fetchall()
        res["borradores_vencidos"] = len(vencidos)
        por_chat = {}
        for did, link_id in vencidos:
            if link_id:
                por_chat.setdefault(link_id, []).append(did)
        for link_id, ids in por_chat.items():
            cur.execute("SELECT chat_id FROM bot_chat_links WHERE id = %s", (link_id,))
            row = cur.fetchone()
            if not row:
                continue
            texto = (f"💤 Retención: los borradores #{', #'.join(str(i) for i in ids)} llevaban "
                     f"{DIAS_BORRADOR} días sin actividad y pasaron a DESCARTADO. Se eliminan "
                     f"en {DIAS_DESCARTADO} días; si alguno sirve, recréalo desde la Bandeja web.")
            cur.execute("""
                INSERT INTO bot_messages (chat_link_id, raw_chat_id, direction, channel, kind, content)
                VALUES (%s, %s, 'OUT', 'telegram', 'retencion_aviso', %s)
            """, (link_id, str(row[0]), texto[:2000]))
            if send_fn:
                try:
                    send_fn(str(row[0]), texto)
                except Exception as e:
                    print(f"⚠️ [RETENCIÓN] aviso al chat {row[0]} falló: {e}")

        # 3. bot_messages > 90 días sin borrador vivo
        cur.execute("""
            DELETE FROM bot_messages m
             WHERE m.created_at < NOW() - INTERVAL '%s days'
               AND (m.draft_id IS NULL
                    OR NOT EXISTS (SELECT 1 FROM transaction_drafts d WHERE d.id = m.draft_id))
        """ % int(DIAS_MENSAJES))
        res["mensajes_borrados"] = cur.rowcount

        conn.commit()
        cur.close()
    except Exception as e:
        print(f"⚠️ [RETENCIÓN] purga falló (se reintenta en una hora): {e}")
        try:
            if conn is not None:
                conn.rollback()
        except Exception:
            pass
    finally:
        if propia and conn is not None:
            put_conn(conn)
    return res
