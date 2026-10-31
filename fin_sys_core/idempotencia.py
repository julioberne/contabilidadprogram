# -*- coding: utf-8 -*-
"""idempotencia.py — Un envío, una transacción (estándar H8.2).

La clave entra en la MISMA transacción de BD que el movimiento: existe si y solo
si ese movimiento quedó guardado. Un doble clic o un reintento con la misma clave
espera al primero en el INSERT y luego recibe su transacción, sin crear otra; si
el primero falló, su clave se fue con el rollback y el segundo sigue normal.

Sin la migración (scripts/migrate_h8.py) todo funciona como antes, sin protección
y sin error. Las claves viven 7 días (las borra la tarea `limpieza_cola`).
"""
import hashlib
import json
from typing import Optional

import psycopg2.errors


class TransaccionRepetida(Exception):
    """Ese envío ya quedó guardado: `transaction_id` es la transacción que creó."""

    def __init__(self, transaction_id: int):
        super().__init__(f"Envío repetido de la transacción {transaction_id}")
        self.transaction_id = transaction_id


class ClaveReusada(Exception):
    """La misma clave llegó con otros datos: es un error del cliente, no un reintento."""


def huella_de(datos: dict) -> str:
    return hashlib.sha256(json.dumps(datos, sort_keys=True, default=str).encode("utf-8")).hexdigest()


def reservar(cur, clave: str, huella: Optional[str] = None) -> bool:
    """Reserva la clave con el cursor de la transacción en curso.
    → True si quedó reservada; False sin la migración (la transacción sigue sana).
    Lanza TransaccionRepetida o ClaveReusada si ya estaba."""
    cur.execute("SAVEPOINT idempotencia")
    try:
        cur.execute("""
            INSERT INTO idempotency_keys (clave, huella) VALUES (%s, %s)
            ON CONFLICT (clave) DO NOTHING RETURNING clave
        """, (clave, huella))
    except psycopg2.errors.UndefinedTable:
        cur.execute("ROLLBACK TO SAVEPOINT idempotencia")
        return False
    nueva = cur.fetchone()
    cur.execute("RELEASE SAVEPOINT idempotencia")
    if nueva:
        return True
    cur.execute("SELECT huella, transaction_id FROM idempotency_keys WHERE clave = %s", (clave,))
    huella_previa, transaction_id = cur.fetchone()
    if huella and huella_previa and huella != huella_previa:
        raise ClaveReusada(clave)
    raise TransaccionRepetida(transaction_id)


def guardar(cur, clave: str, transaction_id: int) -> None:
    cur.execute("UPDATE idempotency_keys SET transaction_id = %s WHERE clave = %s", (transaction_id, clave))


def purgar(dias: int = 7) -> int:
    """Borra las claves viejas (los reintentos llegan en segundos o minutos). → cuántas."""
    from fin_sys_core.db_pool import get_conn, put_conn
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute("DELETE FROM idempotency_keys WHERE creada < now() - make_interval(days => %s)", (int(dias),))
        n = cur.rowcount
        conn.commit()
        return n
    except psycopg2.errors.UndefinedTable:
        conn.rollback()
        return 0
    finally:
        put_conn(conn)
