# -*- coding: utf-8 -*-
"""FIN-SYS OS v2.0 — Módulo 09: núcleo canal-agnóstico del Bot IA.

Recibe mensajes normalizados (InboundMessage como dict) de cualquier adaptador
(Telegram hoy, WhatsApp en Etapa D) y devuelve la respuesta de texto. No sabe
nada de las APIs de los canales.

Regla 6 (no negociable): el LLM solo PROPONE — todo nace como fila en
transaction_drafts y solo una confirmación humana explícita ("Confirmar #N")
ejecuta el pipeline oficial (transaction_service.create_transaction).

Máquina de estados del borrador:
    BORRADOR → PROCESANDO → CONFIRMADO | ERROR
    BORRADOR → DESCARTADO
La transición a PROCESANDO es una actualización condicional: solo una petición
gana (chat y web no pueden doble-confirmar). Un PROCESANDO atascado >5 min se
puede retomar.

InboundMessage = {
    "channel": "telegram" | "whatsapp",
    "chat_id": str,
    "external_message_id": str,   # update_id (TG) / wamid (WA) — clave de dedupe
    "kind": "text" | "audio" | "unsupported",
    "text": str | None,
    "media_path": str | None,     # ruta FS relativa (p.ej. "uploads/x.ogg")
}
"""
import json
import re

# Fuente ÚNICA de inferencia — compartida con la Ingestión por Voz de la web
from draft_builder import (          # noqa: F401  (re-exportadas para tests)
    TIPOS_VALIDOS,
    build_draft,
    build_payload,
    compute_missing,
    fmt_money as _fmt_money,
    norm as _norm,
    resolver_cuenta as _resolver_cuenta,
    resolver_metodo_pago as _resolver_metodo_pago,
    resolver_portafolio as _resolver_portafolio,
)

SCHEMA_VERSION = 1

AYUDA = (
    "🤖 FIN-SYS Bot — registro contable por chat\n\n"
    "Envíame un gasto o ingreso en lenguaje natural, por texto o nota de voz:\n"
    "  \"Gasté 45.000 en almuerzo con Juan, pagué desde Bancolombia\"\n\n"
    "📸 También acepto FOTOS de comprobantes:\n"
    "  · Foto con texto → crea el borrador con la foto como evidencia\n"
    "  · Foto respondiendo a un borrador → se adjunta a ESE borrador\n"
    "  · Foto suelta → se adjunta a tu último borrador pendiente\n\n"
    "📍 Y UBICACIÓN (clip 📎 → Ubicación): se adjunta al borrador igual que\n"
    "la foto y queda como link de Maps en la transacción.\n\n"
    "Yo lo convierto en un BORRADOR. Nada toca tu contabilidad hasta que\n"
    "confirmes (botón ✅ o \"Confirmar #N\").\n\n"
    "Comandos:\n"
    "  Confirmar #N — oficializa el borrador (crea transacción + asiento)\n"
    "  Descartar #N — elimina el borrador\n"
    "  /empresa — muestra o cambia la empresa donde registro por defecto\n"
    "  /borradores — lista tus borradores pendientes\n"
    "  /analisis <pregunta> — cifras del catálogo con gráfica, sobre la\n"
    "    empresa por defecto del chat (ej: /analisis cuánto gasté este mes)\n"
    "  /resumen — el resumen automático consolidado, ya mismo\n"
    "  /ayuda — este mensaje\n\n"
    "Para completar un borrador (también los que llegan por SMS 📲),\n"
    "RESPONDE (reply) a su mensaje. Puedes mandar todo junto:\n"
    "    abono cuota 1\n"
    "    Tercero: Leidy Molina cc 1007289007\n"
    "  · lo que va sin marca es el concepto\n"
    "  · \"Tercero: nombre\" busca uno existente (o un número: documento o\n"
    "    celular); con \"cc\"/\"nit\" y el número lo crea si no existe —\n"
    "    el documento manda, así que nunca se duplica\n"
    "  · \"Tercero nuevo: Nombre\" lo crea sin documento (provisional)\n"
    "  · el botón 👤 Tercero muestra los más recientes\n"
    "  · 💾 Guardar (borradores de SMS): registra la cuenta, celular o llave\n"
    "    del SMS en la ficha del tercero — la próxima vez el borrador llega\n"
    "    con ese tercero ya puesto. Nada se guarda solo.\n"
    "Para corregir lo demás: 🏢 Cambiar empresa, o edítalo en la Bandeja web."
)

NO_VINCULADO = (
    "🔒 Este bot es privado.\n"
    "Para vincular tu cuenta: entra a FIN-SYS en la web, genera un código de\n"
    "vinculación y envíame: /vincular TUCODIGO"
)

NO_SOPORTADO = (
    "Por ahora entiendo texto, notas de voz, fotos de comprobantes y "
    "ubicación 📍.\nStickers y documentos llegan en una próxima etapa."
)

# ── Comandos deterministas (regex — confirmar/descartar JAMÁS pasan por el LLM) ──
_RE_CONFIRM = re.compile(r"^\s*/?confirmar\s*#?\s*(\d+)?\s*$", re.IGNORECASE)
_RE_DISCARD = re.compile(r"^\s*/?descartar\s*#?\s*(\d+)?\s*$", re.IGNORECASE)
_RE_LINK    = re.compile(r"^\s*/?vincular\s+([A-Za-z0-9]{4,12})\s*$", re.IGNORECASE)
_RE_AYUDA   = re.compile(r"^\s*/(start|ayuda|help)\s*$", re.IGNORECASE)
_RE_DRAFTS  = re.compile(r"^\s*/?borradores\s*$", re.IGNORECASE)
_RE_EMPRESA = re.compile(r"^\s*/empresa\s*(.*)$", re.IGNORECASE)
# Hito 3 Análisis Inteligente: comando EXPLÍCITO (regla 6b: el bot no
# adivina — una pregunta jamás se confunde con un registro de gasto).
# El comando PELADO también matchea (arg None): responde el ejemplo de uso
# en vez de caer al registrador y fabricar un borrador basura de $0
# (visto en prod el 22-sep con "/pregunta" suelto).
_RE_ANALISIS = re.compile(r"^\s*/(?:analisis|análisis|pregunta)\b\s*(.*)$",
                          re.IGNORECASE | re.DOTALL)
_RE_RESUMEN  = re.compile(r"^\s*/resumen\s*$", re.IGNORECASE)


def parse_command(text: str):
    """Clasifica un texto como comando determinista. → (cmd, arg) o (None, None)."""
    t = text or ""
    m = _RE_CONFIRM.match(t)
    if m:
        return "confirmar", int(m.group(1)) if m.group(1) else None
    m = _RE_DISCARD.match(t)
    if m:
        return "descartar", int(m.group(1)) if m.group(1) else None
    m = _RE_LINK.match(t)
    if m:
        return "vincular", m.group(1).upper()
    if _RE_AYUDA.match(t):
        return "ayuda", None
    if _RE_DRAFTS.match(t):
        return "borradores", None
    m = _RE_EMPRESA.match(t)
    if m:
        return "empresa", (m.group(1) or "").strip() or None
    m = _RE_ANALISIS.match(t)
    if m:
        return "analisis", m.group(1).strip() or None
    if _RE_RESUMEN.match(t):
        return "resumen", None
    return None, None


def render_summary(draft_id: int, payload: dict, inferred=None, missing=None) -> str:
    """Resumen legible del borrador — lo que el humano revisa antes de confirmar."""
    inferred = set(inferred or payload.get("inferred_fields") or [])
    missing = missing if missing is not None else payload.get("missing_fields") or []

    def _inf(campo):
        return " (inferido)" if campo in inferred else ""

    tp = payload.get("third_party") or {}
    lineas = [
        f"🧾 BORRADOR #{draft_id}",
        f"Tipo: {payload.get('type')}",
        f"Monto: {_fmt_money(payload.get('amount'))} COP" + _inf("amount"),
        f"Concepto: {payload.get('concept') or '—'}",
        f"Categoría: {payload.get('category')}" + _inf("category"),
        f"Pago: {payload.get('payment_method')}" + _inf("payment_method"),
        f"Tercero: {tp.get('name')} ({tp.get('identification_type')} {tp.get('identification_number')})" + _inf("third_party"),
    ]
    contacto = [v for v in (tp.get("phone") and f"📞 {tp['phone']}",
                            tp.get("email") and f"✉ {tp['email']}",
                            tp.get("address") and f"🏠 {tp['address']}") if v]
    if contacto:
        lineas.append("  " + " · ".join(contacto))
    lineas += [
        f"Fecha: {payload.get('transaction_date')}",
        f"Portafolio: {payload.get('portfolio_name')}",
    ]
    if payload.get("tags"):
        lineas.append(f"🏷️ Etiquetas: {', '.join(payload['tags'])}")
    if payload.get("geo_maps_link"):
        lineas.append("📍 Ubicación adjunta")
    if payload.get("apply_iva"):
        lineas.append("IVA 19%: se calculará al confirmar")
    if missing:
        lineas.append(f"\n⚠ Falta: {', '.join(missing)} — descarta y reenvía la operación completa")
    lineas.append(f"\nResponde:\n▸ Confirmar #{draft_id}\n▸ Descartar #{draft_id}")
    return "\n".join(lineas)


# ══════════════════════════════════════════════════════════════════════════════
# Entrada principal (canal-agnóstica)
# ══════════════════════════════════════════════════════════════════════════════

def handle_message(msg: dict):
    """Procesa un InboundMessage. Devuelve:
      · None — duplicado ya procesado
      · str — respuesta de texto plano
      · dict {"text", "draft_id", "buttons"} — resumen de borrador con botones
        inline (Etapa E); el adaptador del canal decide cómo pintarlos.
        Puede traer "photo_png_base64" (hito 3: gráfica del análisis) — el
        adaptador la envía como foto después del texto."""
    from db_pool import get_conn, put_conn
    conn = get_conn()
    try:
        cur = conn.cursor()

        msg_row_id = _registrar_entrante(cur, msg)
        if msg_row_id is None:          # duplicado (re-poll / reintento)
            conn.commit()
            return None

        link = _get_link(cur, msg["channel"], msg["chat_id"])
        cmd, arg = parse_command(msg.get("text") or "")

        # ── Chat NO vinculado: solo se atiende /vincular ──
        if link is None or link["status"] != "ACTIVO":
            reply = _flujo_no_vinculado(cur, msg, cmd, arg)
            conn.commit()
            return reply

        # ── Comandos deterministas ──
        if cmd == "ayuda":
            conn.commit()
            return AYUDA
        if cmd == "vincular":
            conn.commit()
            return "✅ Este chat ya está vinculado. Envíame un gasto o ingreso, o /ayuda."
        if cmd == "borradores":
            reply = _listar_borradores(cur, link)
            conn.commit()
            return reply
        if cmd in ("confirmar", "descartar"):
            draft_id = arg if arg is not None else _unico_borrador(cur, link)
            conn.commit()               # persistir dedupe ANTES de confirmar
            if draft_id is None:
                return (f"¿Cuál borrador? Indícame el número: {cmd.capitalize()} #N\n"
                        "(/borradores para ver la lista)")
            if cmd == "confirmar":
                resultado = confirmar_draft(draft_id, chat_link_id=link["id"])
                texto, botones_medio = _confirmacion_con_medio(cur, link, draft_id, resultado)
                if botones_medio:             # 💾 igual que con el botón ✅
                    return {"text": texto, "buttons": botones_medio}
                return resultado
            return descartar_draft(draft_id, chat_link_id=link["id"])
        if cmd == "empresa":
            reply = _cmd_empresa(cur, link, arg)
            conn.commit()
            return reply

        # ── Hito 3 Análisis Inteligente: pregunta con cifras del catálogo ──
        # El dedupe se persiste ANTES de llamar al traductor (puede tardar).
        if cmd == "analisis":
            pid, nombre = _portafolio_del_chat(cur, link)
            conn.commit()
            return _responder_analisis(arg, pid, nombre)
        if cmd == "resumen":
            conn.commit()
            # El MISMO texto del envío periódico (consolidado), a demanda.
            from insight_engine import resumen_texto
            return resumen_texto(None)

        # ── 📸 Foto (Etapa E): evidencia de un borrador o borrador nuevo ──
        if msg.get("kind") == "photo":
            reply = _flujo_foto(cur, link, msg, msg_row_id)
            conn.commit()
            return reply

        # ── 📍 Ubicación (Etapa E.2): geolocalización del borrador ──
        if msg.get("kind") == "location":
            reply = _flujo_ubicacion(cur, link, msg)
            conn.commit()
            return reply

        # ── 📝 Texto RESPONDIENDO a un borrador (Etapa 09.G): completar
        #    tercero / concepto de ESE borrador, jamás crear otro ──
        if msg.get("kind") == "text" and msg.get("reply_to_message_id"):
            draft_id = _draft_por_reply(cur, link, msg)
            if draft_id is not None:
                reply = _flujo_reply(cur, link, draft_id, msg.get("text") or "")
                conn.commit()
                if reply is not None:
                    return reply

        # ── Entrada no soportada en el MVP ──
        if msg.get("kind") == "unsupported":
            conn.commit()
            return NO_SOPORTADO

        # ── Registro: texto libre o nota de voz → borrador ──
        texto = msg.get("text") or ""
        if msg.get("kind") == "audio":
            from ai_engine import transcribe_audio_only
            # transcribe_path: archivo local temporal (Whisper necesita FS);
            # media_path puede ser ya la URL del bucket (Etapa E).
            texto = transcribe_audio_only(msg.get("transcribe_path") or msg["media_path"])
            if not (texto or "").strip():
                conn.commit()
                return "No pude transcribir la nota de voz. Intenta de nuevo o escríbeme el movimiento."

        # ── SMS del banco pegado o reenviado al chat (etapa 09.F, plan B sin
        #    túnel): mismo parser determinista del webhook, jamás el LLM ──
        if msg.get("kind") == "text":
            from bot_sms import borrador_desde_chat
            reply = borrador_desde_chat(cur, link, texto, msg, msg_row_id)
            if reply is not None:
                conn.commit()
                return reply

        reply = _crear_borrador(cur, link, texto, msg, msg_row_id)
        conn.commit()
        return reply
    except Exception as e:
        conn.rollback()
        return f"⚠ Error procesando el mensaje: {e}"
    finally:
        put_conn(conn)


def _portafolio_del_chat(cur, link):
    """Empresa amarrada del chat para /analisis (criterio inmutable 2: la
    decide la vinculación, jamás el LLM). → (portfolio_id, nombre_visible)
    o (None, None) si el default no resuelve (se responde consolidado).
    El nombre visible prefiere el del Control Tower (idioma de Andrés)."""
    try:
        cur.execute("""
            SELECT p.id, COALESCE(NULLIF(btrim(e.name), ''), p.name)
              FROM portfolios p
              LEFT JOIN entities e ON e.portfolio_id = p.id
             WHERE p.name = %s
             LIMIT 1;
        """, (link.get("default_portfolio"),))
        fila = cur.fetchone()
        return (fila[0], fila[1]) if fila else (None, None)
    except Exception:
        return (None, None)


def _responder_analisis(pregunta: str, portfolio_id, nombre_portafolio):
    """Pregunta en español → la MISMA maquinaria de la web (analytics_qa).
    → dict {"text", "photo_png_base64"?} — el adaptador manda la foto aparte."""
    if not (pregunta or "").strip():
        return ("Dime la pregunta después del comando, por ejemplo:\n"
                "/analisis cuánto gasté este mes por categoría")
    try:
        from analytics_qa import responder_pregunta
        r = responder_pregunta(pregunta.strip(), portfolio_id=portfolio_id)
    except Exception as e:
        return f"⚠ El análisis falló: {e}"
    encabezado = (f"🏢 {nombre_portafolio}\n" if nombre_portafolio
                  else "🏢 Todas las empresas (consolidado)\n")
    out = {"text": encabezado + (r.get("texto") or "Sin respuesta.")}
    if r.get("grafica_png_base64"):
        out["photo_png_base64"] = r["grafica_png_base64"]
    return out


def log_outbound(channel: str, chat_id: str, content: str, chat_link_id=None, draft_id=None):
    """Auditoría de mensajes salientes (best-effort, nunca rompe el flujo)."""
    from db_pool import get_conn, put_conn
    try:
        conn = get_conn()
        try:
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO bot_messages (chat_link_id, raw_chat_id, direction, channel, kind, content, draft_id)
                VALUES (%s, %s, 'OUT', %s, 'text', %s, %s)
            """, (chat_link_id, str(chat_id), channel, (content or "")[:2000], draft_id))
            conn.commit()
        finally:
            put_conn(conn)
    except Exception:
        pass


# ══════════════════════════════════════════════════════════════════════════════
# Internos con BD
# ══════════════════════════════════════════════════════════════════════════════

def _registrar_entrante(cur, msg):
    """Inserta el mensaje IN con dedupe por (channel, external_message_id).
    → id de la fila, o None si ya se procesó (duplicado)."""
    cur.execute("""
        INSERT INTO bot_messages (raw_chat_id, direction, channel, external_message_id, kind, content)
        VALUES (%s, 'IN', %s, %s, %s, %s)
        ON CONFLICT (channel, external_message_id)
            WHERE direction = 'IN' AND external_message_id IS NOT NULL
            DO NOTHING
        RETURNING id
    """, (str(msg.get("chat_id")), msg["channel"], str(msg.get("external_message_id")),
          msg.get("kind"), (msg.get("text") or msg.get("media_path") or "")[:2000]))
    row = cur.fetchone()
    return row[0] if row else None


def _get_link(cur, channel, chat_id):
    cur.execute("""
        SELECT id, hub_user_id, default_portfolio, status
        FROM bot_chat_links WHERE channel = %s AND chat_id = %s
    """, (channel, str(chat_id)))
    row = cur.fetchone()
    if not row:
        return None
    return {"id": row[0], "hub_user_id": row[1],
            "default_portfolio": row[2] or "Personal", "status": row[3]}


def _flujo_no_vinculado(cur, msg, cmd, arg):
    if cmd != "vincular":
        return NO_VINCULADO

    # Anti fuerza bruta: máx. 5 códigos fallidos por chat por hora
    cur.execute("""
        SELECT COUNT(*) FROM bot_messages
        WHERE channel = %s AND raw_chat_id = %s AND kind = 'vincular_fail'
          AND created_at > NOW() - INTERVAL '1 hour'
    """, (msg["channel"], str(msg["chat_id"])))
    if cur.fetchone()[0] >= 5:
        return "Demasiados intentos fallidos. Espera una hora y genera un código nuevo en la web."

    import hashlib
    code_hash = hashlib.sha256(arg.upper().encode()).hexdigest()
    cur.execute("""
        UPDATE bot_link_codes SET used = TRUE
        WHERE code_hash = %s AND NOT used AND expires_at > NOW()
        RETURNING hub_user_id
    """, (code_hash,))
    row = cur.fetchone()
    if not row:
        cur.execute("""
            INSERT INTO bot_messages (raw_chat_id, direction, channel, kind, content)
            VALUES (%s, 'OUT', %s, 'vincular_fail', 'código inválido o expirado')
        """, (str(msg["chat_id"]), msg["channel"]))
        return "Código inválido o expirado. Genera uno nuevo en FIN-SYS (web) — dura 10 minutos."

    hub_user_id = row[0]
    # Portafolio por defecto: uno REAL de esta instalación (nunca un literal
    # que podría no existir y bloquear la confirmación más tarde).
    portafolio, _ = _resolver_portafolio(cur, "")
    cur.execute("""
        INSERT INTO bot_chat_links (channel, chat_id, hub_user_id, status, default_portfolio)
        VALUES (%s, %s, %s, 'ACTIVO', %s)
        ON CONFLICT (channel, chat_id)
            DO UPDATE SET hub_user_id = EXCLUDED.hub_user_id, status = 'ACTIVO',
                          default_portfolio = EXCLUDED.default_portfolio
    """, (msg["channel"], str(msg["chat_id"]), hub_user_id, portafolio))
    cur.execute("SELECT name FROM hub_users WHERE id = %s", (hub_user_id,))
    nombre = (cur.fetchone() or ["?"])[0]
    extra = f"\nPortafolio por defecto: {portafolio}" if portafolio else ""
    return f"✅ Chat vinculado a {nombre}.{extra}\n\n{AYUDA}"


def _crear_borrador(cur, link, texto, msg, msg_row_id):
    """Texto → LLM → payload validado → fila en transaction_drafts → resumen."""
    if not (texto or "").strip():
        return "No recibí contenido. Cuéntame el movimiento (\"gasté 20.000 en taxi\") o /ayuda."

    from ai_engine import structure_text_only

    # El portafolio se valida ANTES de llamar al LLM: si el default del chat no
    # existe (config vieja), se corrige aquí y no al confirmar — el humano lo ve
    # en el resumen, que es donde debe enterarse.
    portafolio, _ = _resolver_portafolio(cur, link["default_portfolio"])
    if portafolio is None:
        return ("No hay portafolios creados en FIN-SYS. Crea uno en la web antes "
                "de registrar movimientos por chat.")

    parsed = structure_text_only(texto, portafolio)

    # Misma inferencia que la Ingestión por Voz de la web (draft_builder):
    # portafolio validado, método de pago cruzado con las cuentas reales
    # (lo que el usuario DIJO manda sobre lo que el LLM propuso) y account_id.
    draft = build_draft(cur, parsed, texto, portafolio)
    payload = draft["payload"]
    inferred = draft["inferred_fields"]
    missing = draft["missing_fields"]

    media_db = None
    if msg.get("media_path"):
        media_db = str(msg["media_path"]).replace("\\", "/")
        if not media_db.startswith("http"):     # URL del bucket va tal cual
            media_db = "/" + media_db.lstrip("/")

    cur.execute("""
        INSERT INTO transaction_drafts
            (chat_link_id, user_id, channel, portfolio_name, status, schema_version,
             payload, raw_text, media_path, media_paths, external_message_id)
        VALUES (%s, %s, %s, %s, 'BORRADOR', %s, %s, %s, %s, %s, %s)
        RETURNING id
    """, (link["id"], link["hub_user_id"], msg["channel"], payload["portfolio_name"],
          SCHEMA_VERSION, json.dumps(payload), texto, media_db,
          json.dumps([media_db] if media_db else []),
          str(msg.get("external_message_id"))))
    draft_id = cur.fetchone()[0]
    cur.execute("UPDATE bot_messages SET draft_id = %s, chat_link_id = %s WHERE id = %s",
                (draft_id, link["id"], msg_row_id))
    texto_resumen = render_summary(draft_id, payload, inferred, missing)
    if msg.get("media_path"):
        texto_resumen = "📎 Evidencia adjunta.\n" + texto_resumen
    return {"text": texto_resumen, "draft_id": draft_id,
            "buttons": _botones_borrador(draft_id)}


def _botones_borrador(draft_id: int):
    """Botonera estándar bajo el resumen (Etapa E). Formato canal-agnóstico:
    filas de (etiqueta, callback_data). El texto 'Confirmar #N' del resumen
    se mantiene como fallback para canales sin botones."""
    return [
        [("✅ Confirmar", f"ok:{draft_id}"), ("❌ Descartar", f"no:{draft_id}")],
        [("🏢 Cambiar empresa", f"emp:{draft_id}"), ("🏷️ Etiquetas", f"tags:{draft_id}")],
        # Etapa 09.G: completar el borrador sin salir del chat (Regla 6b: el
        # tercero sale de third_parties o lo crea el humano; nada se adivina)
        [("👤 Tercero", f"tp:{draft_id}"), ("📝 Concepto", f"cpt:{draft_id}")],
        [("💤 Dejar en borrador", f"hold:{draft_id}")],
    ]


def _flujo_foto(cur, link, msg, msg_row_id):
    """📸 Foto entrante (ya subida al bucket por el adaptador — media_path=URL).

    Reglas acordadas con Andrés (2026-09-09, cero inferencia):
      · con texto (caption) → borrador NUEVO con la foto como evidencia
      · respondiendo al mensaje de un borrador → evidencia de ESE borrador
      · suelta → evidencia del ÚLTIMO borrador pendiente (se le informa cuál)
    """
    if not msg.get("media_path"):
        return ("No pude guardar la foto (falló la subida al archivo). "
                "Inténtalo de nuevo en un momento.")

    texto = (msg.get("text") or "").strip()
    if texto:
        return _crear_borrador(cur, link, texto, msg, msg_row_id)

    # ¿Es respuesta al mensaje-resumen de un borrador?
    draft_id = None
    if msg.get("reply_to_message_id"):
        cur.execute("""
            SELECT id FROM transaction_drafts
            WHERE chat_link_id = %s AND bot_summary_message_id = %s
        """, (link["id"], str(msg["reply_to_message_id"])))
        row = cur.fetchone()
        draft_id = row[0] if row else None

    if draft_id is None:
        cur.execute("""
            SELECT id FROM transaction_drafts
            WHERE chat_link_id = %s AND status = 'BORRADOR'
            ORDER BY id DESC LIMIT 1
        """, (link["id"],))
        row = cur.fetchone()
        draft_id = row[0] if row else None

    if draft_id is None:
        return ("Recibí la foto pero no tienes borradores pendientes.\n"
                "Envíala de nuevo CON un texto describiendo el movimiento "
                "(ej: \"mercado 45.000\") y creo el borrador con la foto "
                "como evidencia.")

    return _adjuntar_evidencia(cur, link, draft_id, msg["media_path"])


def _adjuntar_evidencia(cur, link, draft_id, url):
    """AÑADE una evidencia al borrador (Etapa E.3: pueden ser varias — 2 o 3
    fotos, o foto + PDF). media_path (singular) queda = la primera, por
    compat con la bandeja. Devuelve la botonera de nuevo."""
    cur.execute("""
        SELECT media_path, media_paths FROM transaction_drafts
         WHERE id = %s AND chat_link_id = %s AND status IN ('BORRADOR', 'ERROR')
         FOR UPDATE
    """, (draft_id, link["id"]))
    row = cur.fetchone()
    if not row:
        return (f"El borrador #{draft_id} ya no es editable (¿confirmado o "
                "descartado?). Envía la foto con texto para crear uno nuevo.")
    principal, lista = row
    lista = lista if isinstance(lista, list) else json.loads(lista or "[]")
    if not lista and principal:      # borradores anteriores a media_paths
        lista = [principal]
    if url not in lista:
        lista.append(url)
    cur.execute("""
        UPDATE transaction_drafts
           SET media_path = %s, media_paths = %s, updated_at = NOW()
         WHERE id = %s
    """, (lista[0], json.dumps(lista), draft_id))
    n = len(lista)
    texto = (f"📎 Evidencia adjuntada al borrador #{draft_id}." if n == 1 else
             f"📎 Evidencia {n} adjuntada al borrador #{draft_id} (van {n}).")
    return {"text": texto, "draft_id": draft_id,
            "buttons": _botones_borrador(draft_id)}


def _flujo_ubicacion(cur, link, msg):
    """📍 Ubicación de Telegram (Etapa E.2): igual que la foto suelta —
    respondiendo al resumen va a ESE borrador; suelta, al último pendiente.
    Solo se guarda cuando TÚ la envías explícitamente (cero rastreo)."""
    lat, lon = msg.get("latitude"), msg.get("longitude")
    if lat is None or lon is None:
        return NO_SOPORTADO

    draft_id = None
    if msg.get("reply_to_message_id"):
        cur.execute("""
            SELECT id FROM transaction_drafts
            WHERE chat_link_id = %s AND bot_summary_message_id = %s
        """, (link["id"], str(msg["reply_to_message_id"])))
        row = cur.fetchone()
        draft_id = row[0] if row else None
    if draft_id is None:
        cur.execute("""
            SELECT id FROM transaction_drafts
            WHERE chat_link_id = %s AND status = 'BORRADOR'
            ORDER BY id DESC LIMIT 1
        """, (link["id"],))
        row = cur.fetchone()
        draft_id = row[0] if row else None
    if draft_id is None:
        return ("Recibí la ubicación pero no tienes borradores pendientes.\n"
                "Primero envíame el gasto/ingreso y luego la ubicación.")

    cur.execute("""
        SELECT payload FROM transaction_drafts
         WHERE id = %s AND chat_link_id = %s AND status IN ('BORRADOR', 'ERROR')
         FOR UPDATE
    """, (draft_id, link["id"]))
    row = cur.fetchone()
    if not row:
        return f"El borrador #{draft_id} ya no es editable."
    payload = row[0] if isinstance(row[0], dict) else json.loads(row[0])
    payload["geo_latitude"] = float(lat)
    payload["geo_longitude"] = float(lon)
    payload["geo_maps_link"] = f"https://www.google.com/maps?q={float(lat)},{float(lon)}"
    cur.execute("""
        UPDATE transaction_drafts SET payload = %s, updated_at = NOW()
        WHERE id = %s
    """, (json.dumps(payload), draft_id))
    return {"text": f"📍 Ubicación adjuntada al borrador #{draft_id}.",
            "draft_id": draft_id, "buttons": _botones_borrador(draft_id)}


# ══════════════════════════════════════════════════════════════════════════════
# Etapa 09.G — completar tercero y concepto desde el chat (Regla 6b: el
# tercero sale de third_parties o lo dicta el humano; el concepto es literal)
# ══════════════════════════════════════════════════════════════════════════════

_TERCERO_GENERICO = "999999999"

# Un reply puede traer VARIOS datos, en una o varias líneas. Uso real de
# Andrés (22 y 30-sep-2026) que la primera versión se tragaba entero como
# concepto:
#     abono leidy cuota 1V
#     Tercero : leidy daniela Molina  cc 1007289007
# Marcadores: "Concepto", "Tercero", "Tercero nuevo". Al INICIO de una línea
# los dos puntos son opcionales ("Concepto dulces…"); en medio de la línea
# son obligatorios ("… tercero: Jorge cc 123"). Lo que no lleva marcador ES
# el concepto (literal). Nada de esto pasa por el LLM.
_RE_MARCA_INICIO = re.compile(r"^\s*(tercero\s+nuevo|tercero|concepto)\b\s*:?\s*", re.IGNORECASE)
_RE_MARCA_MEDIO = re.compile(r"\b(tercero\s+nuevo|tercero|concepto)\s*:\s*", re.IGNORECASE)
_RE_MARCA_CORTA = re.compile(r"^\s*([ct])\s*:\s*", re.IGNORECASE)
# Datos del tercero dentro de su línea: documento, celular y correo
_RE_DOC = re.compile(
    r"\b(?P<tipo>nit|c\.?\s?c\.?|c\.?\s?e\.?|c[eé]dula)\s*[:.#]?\s*(?:n[o°º]\.?\s*)?"
    r"(?P<num>\d[\d.\-]{3,19})", re.IGNORECASE)
_RE_NUM_FINAL = re.compile(r"[,;]\s*(?P<num>\d[\d.\-]{3,19})\s*$")
_RE_CEL = re.compile(
    r"\b(?:cel(?:ular)?|tel(?:[eé]fono)?|whatsapp|wpp)\s*[:.]?\s*(?P<cel>\+?\d[\d ]{6,14}\d)",
    re.IGNORECASE)
_RE_EMAIL = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")


def _parse_tercero(valor, nuevo=False):
    """«leidy daniela Molina  cc 1007289007 cel 3001234567» →
    {nombre, tipo (CC|NIT|None), num, phone, email, buscar_num, nuevo}.
    `buscar_num` = el humano dio SOLO un número (documento o celular)."""
    v = " " + (valor or "") + " "
    email = phone = tipo = num = None
    m = _RE_EMAIL.search(v)
    if m:
        email, v = m.group(0), v[:m.start()] + " " + v[m.end():]
    m = _RE_CEL.search(v)
    if m:
        phone, v = re.sub(r"\D", "", m.group("cel")), v[:m.start()] + " " + v[m.end():]
    m = _RE_DOC.search(v)
    if m:
        tipo = "NIT" if m.group("tipo").lower().startswith("n") else "CC"
        num, v = m.group("num").strip(".-"), v[:m.start()] + " " + v[m.end():]
    else:
        m = _RE_NUM_FINAL.search(v.rstrip())
        if m:
            num, v = m.group("num").strip(".-"), v[:m.start()]
    nombre = re.sub(r"\s+", " ", v).strip(" ,;.-:")
    buscar_num = None
    if nombre and re.fullmatch(r"[\d\s.+\-]+", nombre):       # solo un número
        buscar_num, nombre = re.sub(r"\D", "", nombre), None
    if num and tipo != "NIT":
        num = re.sub(r"\D", "", num)                          # cédula: solo dígitos
    return {"nombre": nombre or None, "tipo": tipo, "num": num or None, "phone": phone,
            "email": email, "buscar_num": buscar_num, "nuevo": bool(nuevo)}


def _parse_reply(texto):
    """Reply al resumen de un borrador → {"concepto": str|None, "tercero": dict|None}.
    Lo que no lleva marcador ES el concepto (traducción literal, no adivinanza);
    una línea de tercero jamás se mezcla con el concepto."""
    concepto, tercero = [], None
    for linea in (texto or "").splitlines():
        linea = linea.strip()
        if not linea:
            continue
        m = _RE_MARCA_CORTA.match(linea)                      # "c: …" / "t: …"
        if m:
            linea = ("concepto: " if m.group(1).lower() == "c" else "tercero: ") + linea[m.end():]
        clave, pos = None, 0
        m = _RE_MARCA_INICIO.match(linea)
        if m:
            clave, pos = "_".join(m.group(1).lower().split()), m.end()
        segmentos = []
        for m in _RE_MARCA_MEDIO.finditer(linea, pos):
            segmentos.append((clave, linea[pos:m.start()]))
            clave, pos = "_".join(m.group(1).lower().split()), m.end()
        segmentos.append((clave, linea[pos:]))
        for clave, valor in segmentos:
            valor = valor.strip(" ,;")
            if not valor:
                continue
            if clave in ("tercero", "tercero_nuevo"):
                if tercero is None:
                    tercero = _parse_tercero(valor, nuevo=(clave == "tercero_nuevo"))
            else:
                concepto.append(valor)
    texto_concepto = re.sub(r"\s+", " ", " ".join(concepto)).strip()
    return {"concepto": texto_concepto or None, "tercero": tercero}


def _tercero_dict(row):
    """Fila (id, tipo, número, nombre[, phone]) → dict para el payload."""
    d = {"id": row[0], "identification_type": row[1] or "NIT",
         "identification_number": str(row[2]), "name": str(row[3]).strip()}
    if len(row) > 4 and row[4]:
        d["phone"] = str(row[4]).strip()
    return d


def _sql_nombre_sin_tildes(expr="name"):
    """Expresión SQL que compara nombres como draft_builder.norm (sin tildes
    ni mayúsculas): 'Pérez' = 'perez'."""
    return f"translate(lower({expr}), 'áéíóúüñ', 'aeiouun')"


def _tercero_por_documento(cur, num):
    """Igualdad EXACTA de documento comparando solo dígitos (ignora puntos y
    guiones). Los provisionales SN-… y el genérico no cuentan. → dict | None"""
    digitos = re.sub(r"\D", "", str(num or ""))
    if len(digitos) < 4:
        return None
    cur.execute("""
        SELECT id, identification_type, identification_number, name, phone
          FROM third_parties
         WHERE identification_number NOT LIKE 'SN-%%'
           AND identification_number <> %s
           AND regexp_replace(identification_number, '\\D', '', 'g') = %s
         ORDER BY id LIMIT 1
    """, (_TERCERO_GENERICO, digitos))
    fila = cur.fetchone()
    return _tercero_dict(fila) if fila else None


def _buscar_terceros(cur, q, limite=8):
    """Búsqueda DETERMINISTA en third_parties:
      · solo dígitos → documento exacto, o celular (últimos 10 dígitos)
      · texto → nombres que contienen TODAS las palabras, sin tildes ni
        mayúsculas ("leidy molina" encuentra "Leidy Daniela Molina Martínez")
    → 0, 1 o varios dicts (si son varios, el humano elige)."""
    q = (q or "").strip()
    if not q:
        return []
    digitos = re.sub(r"\D", "", q)
    if len(digitos) >= 5 and len(digitos) >= len(q) - 4:    # "10.203.040", "+57 319…"
        cel = digitos[-10:] if len(digitos) >= 10 else digitos
        cur.execute("""
            SELECT id, identification_type, identification_number, name, phone
              FROM third_parties
             WHERE (identification_number NOT LIKE 'SN-%%'
                    AND regexp_replace(identification_number, '\\D', '', 'g') = %s)
                OR regexp_replace(COALESCE(phone, ''), '\\D', '', 'g') LIKE %s
             ORDER BY id LIMIT %s
        """, (digitos, "%" + cel, int(limite)))
    else:
        palabras = [p for p in _norm(q).split() if len(p) >= 2][:6]
        if not palabras:
            return []
        col = _sql_nombre_sin_tildes()
        condiciones = " AND ".join([f"{col} LIKE %s"] * len(palabras))
        cur.execute(f"""
            SELECT id, identification_type, identification_number, name, phone
              FROM third_parties
             WHERE {condiciones} AND identification_number <> %s
             ORDER BY ({_sql_nombre_sin_tildes('btrim(name)')} = %s) DESC, name LIMIT %s
        """, (*[f"%{p}%" for p in palabras], _TERCERO_GENERICO,
              " ".join(_norm(q).split()), int(limite)))
    return [_tercero_dict(r) for r in cur.fetchall()]


def _terceros_recientes(cur, limite=8):
    """Últimos terceros usados en transacciones (sin el genérico)."""
    cur.execute("""
        SELECT tp.id, tp.identification_type, tp.identification_number, tp.name, tp.phone
          FROM third_parties tp
          JOIN (SELECT third_party_id, MAX(id) AS ultimo FROM transactions
                 GROUP BY third_party_id) u ON u.third_party_id = tp.id
         WHERE tp.identification_number <> %s
         ORDER BY u.ultimo DESC LIMIT %s
    """, (_TERCERO_GENERICO, int(limite)))
    return [_tercero_dict(r) for r in cur.fetchall()]


def _doc_legible(tercero) -> str:
    doc = str(tercero.get("identification_number") or "")
    if doc.startswith("SN-"):
        return "sin documento"
    return f"{tercero.get('identification_type')} {doc}"


def _botones_terceros(draft_id, terceros, crear=None):
    """Una fila por candidato (con su documento, para distinguir homónimos) y,
    si hay datos dictados pendientes, «➕ Crear nuevo: <nombre>»."""
    filas = [[(f"{t['name'][:32]} · {_doc_legible(t)}"[:60], f"tpset:{draft_id}:{t['id']}")]
             for t in terceros]
    if crear:
        filas.append([(f"➕ Crear nuevo: {crear}"[:60], f"tpnew:{draft_id}")])
    filas.append([("« Volver", f"tpback:{draft_id}")])
    return filas


def _medio_pendiente(cur, payload):
    """¿Queda algo por guardar? El borrador viene de un SMS y, si mañana llegara
    OTRO SMS con el mismo medio de pago (cuenta, celular, llave o nombre del
    banco), ¿vendría ya con el tercero que tiene asignado este borrador?
      · sí → None (no se ofrece nada);
      · no → {"tipo", "valor", "tercero_id", "tercero_nombre", "dueno"}, con
        `dueno` = nombre de OTRO tercero que hoy tiene registrado ese medio
        (hay que moverlo) o None (basta guardarlo).
    Usa el MISMO cruce que el SMS entrante (bot_sms.tercero_de_medio).
    A prueba de instalaciones sin migrar: un error no envenena la transacción."""
    from terceros_cuentas import dueno, medio_de_payload
    sms_meta = (payload or {}).get("sms") or {}
    medio = medio_de_payload(sms_meta)       # (tipo, valor) | None
    tp = (payload or {}).get("third_party") or {}
    numero = str(tp.get("identification_number") or "")
    if not medio or not numero or numero == _TERCERO_GENERICO:
        return None
    try:
        cur.execute("SAVEPOINT medio_pendiente")
        from bot_sms import tercero_de_medio
        cur.execute("SELECT id, name FROM third_parties WHERE identification_number = %s", (numero,))
        tercero = cur.fetchone()
        resuelto = actual = None
        if tercero:
            resuelto, _ = tercero_de_medio(cur, medio, sms_meta.get("contraparte"))
            actual = dueno(cur, *medio)
        cur.execute("RELEASE SAVEPOINT medio_pendiente")
    except Exception as e:
        try:
            cur.execute("ROLLBACK TO SAVEPOINT medio_pendiente")
        except Exception:
            pass
        print(f"⚠️ [BOT] medios de pago no disponibles: {e}")
        return None
    if not tercero:
        return None                          # el tercero del borrador aún no tiene ficha
    if resuelto and str(resuelto.get("identification_number")) == numero:
        return None                          # el próximo SMS igual ya llegaría con él
    return {"tipo": medio[0], "valor": medio[1], "tercero_id": tercero[0],
            "tercero_nombre": str(tercero[1]).strip(),
            "dueno": actual["name"] if actual and actual["id"] != tercero[0] else None}


def _boton_medio(draft_id, pendiente):
    """Botón explícito para registrar el medio en la ficha (Regla 6b: nada
    se memoriza solo). Si ya es de otro tercero, el botón es «Mover»."""
    from terceros_cuentas import describir
    desc = describir(pendiente["tipo"], pendiente["valor"])
    if pendiente["dueno"]:
        return (f"🔁 Mover {desc} a {pendiente['tercero_nombre']}"[:60], f"tpmove:{draft_id}")
    return (f"💾 Guardar {desc} en {pendiente['tercero_nombre']}"[:60], f"tpsave:{draft_id}")


def _nota_medio(pendiente) -> str:
    """Línea que explica el botón 💾/🔁 (o "" si no hay nada pendiente)."""
    if not pendiente:
        return ""
    from terceros_cuentas import describir
    desc = describir(pendiente["tipo"], pendiente["valor"])
    if pendiente["dueno"]:
        return (f"🔁 {desc} está registrado hoy en la ficha de {pendiente['dueno']}. Si en "
                f"realidad es de {pendiente['tercero_nombre']}, toca «Mover».")
    return (f"💾 Toca «Guardar» y la próxima vez que llegue un SMS con {desc} el borrador "
            f"vendrá con {pendiente['tercero_nombre']} ya puesto.")


def _botones_con_medio(draft_id, pendiente):
    """Botonera estándar + (arriba) el botón 💾/🔁 cuando hay un medio de pago
    del SMS sin registrar en la ficha del tercero asignado."""
    filas = _botones_borrador(draft_id)
    if pendiente:
        filas.insert(0, [_boton_medio(draft_id, pendiente)])
    return filas


def _confirmacion_con_medio(cur, link, draft_id, resultado):
    """Tras confirmar: última oportunidad de registrar el medio de pago del SMS
    en la ficha del tercero (09.G §10). → (texto, botones | None)
    Es un extra: si algo falla, la confirmación se informa igual (jamás lanza)."""
    if not str(resultado).startswith("✅"):
        return resultado, None
    try:
        cur.execute("SELECT payload FROM transaction_drafts WHERE id = %s AND chat_link_id = %s",
                    (draft_id, link["id"]))
        fila = cur.fetchone()
        payload = (fila[0] if isinstance(fila[0], dict) else json.loads(fila[0])) if fila else {}
        pendiente = _medio_pendiente(cur, payload)
        cur.connection.commit()
    except Exception as e:
        print(f"⚠️ [BOT] botón 💾 tras confirmar #{draft_id}: {e}")
        try:
            cur.connection.rollback()
        except Exception:
            pass
        return resultado, None
    if not pendiente:
        return resultado, None
    return resultado + "\n\n" + _nota_medio(pendiente), [[_boton_medio(draft_id, pendiente)]]


def _asignar_tercero(link, draft_id, tercero, cur=None):
    """Escribe el tercero en el borrador (editar_draft, determinista).
    → dict {text, draft_id, buttons, payload, medio_pendiente}, o str con el error.
    Con `cur`, la botonera incluye 💾 si el SMS trae un medio sin registrar."""
    editado = editar_draft(draft_id, {"third_party": {
        "identification_type": tercero["identification_type"],
        "identification_number": tercero["identification_number"],
        "name": tercero["name"]}}, hub_user_id=link["hub_user_id"])
    if editado.get("error"):
        return editado["error"]
    payload = editado["payload"]
    pendiente = _medio_pendiente(cur, payload) if cur is not None else None
    nota = _nota_medio(pendiente)
    return {"text": f"👤 Tercero → {tercero['name']} ({_doc_legible(tercero)})\n"
                    + (nota + "\n" if nota else "") + "\n"
                    + render_summary(draft_id, payload),
            "draft_id": draft_id, "buttons": _botones_con_medio(draft_id, pendiente),
            "payload": payload, "medio_pendiente": pendiente}


def _crear_tercero(cur, datos):
    """Alta desde el chat con lo que el humano dictó: con documento queda
    completo; sin documento nace provisional SN-… — el MISMO camino que la
    web (database_driver._asegurar_tercero). → dict del tercero."""
    from database_driver import _asegurar_tercero
    tp_id = _asegurar_tercero(cur, {
        "identification_type": datos.get("tipo") or "CC",
        "identification_number": datos.get("num") or "",
        "name": datos["nombre"],
        "phone": datos.get("phone"),
        "email": datos.get("email"),
    })
    cur.execute("SELECT id, identification_type, identification_number, name, phone "
                "FROM third_parties WHERE id = %s", (tp_id,))
    return _tercero_dict(cur.fetchone())


def _rellenar_contacto(cur, tp_id, datos):
    """Celular / correo dictados junto al tercero: RELLENAN lo vacío, jamás
    pisan lo que ya está en la ficha (misma regla que _asegurar_tercero)."""
    if not (datos.get("phone") or datos.get("email")):
        return
    cur.execute("""
        UPDATE third_parties
           SET phone = COALESCE(NULLIF(btrim(phone), ''), %s),
               email = COALESCE(NULLIF(btrim(email), ''), %s)
         WHERE id = %s AND identification_number <> %s
    """, (datos.get("phone"), datos.get("email"), tp_id, _TERCERO_GENERICO))


def _guardar_pendiente(cur, link, draft_id, datos):
    """Deja en el borrador los datos dictados de un tercero que aún no se
    crea: hay parecidos y el humano debe elegir uno o «➕ Crear nuevo»."""
    pendiente = {k: datos.get(k) for k in ("nombre", "tipo", "num", "phone", "email")}
    cur.execute("""
        UPDATE transaction_drafts
           SET payload = jsonb_set(payload, '{tercero_pendiente}', %s::jsonb, true)
         WHERE id = %s AND chat_link_id = %s
    """, (json.dumps(pendiente), draft_id, link["id"]))


def _tomar_pendiente(cur, link, draft_id):
    """Lee y BORRA los datos pendientes del borrador. → dict | None.
    OJO: deja un UPDATE sin confirmar sobre el borrador — el llamador debe
    hacer commit ANTES de llamar a editar_draft (otra conexión, FOR UPDATE)."""
    cur.execute("""
        SELECT payload->'tercero_pendiente' FROM transaction_drafts
         WHERE id = %s AND chat_link_id = %s
    """, (draft_id, link["id"]))
    row = cur.fetchone()
    pendiente = row[0] if row else None
    if isinstance(pendiente, str):
        pendiente = json.loads(pendiente)
    if pendiente:
        cur.execute("""
            UPDATE transaction_drafts SET payload = payload - 'tercero_pendiente'
             WHERE id = %s AND chat_link_id = %s
        """, (draft_id, link["id"]))
    return pendiente or None


def _completar_provisional(cur, tp_id, pendiente):
    """El humano eligió un tercero SIN documento (SN-…) y había dictado uno:
    se le completa la ficha en vez de crear un duplicado. → fila nueva | None"""
    if not pendiente.get("num") or _tercero_por_documento(cur, pendiente["num"]):
        return None
    cur.execute("""
        UPDATE third_parties
           SET identification_type = %s, identification_number = %s,
               phone = COALESCE(NULLIF(btrim(phone), ''), %s),
               email = COALESCE(NULLIF(btrim(email), ''), %s)
         WHERE id = %s AND identification_number LIKE 'SN-%%'
        RETURNING id, identification_type, identification_number, name, phone
    """, (pendiente.get("tipo") or "CC", pendiente["num"], pendiente.get("phone"),
          pendiente.get("email"), tp_id))
    return cur.fetchone()


def _resolver_tercero_dictado(cur, t):
    """Qué hacer con el tercero que el humano dictó (Regla 6b: igualdad o
    decide el humano; escribirlo distinto jamás crea un duplicado).
      → ("asignar", tercero, False)   un único candidato seguro
      → ("crear", None, False)        no existe y hay datos para crearlo
      → ("elegir", candidatos, crear) hay parecidos: decide el humano
      → ("nada", mensaje, False)      no existe y faltan datos"""
    nombre, num = t.get("nombre"), t.get("num")
    if t.get("buscar_num") and not nombre:                 # "Tercero: 3193301184"
        encontrados = _buscar_terceros(cur, t["buscar_num"])
        if len(encontrados) == 1:
            return "asignar", encontrados[0], False
        if encontrados:
            return "elegir", encontrados, False
        return "nada", (f"No encontré ningún tercero con el número {t['buscar_num']}. "
                        f"Para crearlo responde: Tercero: Nombre cc {t['buscar_num']}"), False
    if num:
        por_documento = _tercero_por_documento(cur, num)
        if por_documento:                                  # el documento manda
            return "asignar", por_documento, False
        if not nombre:
            return "nada", (f"No existe un tercero con el documento {num}. Dime también "
                            f"el nombre: Tercero: Nombre cc {num}"), False
    parecidos = _buscar_terceros(cur, nombre) if nombre else []
    if num:
        # Documento nuevo para el sistema. Si hay nombres parecidos, el humano
        # dice si es uno de ellos (y se le completa el documento) o es otro.
        return ("elegir", parecidos, True) if parecidos else ("crear", None, False)
    if t.get("nuevo"):
        exactos = [p for p in parecidos if _norm(p["name"]) == _norm(nombre)]
        if len(exactos) == 1:
            return "asignar", exactos[0], False            # ya existía: no se duplica
        return ("elegir", parecidos, True) if parecidos else ("crear", None, False)
    if len(parecidos) == 1:
        return "asignar", parecidos[0], False
    if parecidos:
        return "elegir", parecidos, False
    return "nada", (f"No encontré ningún tercero que coincida con «{nombre}». Para crearlo "
                    f"dime su documento:\n  Tercero: {nombre} cc 123456\n"
                    f"(o \"Tercero nuevo: {nombre}\" para crearlo sin documento)"), False


def _draft_por_reply(cur, link, msg):
    """reply_to_message_id → id de un borrador editable de este chat, o None."""
    if not msg.get("reply_to_message_id"):
        return None
    cur.execute("""
        SELECT id FROM transaction_drafts
         WHERE chat_link_id = %s AND bot_summary_message_id = %s
           AND status IN ('BORRADOR', 'ERROR')
    """, (link["id"], str(msg["reply_to_message_id"])))
    row = cur.fetchone()
    return row[0] if row else None


def _flujo_reply(cur, link, draft_id, texto):
    """Texto respondiendo al resumen de un borrador (Etapa 09.G). Puede traer
    concepto y tercero a la vez, en una o varias líneas."""
    datos = _parse_reply(texto)
    concepto, t = datos["concepto"], datos["tercero"]
    if not concepto and not t:
        return None
    notas, payload, botones = [], None, None

    if concepto:
        editado = editar_draft(draft_id, {"concept": concepto[:255]},
                               hub_user_id=link["hub_user_id"])
        if editado.get("error"):
            return editado["error"]
        payload = editado["payload"]
        notas.append(f"📝 Concepto → «{concepto[:255]}»")

    if t:
        accion, dato, puede_crear = _resolver_tercero_dictado(cur, t)
        creado = False
        if accion == "crear":
            dato, accion, creado = _crear_tercero(cur, t), "asignar", True
        if accion == "asignar":
            _rellenar_contacto(cur, dato["id"], t)
            res = _asignar_tercero(link, draft_id, dato, cur=cur)
            if isinstance(res, str):
                return res
            payload = res["payload"]
            notas.append(("👤 Tercero CREADO → " if creado else "👤 Tercero → ")
                         + f"{dato['name']} ({_doc_legible(dato)})")
        elif accion == "elegir":
            if puede_crear:
                _guardar_pendiente(cur, link, draft_id, t)
            notas.append(f"👤 «{t.get('nombre') or t.get('buscar_num')}»: hay terceros parecidos. "
                         + ("Toca el que es, o crea uno nuevo (así no quedan duplicados)."
                            if puede_crear else "Toca el que es."))
            botones = _botones_terceros(draft_id, dato,
                                        crear=(t.get("nombre") if puede_crear else None))
        else:
            notas.append("👤 " + dato)

    if payload is None:
        cur.execute("SELECT payload FROM transaction_drafts WHERE id = %s AND chat_link_id = %s",
                    (draft_id, link["id"]))
        row = cur.fetchone()
        payload = (row[0] if isinstance(row[0], dict) else json.loads(row[0])) if row else {}
    if botones is None:
        # Medio de pago del SMS aún sin registrar en la ficha del tercero → botón 💾
        pendiente = _medio_pendiente(cur, payload)
        if pendiente:
            notas.append(_nota_medio(pendiente))
        botones = _botones_con_medio(draft_id, pendiente)
    return {"text": "\n".join(notas) + "\n\n" + render_summary(draft_id, payload),
            "draft_id": draft_id, "buttons": botones}


def _tags_reales(cur):
    """Etiquetas del módulo de Etiquetas (tag_definitions = fuente de la
    verdad). → [(id, name)]."""
    cur.execute("SELECT id, name FROM tag_definitions ORDER BY id LIMIT 12")
    return [(r[0], str(r[1]).strip()) for r in cur.fetchall()]


def _botones_tags(cur, draft_id, payload):
    """Toggle de etiquetas: ✓ en las puestas; tocar añade/quita."""
    puestas = set(payload.get("tags") or [])
    filas = []
    for tid, nombre in _tags_reales(cur):
        marca = "✓ " if nombre in puestas else ""
        filas.append([(f"{marca}{nombre}", f"tagset:{draft_id}:{tid}")])
    filas.append([("✔ Listo", f"tagdone:{draft_id}")])
    return filas


def _empresas_reales(cur):
    """Empresas del árbol para los botones de destino. → [(entity_id, label)].
    Se listan ENTIDADES (no portafolios): es el lenguaje de Andrés; el
    portafolio se garantiza al elegir (ensure_portfolio_for_entity)."""
    cur.execute("""
        SELECT id, name, type FROM entities
        WHERE COALESCE(status, '') <> 'ARCHIVADA'
        ORDER BY id
        LIMIT 12
    """)
    iconos = {"HOLDING": "🏛️", "EMPRESA": "🏢", "SUB_EMPRESA": "📍", "PROYECTO": "📐"}
    return [(r[0], f"{iconos.get(r[2], '🏢')} {r[1].strip()}") for r in cur.fetchall()]


def _cmd_empresa(cur, link, arg):
    """/empresa — muestra o cambia la empresa/portafolio default del chat.
    DETERMINISTA: match difuso contra nombres reales, jamás el LLM."""
    if not arg:
        cur.execute("SELECT name FROM entities ORDER BY id LIMIT 12")
        nombres = [r[0].strip() for r in cur.fetchall()]
        lista = "\n".join(f"  · {n}" for n in nombres) or "  (sin empresas)"
        return (f"🏢 Empresa/portafolio actual del chat: {link['default_portfolio']}\n\n"
                f"Tus empresas:\n{lista}\n\n"
                "Para cambiar: /empresa <nombre> (vale un pedazo del nombre)")

    from draft_builder import norm
    objetivo = norm(arg)
    cur.execute("SELECT id, name, portfolio_id FROM entities ORDER BY id")
    candidatos = [(r[0], r[1].strip(), r[2]) for r in cur.fetchall()]
    elegido = next((c for c in candidatos if norm(c[1]) == objetivo), None) \
        or next((c for c in candidatos if objetivo in norm(c[1])), None)
    if not elegido:
        return (f"No encontré ninguna empresa que se parezca a \"{arg}\".\n"
                "Usa /empresa (sin nombre) para ver la lista.")

    portfolio_name = _portafolio_de_entidad(cur, elegido[0])
    if not portfolio_name:
        return (f"No pude preparar la contabilidad de {elegido[1]}. "
                "Ábrela una vez en la web e intenta de nuevo.")
    cur.execute("UPDATE bot_chat_links SET default_portfolio = %s WHERE id = %s",
                (portfolio_name, link["id"]))
    return (f"✅ Listo: los próximos registros de este chat van a "
            f"{elegido[1]} (portafolio \"{portfolio_name}\").")


def _portafolio_de_entidad(cur, entity_id):
    """Nombre del portafolio de la entidad, creándolo si no tiene (misma
    garantía que la web al seleccionar empresa). → nombre o None."""
    try:
        from org_driver import ensure_portfolio_for_entity
        out = ensure_portfolio_for_entity(int(entity_id))
        return out.get("portfolio_name")
    except Exception as e:
        print(f"⚠️ [BOT] ensure_portfolio({entity_id}) falló: {e}")
        return None


def guardar_summary_message_id(draft_id: int, message_id) -> None:
    """El adaptador registra el message_id del resumen enviado — habilita el
    reply-con-foto y la edición del mensaje al confirmar por botón."""
    from db_pool import get_conn, put_conn
    try:
        conn = get_conn()
        try:
            cur = conn.cursor()
            cur.execute("""
                UPDATE transaction_drafts SET bot_summary_message_id = %s
                WHERE id = %s
            """, (str(message_id), draft_id))
            conn.commit()
        finally:
            put_conn(conn)
    except Exception:
        pass   # best-effort: sin esto solo se pierde el reply-con-foto


# ══════════════════════════════════════════════════════════════════════════════
# Callbacks de botones (Etapa E) — deterministas, el LLM no participa
# ══════════════════════════════════════════════════════════════════════════════

def handle_callback(channel: str, chat_id: str, data: str):
    """Procesa el toque de un botón inline. → dict de instrucciones:
      {"alert": toast corto,
       "edit_text": nuevo texto del mensaje original (None = no tocar),
       "edit_buttons": nueva botonera ([] = quitar, None = no tocar),
       "text": mensaje NUEVO a enviar (None = ninguno)}
    Idempotente: el estado del borrador en BD manda — un botón viejo en el
    historial no puede confirmar dos veces."""
    out = {"alert": None, "edit_text": None, "edit_buttons": None, "text": None}
    partes = (data or "").split(":")
    accion = partes[0] if partes else ""

    from db_pool import get_conn, put_conn
    conn = get_conn()
    try:
        cur = conn.cursor()
        link = _get_link(cur, channel, chat_id)
        if link is None or link["status"] != "ACTIVO":
            out["alert"] = "Chat no vinculado."
            return out

        try:
            draft_id = int(partes[1])
        except (IndexError, ValueError):
            out["alert"] = "Botón inválido."
            return out

        if accion == "ok":
            conn.commit()
            resultado = confirmar_draft(draft_id, chat_link_id=link["id"])
            out["alert"] = "Confirmando…"
            out["edit_buttons"] = []          # el botón no puede volver a usarse
            # Con la confirmación va el botón 💾 si el medio de pago del SMS
            # aún no está en la ficha del tercero (09.G §10).
            out["text"], botones_medio = _confirmacion_con_medio(cur, link, draft_id, resultado)
            if botones_medio:
                out["text_buttons"] = botones_medio
            log_outbound(channel, chat_id, out["text"], link["id"], draft_id)
            return out

        if accion == "no":
            conn.commit()
            resultado = descartar_draft(draft_id, chat_link_id=link["id"])
            out["alert"] = "Descartado" if "descartado" in resultado.lower() else None
            out["edit_buttons"] = []
            out["text"] = resultado
            log_outbound(channel, chat_id, resultado, link["id"], draft_id)
            return out

        if accion == "hold":
            # 💤 Dejar en borrador: no toca el estado (YA es BORRADOR) — solo
            # retira la botonera para que quede "guardado para después".
            conn.commit()
            out["alert"] = "Guardado como borrador."
            out["edit_buttons"] = []
            out["text"] = (f"💤 El borrador #{draft_id} queda pendiente en la bandeja.\n"
                           f"Lo retomas con \"Confirmar #{draft_id}\", /borradores "
                           "o desde la web.")
            log_outbound(channel, chat_id, out["text"], link["id"], draft_id)
            return out

        if accion == "tags":
            cur.execute("""
                SELECT payload FROM transaction_drafts
                WHERE id = %s AND chat_link_id = %s
            """, (draft_id, link["id"]))
            row = cur.fetchone()
            if not row:
                conn.commit()
                out["alert"] = "Borrador no encontrado."
                return out
            payload = row[0] if isinstance(row[0], dict) else json.loads(row[0])
            filas = _botones_tags(cur, draft_id, payload)
            conn.commit()
            if len(filas) == 1:      # solo el botón Listo: no hay etiquetas creadas
                out["alert"] = "No tienes etiquetas. Créalas en el módulo 🏷️ de la web."
                return out
            out["alert"] = "Toca para poner/quitar etiquetas"
            out["edit_buttons"] = filas
            return out

        if accion == "tagset":
            try:
                tag_id = int(partes[2])
            except (IndexError, ValueError):
                out["alert"] = "Botón inválido."
                return out
            cur.execute("SELECT name FROM tag_definitions WHERE id = %s", (tag_id,))
            row = cur.fetchone()
            if not row:
                conn.commit()
                out["alert"] = "Esa etiqueta ya no existe."
                return out
            nombre = str(row[0]).strip()
            cur.execute("""
                SELECT payload FROM transaction_drafts
                WHERE id = %s AND chat_link_id = %s
            """, (draft_id, link["id"]))
            fila_d = cur.fetchone()
            conn.commit()
            if not fila_d:
                out["alert"] = "Borrador no encontrado."
                return out
            payload = fila_d[0] if isinstance(fila_d[0], dict) else json.loads(fila_d[0])
            puestas = list(payload.get("tags") or [])
            if nombre in puestas:
                puestas.remove(nombre)
                out["alert"] = f"− {nombre}"
            else:
                puestas.append(nombre)
                out["alert"] = f"+ {nombre}"
            editado = editar_draft(draft_id, {"tags": puestas},
                                   hub_user_id=link["hub_user_id"])
            if editado.get("error"):
                out["alert"] = editado["error"][:190]
                return out
            out["edit_buttons"] = _botones_tags(cur, draft_id, editado["payload"])
            return out

        if accion == "tagdone":
            cur.execute("""
                SELECT payload FROM transaction_drafts
                WHERE id = %s AND chat_link_id = %s
            """, (draft_id, link["id"]))
            row = cur.fetchone()
            conn.commit()
            if row:
                payload = row[0] if isinstance(row[0], dict) else json.loads(row[0])
                out["edit_text"] = render_summary(draft_id, payload)
            out["edit_buttons"] = _botones_borrador(draft_id)
            return out

        # ── Etapa 09.G: 👤 Tercero / 📝 Concepto ──
        if accion == "tp":
            terceros = _terceros_recientes(cur)
            conn.commit()
            if not terceros:
                out["alert"] = "Sin terceros recientes. Responde al borrador: Tercero: nombre, NIT o celular"
                return out
            out["alert"] = "Elige el tercero (o responde al borrador con Tercero: …)"
            out["edit_buttons"] = _botones_terceros(draft_id, terceros)
            return out

        if accion == "tpback":
            conn.commit()
            out["edit_buttons"] = _botones_borrador(draft_id)
            return out

        if accion == "tpset":
            try:
                tp_id = int(partes[2])
            except (IndexError, ValueError):
                out["alert"] = "Botón inválido."
                return out
            cur.execute("SELECT id, identification_type, identification_number, name, phone "
                        "FROM third_parties WHERE id = %s", (tp_id,))
            row = cur.fetchone()
            if not row:
                conn.commit()
                out["alert"] = "Ese tercero ya no existe."
                out["edit_buttons"] = _botones_borrador(draft_id)
                return out
            # Si el humano había dictado un documento y eligió un tercero SIN
            # documento, se le completa la ficha (no se crea un duplicado).
            pendiente = _tomar_pendiente(cur, link, draft_id)
            completado = None
            if pendiente and str(row[2]).startswith("SN-"):
                completado = _completar_provisional(cur, tp_id, pendiente)
            conn.commit()                 # antes de editar_draft (otra conexión)
            tercero = _tercero_dict(completado or row)
            res = _asignar_tercero(link, draft_id, tercero, cur=cur)
            conn.commit()
            if isinstance(res, str):
                out["alert"] = res[:190]
                return out
            out["alert"] = f"👤 {tercero['name']}"[:190]
            out["edit_text"] = (("📇 Documento completado en la ficha.\n" if completado else "")
                                + res["text"])
            out["edit_buttons"] = res["buttons"]      # incluye 💾 si el SMS trae un medio sin registrar
            return out

        if accion == "tpnew":
            pendiente = _tomar_pendiente(cur, link, draft_id)
            if not pendiente or not pendiente.get("nombre"):
                conn.commit()
                out["alert"] = "Ya no tengo esos datos. Responde de nuevo: Tercero: Nombre cc 123"
                out["edit_buttons"] = _botones_borrador(draft_id)
                return out
            tercero = (_tercero_por_documento(cur, pendiente["num"]) if pendiente.get("num") else None) \
                or _crear_tercero(cur, pendiente)
            conn.commit()                 # antes de editar_draft (otra conexión)
            res = _asignar_tercero(link, draft_id, tercero, cur=cur)
            conn.commit()
            if isinstance(res, str):
                out["alert"] = res[:190]
                return out
            out["alert"] = f"👤 Creado: {tercero['name']}"[:190]
            out["edit_text"] = "👤 Tercero CREADO.\n" + res["text"]
            out["edit_buttons"] = res["buttons"]
            return out

        # ── 09.G §10: registrar (💾) o mover (🔁) el medio de pago del SMS en la
        #    ficha del tercero. SIEMPRE explícito: nada se memoriza solo. ──
        if accion in ("tpsave", "tpmove"):
            cur.execute("SELECT payload, status FROM transaction_drafts WHERE id = %s AND chat_link_id = %s",
                        (draft_id, link["id"]))
            fila = cur.fetchone()
            if not fila:
                conn.commit()
                out["alert"] = "Borrador no encontrado."
                return out
            payload = fila[0] if isinstance(fila[0], dict) else json.loads(fila[0])
            editable = fila[1] in ("BORRADOR", "ERROR")
            botones_despues = _botones_borrador(draft_id) if editable else []
            pendiente = _medio_pendiente(cur, payload)
            if not pendiente:
                conn.commit()
                out["alert"] = "Nada que guardar: ese dato ya está asociado a este tercero."
                out["edit_buttons"] = botones_despues
                return out
            from terceros_cuentas import agregar, describir, mover
            desc = describir(pendiente["tipo"], pendiente["valor"])
            nombre = pendiente["tercero_nombre"]
            if pendiente["dueno"] and accion != "tpmove":
                # Alguien lo registró a nombre de otro entre tanto: no se pisa solo
                conn.commit()
                out["alert"] = f"{desc} ya está en la ficha de {pendiente['dueno']}."[:190]
                out["edit_buttons"] = ([[_boton_medio(draft_id, pendiente)]] + botones_despues
                                       if editable else [[_boton_medio(draft_id, pendiente)]])
                return out
            if pendiente["dueno"] and mover(cur, pendiente["tipo"], pendiente["valor"],
                                            pendiente["tercero_id"], origen="bot"):
                out["alert"] = "🔁 Movido"
                mensaje = (f"🔁 Listo: {desc} pasó de la ficha de {pendiente['dueno']} a la de "
                           f"{nombre}. Desde ahora los SMS con ese dato llegan con {nombre}.")
            else:
                r = agregar(cur, pendiente["tercero_id"], pendiente["tipo"], pendiente["valor"],
                            origen="bot")
                if not r["ok"]:
                    conn.rollback()
                    out["alert"] = r["error"][:190]
                    return out
                out["alert"] = "💾 Guardado"
                mensaje = (f"💾 Listo: {desc} quedó en la ficha de {nombre}. La próxima vez que "
                           f"llegue un SMS con ese dato, el borrador vendrá con {nombre} ya puesto. "
                           "(Se ve y se edita en el módulo Terceros de la web.)")
            conn.commit()
            out["edit_buttons"] = botones_despues
            out["text"] = mensaje
            log_outbound(channel, chat_id, mensaje, link["id"], draft_id)
            return out

        if accion == "cpt":
            conn.commit()
            out["alert"] = "Responde al mensaje del borrador con el concepto"
            out["text"] = (f"📝 Para completar el borrador #{draft_id}: RESPONDE (reply) al "
                           "mensaje del borrador. Puedes mandar todo junto:\n\n"
                           "  abono cuota 1\n"
                           "  Tercero: Leidy Molina cc 1007289007\n\n"
                           "· Lo que escribas sin marca es el concepto.\n"
                           "· \"Tercero: nombre\" busca uno existente; con \"cc\" o \"nit\" y el "
                           "número lo crea si no existe (nunca duplica: el documento manda).")
            return out

        if accion == "emp":
            filas = [[(label, f"empset:{draft_id}:{eid}")]
                     for eid, label in _empresas_reales(cur)]
            filas.append([("« Volver", f"empback:{draft_id}")])
            conn.commit()
            out["alert"] = "¿A qué empresa va este registro?"
            out["edit_buttons"] = filas
            return out

        if accion == "empback":
            conn.commit()
            out["edit_buttons"] = _botones_borrador(draft_id)
            return out

        if accion == "empset":
            try:
                entity_id = int(partes[2])
            except (IndexError, ValueError):
                out["alert"] = "Botón inválido."
                return out
            cur.execute("SELECT name FROM entities WHERE id = %s", (entity_id,))
            row = cur.fetchone()
            conn.commit()
            if not row:
                out["alert"] = "Esa empresa ya no existe."
                out["edit_buttons"] = _botones_borrador(draft_id)
                return out
            portfolio_name = _portafolio_de_entidad(cur, entity_id)
            if not portfolio_name:
                out["alert"] = "No pude preparar esa empresa. Intenta desde la web."
                out["edit_buttons"] = _botones_borrador(draft_id)
                return out
            editado = editar_draft(draft_id, {"portfolio_name": portfolio_name},
                                   hub_user_id=link["hub_user_id"])
            if editado.get("error"):
                out["alert"] = editado["error"][:190]
                out["edit_buttons"] = []
                return out
            out["alert"] = f"→ {row[0].strip()}"
            out["edit_text"] = render_summary(draft_id, editado["payload"])
            out["edit_buttons"] = _botones_borrador(draft_id)
            return out

        out["alert"] = "Botón desconocido."
        return out
    except Exception as e:
        try:
            conn.rollback()
        except Exception:
            pass
        out["alert"] = f"Error: {e}"[:190]
        return out
    finally:
        put_conn(conn)


def _listar_borradores(cur, link):
    cur.execute("""
        SELECT id, payload FROM transaction_drafts
        WHERE chat_link_id = %s AND status = 'BORRADOR'
        ORDER BY id DESC LIMIT 10
    """, (link["id"],))
    rows = cur.fetchall()
    if not rows:
        return "No tienes borradores pendientes. Envíame un gasto o ingreso 🙂"
    lineas = ["📋 Borradores pendientes:"]
    for did, payload in rows:
        p = payload if isinstance(payload, dict) else json.loads(payload)
        lineas.append(f"  #{did} · {p.get('type')} · {_fmt_money(p.get('amount'))} · {p.get('concept') or '—'}")
    lineas.append("\nConfirmar #N / Descartar #N")
    return "\n".join(lineas)


def _unico_borrador(cur, link):
    """Si el usuario tiene EXACTAMENTE un borrador activo, 'confirmar' sin número lo referencia."""
    cur.execute("""
        SELECT id FROM transaction_drafts
        WHERE chat_link_id = %s AND status = 'BORRADOR'
        ORDER BY id DESC LIMIT 2
    """, (link["id"],))
    rows = cur.fetchall()
    return rows[0][0] if len(rows) == 1 else None


# ══════════════════════════════════════════════════════════════════════════════
# Confirmación / descarte (deterministas — el LLM no participa)
# ══════════════════════════════════════════════════════════════════════════════

def confirmar_draft(draft_id: int, chat_link_id=None, hub_user_id=None) -> str:
    """Confirma un borrador por el pipeline oficial. Solo una petición gana.

    Propiedad: desde el chat se pasa chat_link_id; desde la web, hub_user_id.
    """
    from db_pool import get_conn, put_conn
    conn = get_conn()
    try:
        cur = conn.cursor()
        # Pre-check: BD real viva. El fallback silencioso a mock_db de
        # database_driver JAMÁS debe recibir una confirmación.
        cur.execute("SELECT 1")

        # hub_users.id es UUID → el cast del filtro de propiedad debe serlo también
        cur.execute("""
            UPDATE transaction_drafts
               SET status = 'PROCESANDO', updated_at = NOW()
             WHERE id = %s
               AND (status = 'BORRADOR'
                    OR (status = 'PROCESANDO' AND updated_at < NOW() - INTERVAL '5 minutes'))
               AND (%s::int IS NULL OR chat_link_id = %s)
               AND (%s::uuid IS NULL OR user_id = %s)
            RETURNING payload, media_path, media_paths
        """, (draft_id, chat_link_id, chat_link_id,
              str(hub_user_id) if hub_user_id else None,
              str(hub_user_id) if hub_user_id else None))
        row = cur.fetchone()
        conn.commit()                    # la toma del borrador queda firme YA
        if not row:
            return _explicar_no_tomable(cur, draft_id, chat_link_id, hub_user_id, accion="confirmar")

        payload = row[0] if isinstance(row[0], dict) else json.loads(row[0])
        media_path = row[1]
        media_paths = row[2] if isinstance(row[2], list) else json.loads(row[2] or "[]")
        if not media_paths and media_path:
            media_paths = [media_path]

        try:
            return _ejecutar_confirmacion(conn, cur, draft_id, payload, media_path,
                                          media_paths)
        except Exception as e:
            cur.execute("""
                UPDATE transaction_drafts SET status = 'ERROR', error = %s, updated_at = NOW()
                WHERE id = %s
            """, (str(e)[:500], draft_id))
            conn.commit()
            return (f"⚠ El borrador #{draft_id} quedó en estado ERROR: {e}\n"
                    "Revísalo en la Bandeja de la web.")
    finally:
        put_conn(conn)


def _ejecutar_confirmacion(conn, cur, draft_id, payload, media_path,
                           media_paths=None):
    # 1. Campos mínimos
    missing = compute_missing(payload)
    if missing:
        return _revertir(conn, cur, draft_id,
                         f"Faltan campos: {', '.join(missing)}. Descarta el borrador y "
                         "reenvía la operación completa (o edítalo en la Bandeja web).")

    # 2. Portafolio REAL (mata el portafolio-fantasma: registrar_transaccion
    #    crea silenciosamente cualquier nombre que no exista)
    cur.execute("SELECT name FROM portfolios ORDER BY name")
    portafolios = [r[0] for r in cur.fetchall()]
    if payload.get("portfolio_name") not in portafolios:
        return _revertir(conn, cur, draft_id,
                         f"El portafolio '{payload.get('portfolio_name')}' no existe. "
                         f"Disponibles: {', '.join(portafolios) or '(ninguno)'}")

    # 3. Fecha válida
    if not re.match(r"^\d{4}-\d{2}-\d{2}$", str(payload.get("transaction_date") or "")):
        return _revertir(conn, cur, draft_id, "Fecha inválida en el borrador (se espera YYYY-MM-DD).")

    # 4. Cuenta (nunca confirmar sin cuenta → deuda DT-01).
    #    Primero POR ID si el borrador la trae resuelta (etapa 09.F, D-09-03:
    #    la cuenta se identifica por id y su nombre puede cambiar libremente;
    #    editar_draft borra account_id cuando el humano cambia payment_method).
    #    Si no, por payment_method como siempre — re-resuelto al confirmar
    #    porque las cuentas pueden haber cambiado desde que nació el borrador.
    account_id = _cuenta_existente(cur, payload.get("account_id"))
    if account_id is None:
        account_id, err = _resolver_cuenta(cur, payload.get("payment_method"))
        if err:
            return _revertir(conn, cur, draft_id,
                             err + " Descarta el borrador y reenvía la operación "
                                   "nombrando una de tus cuentas.")

    # 5. Contrato oficial + pipeline oficial (el mismo de la web)
    from routers.schemas import TransactionInput
    from transaction_service import create_transaction
    tx_input = TransactionInput(
        portfolio_name=payload["portfolio_name"],
        type=payload["type"],
        amount=float(payload["amount"]),
        concept=payload["concept"],
        payment_method=payload["payment_method"],
        category=payload["category"],
        third_party=payload["third_party"],
        transaction_date=payload["transaction_date"],
        apply_iva=bool(payload.get("apply_iva")),
        apply_gmf=bool(payload.get("apply_gmf")),
        account_id=account_id,
        # Transferencia entre cuentas propias detectada por SMS (etapa 09.F)
        dest_account_id=_cuenta_existente(cur, payload.get("dest_account_id")),
        transaction_currency=payload.get("transaction_currency") or "COP",
        evidence_file_path=media_path,
        evidence_files=media_paths or None,   # Etapa E.3: TODAS las evidencias
        # Etapa E.2 (2026-09-08): sin esto, las etiquetas puestas por botón o
        # en la bandeja y la ubicación adjunta SE PERDÍAN al confirmar.
        tags=payload.get("tags") or None,
        geo_maps_link=payload.get("geo_maps_link"),
        geo_latitude=payload.get("geo_latitude"),
        geo_longitude=payload.get("geo_longitude"),
    )
    resp = create_transaction(tx_input)

    tx_id = resp.get("transaction_id")
    journal = resp.get("journal")
    if journal in ("ok", "skipped_duplicate"):
        cur.execute("""
            UPDATE transaction_drafts
               SET status = 'CONFIRMADO', confirmed_transaction_id = %s,
                   confirmed_at = NOW(), updated_at = NOW(), error = NULL
             WHERE id = %s
        """, (tx_id, draft_id))
        conn.commit()
        return (f"✅ Transacción #{tx_id} registrada\n"
                f"Borrador: #{draft_id}\n"
                f"Neto: {_fmt_money(resp.get('net_value'))} COP\n"
                f"Asiento contable: OK")
    # Transacción creada pero SIN asiento válido → estado ERROR, nunca éxito silencioso
    cur.execute("""
        UPDATE transaction_drafts
           SET status = 'ERROR', confirmed_transaction_id = %s,
               error = %s, updated_at = NOW()
         WHERE id = %s
    """, (tx_id, f"Asiento contable: {journal}", draft_id))
    conn.commit()
    return (f"⚠ La transacción #{tx_id} se creó pero el asiento contable falló "
            f"({journal}). El borrador #{draft_id} quedó en estado ERROR — "
            "revisa el Libro Diario en la web.")


def descartar_draft(draft_id: int, chat_link_id=None, hub_user_id=None) -> str:
    from db_pool import get_conn, put_conn
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute("""
            UPDATE transaction_drafts
               SET status = 'DESCARTADO', updated_at = NOW()
             WHERE id = %s AND status IN ('BORRADOR', 'ERROR')
               AND (%s::int IS NULL OR chat_link_id = %s)
               AND (%s::uuid IS NULL OR user_id = %s)
            RETURNING id
        """, (draft_id, chat_link_id, chat_link_id,
              str(hub_user_id) if hub_user_id else None,
              str(hub_user_id) if hub_user_id else None))
        row = cur.fetchone()
        conn.commit()
        if row:
            return f"🗑 Borrador #{draft_id} descartado. Puedes enviarme la operación de nuevo."
        return _explicar_no_tomable(cur, draft_id, chat_link_id, hub_user_id, accion="descartar")
    finally:
        put_conn(conn)


# Campos del payload que la bandeja web puede editar (Etapa C). account_id NO:
# se re-resuelve desde payment_method al confirmar. inferred/missing se recalculan.
_CAMPOS_EDITABLES = {"type", "amount", "concept", "category", "payment_method",
                     "transaction_date", "portfolio_name", "apply_iva", "apply_gmf",
                     "tags"}


def editar_draft(draft_id: int, cambios: dict, hub_user_id=None) -> dict:
    """Edición determinista desde la bandeja web (Etapa C). Sin LLM.

    Solo BORRADOR o ERROR son editables; un campo editado por el humano deja
    de estar 'inferido'. ERROR vuelve a BORRADOR (la corrección invalida el
    error previo). → dict del borrador actualizado, o {'error': ...}.
    """
    campos = {k: v for k, v in (cambios or {}).items() if k in _CAMPOS_EDITABLES}
    tercero = cambios.get("third_party") if isinstance((cambios or {}).get("third_party"), dict) else None
    if not campos and not tercero:
        return {"error": "Nada que editar: ningún campo editable en la petición."}

    if "type" in campos and campos["type"] not in TIPOS_VALIDOS:
        return {"error": f"Tipo inválido. Válidos: {', '.join(sorted(TIPOS_VALIDOS))}."}
    if "amount" in campos:
        try:
            campos["amount"] = float(campos["amount"])
        except (TypeError, ValueError):
            return {"error": "Monto inválido."}
    if "transaction_date" in campos and not re.match(r"^\d{4}-\d{2}-\d{2}$", str(campos["transaction_date"] or "")):
        return {"error": "Fecha inválida (se espera YYYY-MM-DD)."}
    if "tags" in campos:
        if not isinstance(campos["tags"], list):
            return {"error": "tags debe ser una lista de nombres."}
        campos["tags"] = [str(t).strip() for t in campos["tags"] if str(t).strip()][:20]

    from db_pool import get_conn, put_conn
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT payload, status FROM transaction_drafts
             WHERE id = %s AND status IN ('BORRADOR', 'ERROR')
               AND (%s::uuid IS NULL OR user_id = %s)
             FOR UPDATE
        """, (draft_id, str(hub_user_id) if hub_user_id else None,
              str(hub_user_id) if hub_user_id else None))
        row = cur.fetchone()
        if not row:
            conn.rollback()
            return {"error": f"El borrador #{draft_id} no existe, no es tuyo o ya no es editable."}

        payload = row[0] if isinstance(row[0], dict) else json.loads(row[0])
        editados = set(campos.keys())
        payload.update(campos)
        if "payment_method" in campos:
            # El humano cambió la cuenta por nombre: el id resuelto antes (SMS,
            # etapa 09.F) deja de valer y se re-resuelve por nombre al confirmar.
            payload["account_id"] = None
        if tercero:
            tp = payload.get("third_party") or {}
            tp.update({k: v for k, v in tercero.items()
                       if k in ("identification_type", "identification_number", "name")})
            payload["third_party"] = tp
            editados.add("third_party")

        payload["inferred_fields"] = sorted(set(payload.get("inferred_fields") or []) - editados)
        payload["missing_fields"] = compute_missing(payload)

        cur.execute("""
            UPDATE transaction_drafts
               SET payload = %s, status = 'BORRADOR', error = NULL,
                   portfolio_name = %s, updated_at = NOW()
             WHERE id = %s
            RETURNING id, status, channel, portfolio_name, payload, raw_text,
                      media_path, error, confirmed_transaction_id, created_at
        """, (json.dumps(payload), payload.get("portfolio_name"), draft_id))
        r = cur.fetchone()
        conn.commit()
        return {
            "id": r[0], "status": r[1], "channel": r[2], "portfolio_name": r[3],
            "payload": r[4] if isinstance(r[4], dict) else json.loads(r[4]),
            "raw_text": r[5], "media_path": r[6], "error": r[7],
            "confirmed_transaction_id": r[8], "created_at": str(r[9]),
        }
    finally:
        put_conn(conn)


def _cuenta_existente(cur, account_id):
    """→ el id si esa cuenta sigue existiendo en user_accounts; None si no
    (cuenta borrada, id vacío o basura en el payload)."""
    try:
        account_id = int(account_id)
    except (TypeError, ValueError):
        return None
    cur.execute("SELECT id FROM user_accounts WHERE id = %s", (account_id,))
    row = cur.fetchone()
    return row[0] if row else None


def _revertir(conn, cur, draft_id, motivo: str) -> str:
    """PROCESANDO → BORRADOR con el motivo registrado (validación fallida)."""
    cur.execute("""
        UPDATE transaction_drafts SET status = 'BORRADOR', error = %s, updated_at = NOW()
        WHERE id = %s
    """, (motivo[:500], draft_id))
    conn.commit()
    return f"⚠ No se pudo confirmar el borrador #{draft_id}: {motivo}"


def _explicar_no_tomable(cur, draft_id, chat_link_id, hub_user_id, accion="confirmar") -> str:
    cur.execute("""
        SELECT status, chat_link_id, user_id, confirmed_transaction_id
        FROM transaction_drafts WHERE id = %s
    """, (draft_id,))
    row = cur.fetchone()
    if not row:
        return f"No existe el borrador #{draft_id}. (/borradores para ver los tuyos)"
    status, owner_link, owner_user, tx_id = row
    # Misma semántica que el UPDATE: sin filtro de propiedad (ambos None) no
    # hay restricción de dueño; si se pasa uno, debe coincidir.
    if chat_link_id is None and hub_user_id is None:
        es_dueno = True
    else:
        es_dueno = ((chat_link_id is not None and owner_link == chat_link_id)
                    or (hub_user_id is not None and str(owner_user) == str(hub_user_id)))
    if not es_dueno:
        return f"El borrador #{draft_id} no pertenece a este chat/usuario."
    if status == "CONFIRMADO":
        return f"El borrador #{draft_id} ya fue confirmado (transacción #{tx_id})."
    if status == "DESCARTADO":
        return f"El borrador #{draft_id} ya estaba descartado."
    if status == "PROCESANDO":
        return f"El borrador #{draft_id} se está procesando. Espera unos segundos."
    if status == "ERROR" and accion == "confirmar":
        return (f"El borrador #{draft_id} está en estado ERROR. "
                "Revísalo en la Bandeja web o descártalo.")
    return f"No se pudo {accion} el borrador #{draft_id} (estado: {status})."
