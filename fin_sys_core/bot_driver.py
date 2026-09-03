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
    "Yo lo convierto en un BORRADOR. Nada toca tu contabilidad hasta que\n"
    "respondas \"Confirmar #N\".\n\n"
    "Comandos:\n"
    "  Confirmar #N — oficializa el borrador (crea transacción + asiento)\n"
    "  Descartar #N — elimina el borrador\n"
    "  /borradores — lista tus borradores pendientes\n"
    "  /ayuda — este mensaje\n\n"
    "Para corregir un borrador: descártalo y envía la operación de nuevo\n"
    "(o edítalo desde la Bandeja en la web)."
)

NO_VINCULADO = (
    "🔒 Este bot es privado.\n"
    "Para vincular tu cuenta: entra a FIN-SYS en la web, genera un código de\n"
    "vinculación y envíame: /vincular TUCODIGO"
)

NO_SOPORTADO = (
    "Por ahora entiendo texto y notas de voz. Fotos de facturas y ubicación\n"
    "llegan en una próxima etapa 📸📍"
)

# ── Comandos deterministas (regex — confirmar/descartar JAMÁS pasan por el LLM) ──
_RE_CONFIRM = re.compile(r"^\s*/?confirmar\s*#?\s*(\d+)?\s*$", re.IGNORECASE)
_RE_DISCARD = re.compile(r"^\s*/?descartar\s*#?\s*(\d+)?\s*$", re.IGNORECASE)
_RE_LINK    = re.compile(r"^\s*/?vincular\s+([A-Za-z0-9]{4,12})\s*$", re.IGNORECASE)
_RE_AYUDA   = re.compile(r"^\s*/(start|ayuda|help)\s*$", re.IGNORECASE)
_RE_DRAFTS  = re.compile(r"^\s*/?borradores\s*$", re.IGNORECASE)


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
        f"Fecha: {payload.get('transaction_date')}",
        f"Portafolio: {payload.get('portfolio_name')}",
    ]
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
    """Procesa un InboundMessage y devuelve el texto de respuesta (o None si
    el mensaje es un duplicado ya procesado)."""
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
                return confirmar_draft(draft_id, chat_link_id=link["id"])
            return descartar_draft(draft_id, chat_link_id=link["id"])

        # ── Entrada no soportada en el MVP ──
        if msg.get("kind") == "unsupported":
            conn.commit()
            return NO_SOPORTADO

        # ── Registro: texto libre o nota de voz → borrador ──
        texto = msg.get("text") or ""
        if msg.get("kind") == "audio":
            from ai_engine import transcribe_audio_only
            texto = transcribe_audio_only(msg["media_path"])
            if not (texto or "").strip():
                conn.commit()
                return "No pude transcribir la nota de voz. Intenta de nuevo o escríbeme el movimiento."

        reply = _crear_borrador(cur, link, texto, msg, msg_row_id)
        conn.commit()
        return reply
    except Exception as e:
        conn.rollback()
        return f"⚠ Error procesando el mensaje: {e}"
    finally:
        put_conn(conn)


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
        media_db = "/" + str(msg["media_path"]).replace("\\", "/").lstrip("/")

    cur.execute("""
        INSERT INTO transaction_drafts
            (chat_link_id, user_id, channel, portfolio_name, status, schema_version,
             payload, raw_text, media_path, external_message_id)
        VALUES (%s, %s, %s, %s, 'BORRADOR', %s, %s, %s, %s, %s)
        RETURNING id
    """, (link["id"], link["hub_user_id"], msg["channel"], payload["portfolio_name"],
          SCHEMA_VERSION, json.dumps(payload), texto, media_db,
          str(msg.get("external_message_id"))))
    draft_id = cur.fetchone()[0]
    cur.execute("UPDATE bot_messages SET draft_id = %s, chat_link_id = %s WHERE id = %s",
                (draft_id, link["id"], msg_row_id))
    return render_summary(draft_id, payload, inferred, missing)


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
            RETURNING payload, media_path
        """, (draft_id, chat_link_id, chat_link_id,
              str(hub_user_id) if hub_user_id else None,
              str(hub_user_id) if hub_user_id else None))
        row = cur.fetchone()
        conn.commit()                    # la toma del borrador queda firme YA
        if not row:
            return _explicar_no_tomable(cur, draft_id, chat_link_id, hub_user_id, accion="confirmar")

        payload = row[0] if isinstance(row[0], dict) else json.loads(row[0])
        media_path = row[1]

        try:
            return _ejecutar_confirmacion(conn, cur, draft_id, payload, media_path)
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


def _ejecutar_confirmacion(conn, cur, draft_id, payload, media_path):
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

    # 4. Cuenta desde payment_method (nunca confirmar sin cuenta → deuda DT-01).
    #    Se re-resuelve al confirmar: las cuentas pueden haber cambiado desde
    #    que se creó el borrador.
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
        evidence_file_path=media_path,
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
