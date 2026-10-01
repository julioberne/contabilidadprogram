# -*- coding: utf-8 -*-
"""FIN-SYS OS v2.0 — Editar y borrar etiquetas (🏷️ Tags del panel de contexto).

Archivo NUEVO (Zero-Impact). `database_driver.actualizar_tag` / `eliminar_tag`
quedan sin usar: hacían el UPDATE/DELETE a ciegas, sin validar ni mirar
quién usa la etiqueta.

Las etiquetas viven POR NOMBRE: `transactions.tags` (TEXT[]) y `payload.tags`
de los borradores del bot; `tag_definitions` (UNIQUE name) solo es el catálogo
que ofrecen el selector de la web y los botones del bot.

Reglas (decisión de Andrés, 1-oct-2026):
  · Renombrar cambia SOLO la definición: las transacciones conservan el
    nombre anterior (no se propaga).
  · Borrar una etiqueta en uso: primero 409 con el conteo; con `forzar` se
    quita de las transacciones y de los borradores abiertos del bot y se borra
    la definición (la web pide una segunda confirmación).

Mitad con BD: recibe el cursor del llamador y NO hace commit.
"""
import re

import psycopg2.errors

from fin_sys_core.terceros_borrado import ESTADOS_BORRADOR_ABIERTO, describir_uso

_COLOR = re.compile(r"^#[0-9a-fA-F]{6}$")
NOMBRE_MAX = 100          # tag_definitions.name VARCHAR(100)


# ══════════════════════════════════════════════════════════════════════════════
# Mitad pura
# ══════════════════════════════════════════════════════════════════════════════

def validar(name=None, color=None):
    """→ mensaje de error, o None si los campos presentes son válidos."""
    if name is not None:
        n = str(name).strip()
        if not n:
            return "El nombre de la etiqueta no puede estar vacío."
        if len(n) > NOMBRE_MAX:
            return f"El nombre no puede superar {NOMBRE_MAX} caracteres."
    if color is not None and not _COLOR.match(str(color).strip()):
        return "El color debe ser hexadecimal, p. ej. #FF9800."
    return None


def mensaje_en_uso(nombre, uso) -> str:
    return f"La etiqueta «{nombre}» está en {describir_uso(uso)}."


def _fila_a_tag(r):
    return {"id": r[0], "name": r[1], "color": r[2]}


# ══════════════════════════════════════════════════════════════════════════════
# Mitad con BD (cursor del llamador; sin commit)
# ══════════════════════════════════════════════════════════════════════════════

def uso_de_etiqueta(cur, nombre) -> dict:
    """→ {"transacciones": n, "borradores": [ids abiertos del bot que la llevan]}"""
    cur.execute("""
        SELECT (SELECT COUNT(*) FROM transactions WHERE tags @> ARRAY[%(nombre)s]::text[]),
               (SELECT COALESCE(array_agg(id ORDER BY id), '{}')
                  FROM transaction_drafts
                 WHERE status IN %(abiertos)s AND payload->'tags' ? %(nombre)s)
    """, {"nombre": nombre, "abiertos": ESTADOS_BORRADOR_ABIERTO})
    txs, borradores = cur.fetchone()
    return {"transacciones": int(txs), "borradores": [int(b) for b in (borradores or [])]}


def actualizar(cur, tag_id, name=None, color=None) -> dict:
    """Nombre y/o color de la definición (las transacciones no se tocan).
    → {"ok": True, "tag": {id, name, color}}
    → {"ok": False, "codigo": "invalido" | "no_existe" | "nombre_duplicado" | "sin_cambios", "error"}"""
    error = validar(name, color)
    if error:
        return {"ok": False, "codigo": "invalido", "error": error}
    if name is None and color is None:
        return {"ok": False, "codigo": "sin_cambios", "error": "Nada que editar."}
    cur.execute("SELECT id, name, color FROM tag_definitions WHERE id = %s FOR UPDATE", (tag_id,))
    fila = cur.fetchone()
    if not fila:
        return {"ok": False, "codigo": "no_existe", "error": "Esa etiqueta no existe."}
    nuevo_nombre = str(name).strip() if name is not None else fila[1]
    nuevo_color = str(color).strip() if color is not None else fila[2]
    if nuevo_nombre != fila[1]:
        cur.execute("SELECT 1 FROM tag_definitions WHERE name = %s AND id <> %s", (nuevo_nombre, tag_id))
        if cur.fetchone():
            return {"ok": False, "codigo": "nombre_duplicado",
                    "error": f"Ya existe una etiqueta llamada «{nuevo_nombre}»."}
    try:
        cur.execute("""
            UPDATE tag_definitions SET name = %s, color = %s WHERE id = %s
            RETURNING id, name, color
        """, (nuevo_nombre, nuevo_color, tag_id))
    except psycopg2.errors.UniqueViolation:
        # Carrera entre la comprobación y el UPDATE: el UNIQUE de la BD manda.
        return {"ok": False, "codigo": "nombre_duplicado",
                "error": f"Ya existe una etiqueta llamada «{nuevo_nombre}»."}
    return {"ok": True, "tag": _fila_a_tag(cur.fetchone())}


def eliminar(cur, tag_id, forzar=False) -> dict:
    """Borra la definición. Si la etiqueta está en uso y no se fuerza, no toca
    nada y devuelve el conteo; forzada, la quita de `transactions.tags` y de
    los borradores abiertos del bot antes de borrarla.
    → {"ok": True, "id", "name", "transacciones_actualizadas", "borradores_actualizados"}
    → {"ok": False, "codigo": "no_existe" | "en_uso", "error", "uso"?}"""
    cur.execute("SELECT name FROM tag_definitions WHERE id = %s FOR UPDATE", (tag_id,))
    fila = cur.fetchone()
    if not fila:
        return {"ok": False, "codigo": "no_existe", "error": "Esa etiqueta no existe."}
    nombre = str(fila[0])
    uso = uso_de_etiqueta(cur, nombre)
    en_uso = bool(uso["transacciones"] or uso["borradores"])
    if en_uso and not forzar:
        return {"ok": False, "codigo": "en_uso", "uso": uso, "error": mensaje_en_uso(nombre, uso)}
    txs = borradores = 0
    if en_uso:
        cur.execute("UPDATE transactions SET tags = array_remove(tags, %s) WHERE tags @> ARRAY[%s]::text[]",
                    (nombre, nombre))
        txs = cur.rowcount
        cur.execute("""
            UPDATE transaction_drafts
               SET payload = jsonb_set(payload, '{tags}', COALESCE(
                       (SELECT jsonb_agg(x) FROM jsonb_array_elements(payload->'tags') AS x
                         WHERE x <> to_jsonb(%(nombre)s::text)), '[]'::jsonb)),
                   updated_at = NOW()
             WHERE status IN %(abiertos)s AND payload->'tags' ? %(nombre)s
        """, {"nombre": nombre, "abiertos": ESTADOS_BORRADOR_ABIERTO})
        borradores = cur.rowcount
    cur.execute("DELETE FROM tag_definitions WHERE id = %s", (tag_id,))
    return {"ok": True, "id": tag_id, "name": nombre,
            "transacciones_actualizadas": txs, "borradores_actualizados": borradores}
