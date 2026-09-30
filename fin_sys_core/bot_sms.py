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
from sms_bancolombia import REMITENTE_DEFAULT, extraer_generico, parsear, tiene_dinero

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


def resolver_tercero_por_nombre(cur, nombre):
    """→ dict del tercero si UNA fila de third_parties se llama EXACTAMENTE así
    (sin mayúsculas ni espacios de más — misma igualdad que usa la web en
    database_driver._asegurar_tercero). Sirve para el comercio de una compra
    ("Didi") y el remitente de una transferencia recibida ("SANDRA JIMENEZ").
    Parecidos NO cuentan: 0 ó >1 → None y el humano lo asigna (09.G)."""
    nombre = re.sub(r"\s+", " ", str(nombre or "")).strip()
    if len(nombre) < 2:
        return None
    cur.execute("""
        SELECT identification_type, identification_number, name, phone
          FROM third_parties
         WHERE lower(btrim(name)) = lower(%s) AND identification_number <> '999999999'
         ORDER BY id
    """, (nombre,))
    filas = cur.fetchall()
    if len(filas) != 1:
        return None
    t, n, nom, tel = filas[0]
    d = {"identification_type": t, "identification_number": n, "name": nom}
    if tel:
        d["phone"] = tel
    return d


def concepto_sms(sms, transferencia_propia=False) -> str:
    """Traducción literal del SMS (no una adivinanza): lo que dice el banco."""
    if not sms:
        return ""
    fam, o = sms["familia"], sms.get("origen_last4")
    if fam == "transferencia_enviada":
        if transferencia_propia:
            return f"Transferencia entre cuentas *{o} → *{sms['destino_last4']} (SMS)"
        return f"Transferencia Bancolombia *{o} → *{sms['destino_last4']} (SMS)"
    if fam == "compra_tarjeta":
        tarjeta = "T.Cred" if sms.get("tarjeta_tipo") == "credito" else "T.Deb"
        return f"Compra en {sms.get('contraparte_nombre') or '—'} con {tarjeta} *{o} (SMS)"
    if fam == "transferencia_recibida":
        return f"Transferencia recibida de {sms.get('contraparte_nombre') or '—'} en *{o} (SMS)"
    if fam == "pago_qr":
        return f"Pago con QR a la llave {sms.get('destino') or '—'} desde *{o} (SMS)"
    return f"{fam} (SMS)"


def mapear_a_parsed(sms, cuenta_nombre=None, tercero=None, transferencia_propia=False) -> dict:
    """Forma exacta que consume draft_builder.build_payload. SMS None = no reconocido."""
    if sms is None:
        return {"type": "GASTO", "amount": None, "concept": "", "payment_method": "",
                "category": None, "third_party": {}, "is_recurring": False,
                "inferred_fields": ["type"]}
    if transferencia_propia:
        tipo, inferidos = "TRANSFERENCIA", []
    else:
        # "Compraste", "Recibiste" y "pagaste" no dejan duda del tipo; solo
        # "Transferiste" queda inferido (podría ser entre cuentas propias).
        tipo = sms.get("tipo_sugerido") or "GASTO"
        inferidos = ["type"] if sms.get("tipo_inferido", True) else []
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
        # MI cuenta: por número (transferencias, QR, recibidas) o por tarjeta (compras)
        account_id, cuenta_nombre = resolver_cuenta_por_last4(
            cur, sms["origen_last4"], campo=sms.get("origen_campo") or "last4_cuenta")
        if sms.get("destino_es_celular"):
            tercero = resolver_tercero_por_celular(cur, sms["destino"])
        elif sms.get("contraparte_nombre"):
            # Comercio o remitente: solo igualdad exacta de nombre, un candidato
            tercero = resolver_tercero_por_nombre(cur, sms["contraparte_nombre"])
        elif sms["familia"] == "transferencia_enviada" and sms.get("destino_last4"):
            # ¿El destino es otra cuenta MÍA? → transferencia entre cuentas (determinista)
            dest_account_id, _ = resolver_cuenta_por_last4(cur, sms["destino_last4"])

    # Plantilla DESCONOCIDA pero con dinero (R-09F-13): lectura literal de
    # monto, fecha y de MI cuenta si exactamente UNO de los *NNNN del texto
    # está registrado (cuenta o tarjeta). Todo queda marcado "inferido" y el
    # concepto vacío: el borrador exige revisión humana antes de confirmar.
    generico = None
    if sms is None and tiene_dinero(texto_sms):
        generico = extraer_generico(texto_sms)
        mias = {}
        for l4 in generico["last4_candidatos"]:
            for campo in _CAMPOS_LAST4:
                aid, nom = resolver_cuenta_por_last4(cur, l4, campo=campo)
                if aid:
                    mias[aid] = nom
        if len(mias) == 1:
            account_id, cuenta_nombre = next(iter(mias.items()))

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

    fuente = sms or generico or {}
    if generico:
        payload["amount"] = generico.get("amount")
        inferred.append("amount")
        if account_id:
            inferred.append("payment_method")   # no se sabe si es origen o destino

    # Fecha del SMS (build_payload siempre pone hoy)
    if fuente.get("fecha"):
        payload["transaction_date"] = fuente["fecha"]
    else:
        payload["transaction_date"] = date.today().isoformat()
        inferred.append("transaction_date")
    if fuente.get("currency") and fuente["currency"] != "COP":
        payload["transaction_currency"] = fuente["currency"]

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
        # Lo que el banco escribió de la contraparte (comercio / remitente):
        # queda a la vista para asignar el tercero a mano si no hubo igualdad.
        "contraparte": sms.get("contraparte_nombre") if sms else None,
        "origen_campo": sms.get("origen_campo") if sms else None,
        "plantilla_nueva": bool(generico),
    }
    return {"payload": payload, "inferred_fields": inferred, "missing_fields": missing,
            "sms": sms, "reconocido": sms is not None, "account_id": account_id,
            # True = texto sin familia pero con dinero (se leyó monto/fecha literal)
            "plantilla_nueva": bool(generico),
            # True = ni familia ni dinero: aviso informativo, NO es un movimiento
            "informativo": sms is None and not generico}


def encabezado_sms(res) -> str:
    """Prefijo del resumen (mismo patrón que '📎 Evidencia adjunta.' en bot_driver)."""
    remitente = (res.get("payload") or {}).get("sms", {}).get("remitente") or REMITENTE_DEFAULT
    lineas = [f"📲 SMS Bancolombia ({remitente})"]
    if res.get("plantilla_nueva"):
        lineas.append("⚠️ PLANTILLA NUEVA de SMS — leí monto y fecha tal cual aparecen; revisa el "
                      "tipo y la cuenta, y responde \"Concepto: …\". Avisa para agregar esta "
                      "plantilla al sistema (el texto completo queda guardado en el borrador).")
    elif not res.get("reconocido"):
        lineas.append("⚠️ SMS no reconocido — completa monto y concepto en la Bandeja web")
    elif not res.get("account_id"):
        sms = res.get("sms") or {}
        origen = sms.get("origen_last4") or "????"
        if sms.get("origen_campo") == "last4_tarjeta":
            lineas.append(f"⚠️ Tarjeta *{origen} no registrada — ponle sus últimos 4 dígitos "
                          "en 💳 Cuentas (campo tarjeta) y edita el borrador en la web")
        else:
            lineas.append(f"⚠️ Cuenta *{origen} no registrada — ponle sus últimos 4 dígitos "
                          "en 💳 Cuentas y edita el borrador en la web")
    # Contraparte que el banco nombró pero no existe (igual) en Terceros
    sms = res.get("sms") or {}
    tp = (res.get("payload") or {}).get("third_party") or {}
    if sms.get("contraparte_nombre") and tp.get("identification_number") == "999999999":
        lineas.append(f"👤 El banco dice: {sms['contraparte_nombre']} — asígnalo con el botón "
                      "👤 Tercero o respondiendo \"Tercero: …\"")
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
    if res.get("informativo"):
        # Aviso sin dinero ("Inscribiste la cuenta de un tercero…", claves,
        # alertas de seguridad): no es un movimiento → sin borrador y sin
        # ruido en el chat. El texto queda en bot_messages (kind='sms_info',
        # retención 90 días) por si hay que revisarlo.
        cur.execute("UPDATE bot_messages SET kind = 'sms_info' WHERE id = %s", (msg_id,))
        conn.commit()
        return False
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
    if res.get("plantilla_nueva"):
        resumen += f"\n\n📩 Texto del SMS:\n{texto[:600]}"
    mid = send_fn(str(chat_id), resumen, buttons=_botones_borrador(draft_id))
    if mid:
        guardar_summary_message_id(draft_id, mid)
    log_outbound("telegram", str(chat_id), resumen, link_id, draft_id)
    return True


def borrador_desde_chat(cur, link, texto, msg, msg_row_id):
    """SMS del banco PEGADO o REENVIADO al chat de Telegram (plan B cuando el
    teléfono no pudo enviarlo al webhook: PC apagado, túnel caído).
    Solo actúa si el texto es de una familia conocida; cualquier otra cosa
    devuelve None y sigue el flujo normal del bot. Mismo parser determinista,
    jamás el LLM. Si ese SMS ya había llegado por el webhook, no se duplica."""
    texto = (texto or "").strip()
    if parsear(texto) is None:
        return None
    from bot_driver import SCHEMA_VERSION, _botones_borrador, render_summary
    clave = clave_dedupe(REMITENTE_DEFAULT, texto)
    cur.execute("""
        SELECT draft_id FROM bot_messages
         WHERE channel = 'sms' AND direction = 'IN' AND external_message_id = %s
           AND draft_id IS NOT NULL
    """, (clave,))
    ya = cur.fetchone()
    if ya:
        return f"Ese SMS ya llegó por el teléfono: es el borrador #{ya[0]} (/borradores)."
    cur.execute("""
        SELECT id FROM transaction_drafts
         WHERE chat_link_id = %s AND raw_text = %s AND status <> 'DESCARTADO'
         ORDER BY id DESC LIMIT 1
    """, (link["id"], texto))
    ya = cur.fetchone()
    if ya:
        return f"Ese SMS ya lo registraste: es el borrador #{ya[0]} (/borradores)."

    res = construir_borrador_sms(cur, texto, REMITENTE_DEFAULT, link.get("default_portfolio") or "Personal")
    payload = res["payload"]
    cur.execute("""
        INSERT INTO transaction_drafts
            (chat_link_id, user_id, channel, portfolio_name, status, schema_version,
             payload, raw_text, media_paths, external_message_id)
        VALUES (%s, %s, %s, %s, 'BORRADOR', %s, %s, %s, '[]', %s)
        RETURNING id
    """, (link["id"], str(link["hub_user_id"]), msg.get("channel") or "telegram",
          payload["portfolio_name"], SCHEMA_VERSION, json.dumps(payload), texto,
          str(msg.get("external_message_id") or clave)))
    draft_id = cur.fetchone()[0]
    cur.execute("UPDATE bot_messages SET draft_id = %s, chat_link_id = %s WHERE id = %s",
                (draft_id, link["id"], msg_row_id))
    return {"text": encabezado_sms(res) + render_summary(draft_id, payload,
                                                         res["inferred_fields"], res["missing_fields"]),
            "draft_id": draft_id, "buttons": _botones_borrador(draft_id)}


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
