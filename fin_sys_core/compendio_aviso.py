# -*- coding: utf-8 -*-
"""
compendio_aviso.py — 🔔 Aviso por Telegram cuando el cliente abre un compendio
por PRIMERA vez (spec 13.6 §11, decisión de Andrés 06-oct). Archivo NUEVO.

- Solo si COMPENDIO_AVISO_TELEGRAM=1 (producción): una apertura en local no avisa.
- Destino: COMPENDIO_AVISO_CHAT (ids separados por coma) o, si no está, los chats de
  Telegram ACTIVOS vinculados a usuarios owner o superusuario (bot_chat_links).
- Habla directo con la API de Telegram (sendMessage): NO importa bot_telegram ni
  arranca el poller (el token es compartido; el poller vive solo en producción).
- Jamás lanza: corre en segundo plano después de servir la página.
"""
import os
from typing import List

SQL_CHATS = """
    SELECT DISTINCT l.chat_id
      FROM bot_chat_links l
      JOIN hub_users u ON u.id = l.hub_user_id
     WHERE l.channel = 'telegram' AND l.status = 'ACTIVO'
       AND (lower(coalesce(u.role, '')) = 'owner' OR u.is_superuser)
"""


def activo() -> bool:
    return os.getenv("COMPENDIO_AVISO_TELEGRAM", "").strip() == "1" and bool(os.getenv("TELEGRAM_BOT_TOKEN", "").strip())


def destinos(conn=None) -> List[str]:
    fijos = [c.strip() for c in os.getenv("COMPENDIO_AVISO_CHAT", "").split(",") if c.strip()]
    if fijos:
        return fijos
    from fin_sys_core.accounting_files_driver import _conexion
    with _conexion(conn) as c:
        cur = c.cursor()
        cur.execute(SQL_CHATS)
        out = [str(r[0]) for r in cur.fetchall()]
        cur.close()
    return out


def texto(folio: str, nombre: str, dispositivo: str) -> str:
    return (f"🔔 Tu cliente abrió el compendio {folio}\n{nombre}\n{dispositivo}\n"
            "Míralo en ⇩ Exportación → 🔗 Compendios → 📈 Seguimiento.")


def enviar(chat_id: str, mensaje: str) -> bool:
    import httpx
    token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    r = httpx.post(f"https://api.telegram.org/bot{token}/sendMessage",
                   json={"chat_id": chat_id, "text": mensaje[:4096]}, timeout=10.0)
    return r.status_code == 200


def avisar_primera_apertura(folio: str, nombre: str, dispositivo: str) -> int:
    """→ a cuántos chats llegó. Nunca lanza."""
    if not activo():
        return 0
    n = 0
    try:
        for chat in destinos():
            try:
                n += 1 if enviar(chat, texto(folio, nombre, dispositivo)) else 0
            except Exception as e:  # un chat caído no frena a los demás
                print(f"⚠️ [compendio_aviso] {chat}: {e}")
    except Exception as e:
        print(f"⚠️ [compendio_aviso] sin destinos: {e}")
    return n
