# -*- coding: utf-8 -*-
"""FIN-SYS OS v2.0 — Etapa 09.F: SMS de Bancolombia → borradores del bot.

Dos mitades:
  · PURA (testeable con un cursor falso): resolvedores por id, mapeo al
    payload del borrador, encabezado del resumen, clave de dedupe.
  · CON BD: `procesar_pendientes(send_fn)` — el tick que corre el poller de
    Telegram en cada vuelta: toma los SMS encolados por el webhook en
    bot_messages (channel='sms', draft_id IS NULL), los convierte en
    transaction_drafts y envía el resumen con botones al chat vinculado.

Regla 6b (docs/reglas_proyecto.md): nada se adivina.
  · La cuenta origen se resuelve POR ID con user_accounts.last4_cuenta /
    last4_tarjeta (D-09F-03). 0 ó >1 coincidencias → borrador sin cuenta,
    no confirmable, con aviso. Jamás "Efectivo" por defecto.
  · El tercero solo por third_parties.phone (celular destino) con UNA
    coincidencia exacta; si no, "Sin especificar" (se completa en 09.G).
  · SMS no reconocido → borrador con el texto crudo, sin monto ni concepto.
  · Un error en un SMS marca ESA fila (kind='sms_error') y avisa; el tick
    nunca lanza hacia el poller.
No se usa build_draft: pisa la fecha con hoy y sus resolvedores casan por
palabras ("Bancolombia", "Efectivo") — eso es adivinar (D-09F-04).
Spec: docs/specs/09-bot-ia/09.F-sms-bancolombia.md
"""
import hashlib
import hmac
import json
import re
from datetime import date

from draft_builder import build_payload, compute_missing, resolver_portafolio
from sms_bancolombia import REMITENTE_DEFAULT, parsear

# ── Esquema propio (self-heal en server._startup + scripts/migrate_sms_bancolombia.py) ──
DDL_SMS_TOKENS = """
CREATE TABLE IF NOT EXISTS sms_ingest_tokens (
    id SERIAL PRIMARY KEY,
    hub_user_id UUID NOT NULL REFERENCES hub_users(id) ON DELETE CASCADE,
    token_hash TEXT NOT NULL UNIQUE,                 -- sha256 hex; el token plano se muestra UNA vez
    label TEXT,
    sender_allowlist TEXT[] NOT NULL DEFAULT '{85540}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    last_seen_at TIMESTAMPTZ,
    revoked_at TIMESTAMPTZ
);
"""
# Cuentas por id (D-09F-03): los últimos 4 dígitos son campo estructurado,
# el nombre de la cuenta queda libre. Columnas nulas: no rompen nada existente.
DDL_LAST4 = (
    "ALTER TABLE user_accounts ADD COLUMN IF NOT EXISTS last4_cuenta VARCHAR(4);",
    "ALTER TABLE user_accounts ADD COLUMN IF NOT EXISTS last4_tarjeta VARCHAR(4);",
)

MAX_SMS_BYTES = 4096


def init_sms_tables(conn=None) -> None:
    """Crea la tabla de tokens y las columnas last4 si faltan (arranque del server)."""
    from db_pool import get_conn, put_conn
    propia = conn is None
    if propia:
        conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute(DDL_SMS_TOKENS)
        for sql in DDL_LAST4:
            cur.execute(sql)
        conn.commit()
        cur.close()
    finally:
        if propia:
            put_conn(conn)


# ══════════════════════════════════════════════════════════════════════════════
# Mitad pura
# ══════════════════════════════════════════════════════════════════════════════

def hash_token(token: str) -> str:
    return hashlib.sha256((token or "").encode()).hexdigest()


def solo_digitos(s) -> str:
    return re.sub(r"\D", "", str(s or ""))


def clave_dedupe(remitente, texto, sent_stamp=None) -> str:
    """Clave estable por SMS: el texto ya trae fecha y hora al minuto, así que
    un reenvío de la app cae en el índice único de bot_messages (R-09F-02).
    Dos SMS idénticos en el mismo minuto se funden (D-09F-07, aceptado)."""
    base = f"{solo_digitos(remitente)}|{(texto or '').strip()}|{sent_stamp or ''}"
    return hashlib.sha256(base.encode()).hexdigest()[:32]


_CAMPOS_LAST4 = ("last4_cuenta", "last4_tarjeta")


def resolver_cuenta_por_last4(cur, last4, campo="last4_cuenta"):
    """→ (account_id, name) si EXACTAMENTE una cuenta tiene esos 4 dígitos en
    `campo`; (None, None) si ninguna o si es ambiguo (ambigüedad = pregunta)."""
    if campo not in _CAMPOS_LAST4:
        raise ValueError(f"campo inválido: {campo}")
    last4 = solo_digitos(last4)[-4:]
    if len(last4) != 4:
        return None, None
    cur.execute(f"SELECT id, name FROM user_accounts WHERE {campo} = %s ORDER BY id", (last4,))
    filas = cur.fetchall()
    if len(filas) == 1:
        return filas[0][0], filas[0][1]
    return None, None


def resolver_tercero_por_celular(cur, celular):
    """→ dict del tercero si UNA fila de third_parties tiene ese celular
    (tolera '+57 319 330 1184'); None en cualquier otro caso."""
    celular = solo_digitos(celular)
    if len(celular) != 10:
        return None
    cur.execute("""
        SELECT identification_type, identification_number, name, phone
          FROM third_parties
         WHERE regexp_replace(COALESCE(phone, ''), '\\D', '', 'g') LIKE %s
         ORDER BY id
    """, ("%" + celular,))
    filas = cur.fetchall()
    if len(filas) != 1:
        return None
    t, n, nombre, tel = filas[0]
    return {"identification_type": t, "identification_number": n, "name": nombre,
            "phone": tel}


def concepto_sms(sms, transferencia_propia=False) -> str:
    """Traducción literal del SMS (no una adivinanza): lo que dice el banco."""
    if not sms:
        return ""
    if sms["familia"] == "transferencia_enviada":
        if transferencia_propia:
            return f"Transferencia entre cuentas *{sms['origen_last4']} → *{sms['destino_last4']} (SMS)"
        return f"Transferencia Bancolombia *{sms['origen_last4']} → *{sms['destino_last4']} (SMS)"
    return f"{sms['familia']} (SMS)"


def mapear_a_parsed(sms, cuenta_nombre=None, tercero=None, transferencia_propia=False) -> dict:
    """Forma exacta que consume draft_builder.build_payload. SMS None = no reconocido."""
    if sms is None:
        return {"type": "GASTO", "amount": None, "concept": "", "payment_method": "",
                "category": None, "third_party": {}, "is_recurring": False,
                "inferred_fields": ["type"]}
    if transferencia_propia:
        tipo, inferidos = "TRANSFERENCIA", []
    else:
        tipo, inferidos = sms.get("tipo_sugerido") or "GASTO", ["type"]
    return {
        "type": tipo,
        "amount": sms.get("amount"),
        "concept": concepto_sms(sms, transferencia_propia),
        "payment_method": cuenta_nombre or "",
        "category": None,
        "third_party": tercero or {},
        "is_recurring": False,
        "inferred_fields": inferidos,
    }


def construir_borrador_sms(cur, texto_sms, remitente, portafolio_preferido):
    """SMS crudo → {payload, inferred_fields, missing_fields, sms, reconocido,
    account_id}. Lanza ValueError solo si no hay portafolios."""
    sms = parsear(texto_sms)
    portafolio, corregido = resolver_portafolio(cur, portafolio_preferido)
    if portafolio is None:
        raise ValueError("No hay portafolios en FIN-SYS: crea uno en la web primero.")

    account_id = cuenta_nombre = None
    dest_account_id = None
    tercero = None
    if sms:
        account_id, cuenta_nombre = resolver_cuenta_por_last4(cur, sms["origen_last4"])
        if sms.get("destino_es_celular"):
            tercero = resolver_tercero_por_celular(cur, sms["destino"])
        else:
            # ¿El destino es otra cuenta MÍA? → transferencia entre cuentas (determinista)
            dest_account_id, _ = resolver_cuenta_por_last4(cur, sms["destino_last4"])

    parsed = mapear_a_parsed(sms, cuenta_nombre, tercero,
                             transferencia_propia=bool(dest_account_id))
    payload, inferred = build_payload(parsed, portafolio)
    if corregido:
        inferred.append("portfolio_name")

    # Cuenta POR ID (D-09F-03). build_payload puso "Efectivo"+inferido cuando no
    # había nombre: eso sería adivinar — se deja vacío y no confirmable.
    inferred = [f for f in inferred if f != "payment_method"]
    if account_id:
        payload["payment_method"] = cuenta_nombre
        payload["account_id"] = account_id
    else:
        payload["payment_method"] = ""
        payload["account_id"] = None
    payload["dest_account_id"] = dest_account_id

    # Fecha del SMS (build_payload siempre pone hoy)
    if sms and sms.get("fecha"):
        payload["transaction_date"] = sms["fecha"]
    else:
        payload["transaction_date"] = date.today().isoformat()
        inferred.append("transaction_date")
    if sms and sms.get("currency") and sms["currency"] != "COP":
        payload["transaction_currency"] = sms["currency"]

    missing = compute_missing(payload)
    if not account_id:
        missing.append("cuenta")
    inferred = sorted(set(inferred))
    payload["inferred_fields"] = inferred
    payload["missing_fields"] = missing
    payload["sms"] = {
        "familia": sms["familia"] if sms else None,
        "remitente": solo_digitos(remitente) or REMITENTE_DEFAULT,
        "origen_last4": sms["origen_last4"] if sms else None,
        "destino": sms["destino"] if sms else None,
        "hora": sms.get("hora") if sms else None,
    }
    return {"payload": payload, "inferred_fields": inferred, "missing_fields": missing,
            "sms": sms, "reconocido": sms is not None, "account_id": account_id}


def encabezado_sms(res) -> str:
    """Prefijo del resumen (mismo patrón que '📎 Evidencia adjunta.' en bot_driver)."""
    remitente = (res.get("payload") or {}).get("sms", {}).get("remitente") or REMITENTE_DEFAULT
    lineas = [f"📲 SMS Bancolombia ({remitente})"]
    if not res.get("reconocido"):
        lineas.append("⚠️ SMS no reconocido — completa monto y concepto en la Bandeja web")
    elif not res.get("account_id"):
        origen = (res.get("sms") or {}).get("origen_last4") or "????"
        lineas.append(f"⚠️ Cuenta *{origen} no registrada — ponle sus últimos 4 dígitos "
                      "en 💳 Cuentas y edita el borrador en la web")
    return "\n".join(lineas) + "\n\n"


# ══════════════════════════════════════════════════════════════════════════════
# Mitad con BD
# ══════════════════════════════════════════════════════════════════════════════

def resolver_identidad(cur, token):
    """Token plano del header → {token_id, hub_user_id, allowlist, chat_link_id,
    chat_id} o None. Comparación en tiempo constante sobre el hash."""
    if not token:
        return None
    h = hash_token(token.strip())
    cur.execute("""
        SELECT id, hub_user_id, sender_allowlist, token_hash
          FROM sms_ingest_tokens
         WHERE token_hash = %s AND revoked_at IS NULL
    """, (h,))
    row = cur.fetchone()
    if not row or not hmac.compare_digest(str(row[3]), h):
        return None
    cur.execute("""
        SELECT id, chat_id FROM bot_chat_links
         WHERE hub_user_id = %s AND channel = 'telegram' AND status = 'ACTIVO'
         ORDER BY id LIMIT 1
    """, (str(row[1]),))
    link = cur.fetchone()
    cur.execute("UPDATE sms_ingest_tokens SET last_seen_at = NOW() WHERE id = %s", (row[0],))
    return {
        "token_id": row[0],
        "hub_user_id": str(row[1]),
        "allowlist": [solo_digitos(x) for x in (row[2] or [])],
        "chat_link_id": link[0] if link else None,
        "chat_id": link[1] if link else None,
    }


def encolar_sms(cur, identidad, remitente, texto, sent_stamp=None):
    """Única escritura del webhook: fila IN en bot_messages. → (id|None, duplicado)."""
    ext = clave_dedupe(remitente, texto, sent_stamp)
    kind = "sms" if identidad.get("chat_link_id") else "sms_sin_chat"
    contenido = json.dumps({"from": solo_digitos(remitente), "text": texto,
                            "sentStamp": sent_stamp}, ensure_ascii=False)[:2000]
    cur.execute("""
        INSERT INTO bot_messages (chat_link_id, raw_chat_id, direction, channel,
                                  external_message_id, kind, content)
        VALUES (%s, %s, 'IN', 'sms', %s, %s, %s)
        ON CONFLICT (channel, external_message_id)
            WHERE direction = 'IN' AND external_message_id IS NOT NULL
            DO NOTHING
        RETURNING id
    """, (identidad.get("chat_link_id"), identidad["hub_user_id"], ext, kind, contenido))
    row = cur.fetchone()
    return (row[0], False) if row else (None, True)


def _reparar_sin_chat(cur):
    """SMS que llegaron sin chat vinculado: al vincular, entran a la cola."""
    cur.execute("""
        UPDATE bot_messages m
           SET kind = 'sms', chat_link_id = l.id
          FROM bot_chat_links l
         WHERE m.channel = 'sms' AND m.direction = 'IN' AND m.kind = 'sms_sin_chat'
           AND l.hub_user_id::text = m.raw_chat_id
           AND l.channel = 'telegram' AND l.status = 'ACTIVO'
    """)


def _procesar_uno(conn, cur, fila, send_fn):
    from bot_driver import (SCHEMA_VERSION, _botones_borrador, guardar_summary_message_id,
                            log_outbound, render_summary)
    msg_id, content, chat_link_id, raw_chat_id, ext_id = fila
    datos = json.loads(content) if isinstance(content, str) else (content or {})
    texto = (datos.get("text") or "").strip()
    remitente = datos.get("from") or REMITENTE_DEFAULT

    cur.execute("""
        SELECT id, chat_id, hub_user_id, default_portfolio, status
          FROM bot_chat_links WHERE id = %s
    """, (chat_link_id,))
    link = cur.fetchone()
    if not link or link[4] != "ACTIVO":
        # Se vuelve a la sala de espera; _reparar_sin_chat lo retoma al vincular.
        cur.execute("UPDATE bot_messages SET kind = 'sms_sin_chat', chat_link_id = NULL WHERE id = %s",
                    (msg_id,))
        conn.commit()
        return False
    link_id, chat_id, hub_user_id, portafolio, _ = link

    res = construir_borrador_sms(cur, texto, remitente, portafolio or "Personal")
    payload = res["payload"]
    cur.execute("""
        INSERT INTO transaction_drafts
            (chat_link_id, user_id, channel, portfolio_name, status, schema_version,
             payload, raw_text, media_paths, external_message_id)
        VALUES (%s, %s, 'sms', %s, 'BORRADOR', %s, %s, %s, '[]', %s)
        RETURNING id
    """, (link_id, str(hub_user_id), payload["portfolio_name"], SCHEMA_VERSION,
          json.dumps(payload), texto, ext_id))
    draft_id = cur.fetchone()[0]
    cur.execute("UPDATE bot_messages SET draft_id = %s WHERE id = %s", (draft_id, msg_id))
    conn.commit()                     # el borrador queda firme ANTES de hablar con Telegram

    resumen = encabezado_sms(res) + render_summary(draft_id, payload,
                                                   res["inferred_fields"], res["missing_fields"])
    mid = send_fn(str(chat_id), resumen, buttons=_botones_borrador(draft_id))
    if mid:
        guardar_summary_message_id(draft_id, mid)
    log_outbound("telegram", str(chat_id), resumen, link_id, draft_id)
    return True


def _marcar_error(conn, cur, fila, error, send_fn):
    """La fila no vuelve a tomarse (kind='sms_error'); el texto sigue ahí y se avisa."""
    msg_id, _content, chat_link_id, raw_chat_id, _ext = fila
    try:
        cur.execute("UPDATE bot_messages SET kind = 'sms_error' WHERE id = %s", (msg_id,))
        cur.execute("""
            INSERT INTO bot_messages (chat_link_id, raw_chat_id, direction, channel, kind, content)
            VALUES (%s, %s, 'OUT', 'sms', 'sms_error', %s)
        """, (chat_link_id, raw_chat_id, f"msg {msg_id}: {error}"[:2000]))
        conn.commit()
        if chat_link_id:
            cur.execute("SELECT chat_id FROM bot_chat_links WHERE id = %s", (chat_link_id,))
            row = cur.fetchone()
            if row:
                send_fn(str(row[0]),
                        f"⚠ No pude convertir un SMS en borrador (mensaje {msg_id}): {error}\n"
                        "El texto quedó guardado; revísalo en la Bandeja web.")
    except Exception as e2:
        try:
            conn.rollback()
        except Exception:
            pass
        print(f"⚠️ [SMS] No se pudo marcar el error del mensaje {msg_id}: {e2}")


def procesar_pendientes(send_fn, conn=None, limite=20) -> int:
    """Tick del poller: SMS encolados → borradores → Telegram. → nº convertidos.
    Jamás lanza (patrón tick_resumen_telegram)."""
    from db_pool import get_conn, put_conn
    propia = conn is None
    n = 0
    try:
        if propia:
            conn = get_conn()
        cur = conn.cursor()
        _reparar_sin_chat(cur)
        conn.commit()
        cur.execute("""
            SELECT id, content, chat_link_id, raw_chat_id, external_message_id
              FROM bot_messages
             WHERE channel = 'sms' AND direction = 'IN' AND kind = 'sms' AND draft_id IS NULL
             ORDER BY id LIMIT %s
        """, (int(limite),))
        filas = cur.fetchall()
        for fila in filas:
            try:
                if _procesar_uno(conn, cur, fila, send_fn):
                    n += 1
            except Exception as e:
                try:
                    conn.rollback()
                except Exception:
                    pass
                _marcar_error(conn, cur, fila, e, send_fn)
        cur.close()
    except Exception as e:
        print(f"⚠️ [SMS] tick falló (se reintenta en la próxima vuelta): {e}")
        try:
            if conn is not None:
                conn.rollback()
        except Exception:
            pass
    finally:
        if propia and conn is not None:
            put_conn(conn)
    return n
