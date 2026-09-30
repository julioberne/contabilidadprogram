# -*- coding: utf-8 -*-
"""FIN-SYS OS v2.0 — Etapa 09.G: medios de pago de un tercero.

Un tercero es UNA ficha (third_parties) con VARIOS medios de pago: las
cuentas, celulares y llaves a las que se le transfiere, y el nombre con que
el banco lo llama en sus SMS (remitente de una transferencia recibida,
comercio de una compra). Tabla propia `third_party_accounts` (Zero-Impact:
no altera ninguna tabla existente).

Regla 6b — aquí nada se adivina ni se aprende solo:
  · Registrar un medio es SIEMPRE un acto humano: el botón 💾 del bot o el
    módulo Terceros de la web.
  · El cruce es por IGUALDAD del identificador completo, normalizado.
  · Un medio pertenece a un solo tercero (UNIQUE tipo+valor); cambiarlo de
    dueño también es explícito (`mover`).
Spec: docs/specs/09-bot-ia/09.G-completar-borrador.md §10.
"""
import re
import unicodedata

TIPOS = ("celular", "cuenta", "llave", "nombre_banco")
TERCERO_GENERICO = "999999999"

DDL = """
CREATE TABLE IF NOT EXISTS third_party_accounts (
    id SERIAL PRIMARY KEY,
    third_party_id BIGINT NOT NULL REFERENCES third_parties(id) ON DELETE CASCADE,
    tipo TEXT NOT NULL CHECK (tipo IN ('celular', 'cuenta', 'llave', 'nombre_banco')),
    valor TEXT NOT NULL,              -- identificador COMPLETO, normalizado (ver normalizar)
    banco TEXT,                       -- opcional, informativo: Nequi, Bancolombia…
    etiqueta TEXT,                    -- opcional: "ahorros", "cuenta de la mamá"…
    origen TEXT NOT NULL DEFAULT 'web' CHECK (origen IN ('web', 'bot')),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (tipo, valor)
);
CREATE INDEX IF NOT EXISTS idx_third_party_accounts_tercero
    ON third_party_accounts(third_party_id);
"""


def init_table(conn=None) -> None:
    """Crea la tabla si falta (arranque del server y migración)."""
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


# ══════════════════════════════════════════════════════════════════════════════
# Mitad pura
# ══════════════════════════════════════════════════════════════════════════════

def _sin_tildes(s: str) -> str:
    s = unicodedata.normalize("NFD", s or "")
    return "".join(c for c in s if unicodedata.category(c) != "Mn")


def normalizar(tipo, valor):
    """Forma canónica con la que se guarda y se compara. → str | None (inválido).
      celular       → 10 dígitos que empiezan por 3 (quita +57, espacios, guiones)
      cuenta        → solo dígitos (4 a 20)
      llave         → sin espacios, en minúsculas (celular, cédula, correo o @alias)
      nombre_banco  → MAYÚSCULAS sin tildes ni espacios de más («SANDRA JIMENEZ»)"""
    v = str(valor or "").strip()
    if tipo == "celular":
        d = re.sub(r"\D", "", v)
        if len(d) == 12 and d.startswith("57"):
            d = d[2:]
        return d if re.fullmatch(r"3\d{9}", d) else None
    if tipo == "cuenta":
        d = re.sub(r"\D", "", v)
        return d if 4 <= len(d) <= 20 else None
    if tipo == "llave":
        k = re.sub(r"\s+", "", v).lower()
        return k if 3 <= len(k) <= 80 else None
    if tipo == "nombre_banco":
        n = re.sub(r"\s+", " ", _sin_tildes(v)).strip(" .,;").upper()
        return n if 2 <= len(n) <= 100 else None
    return None


def describir(tipo, valor) -> str:
    """Texto corto para botones y mensajes."""
    if tipo == "celular":
        return f"cel {valor}"
    if tipo == "cuenta":
        return f"cuenta *{valor}"
    if tipo == "llave":
        return f"llave {valor}"
    return f"«{valor}»"


def medio_de_sms(sms):
    """El identificador de la CONTRAPARTE que trae un SMS ya parseado
    (sms_bancolombia.parsear). → (tipo, valor) | None
      transferencia_enviada  → celular o cuenta de destino
      pago_qr                → llave de destino
      transferencia_recibida → nombre del remitente tal como lo escribe el banco
      compra_tarjeta         → nombre del comercio tal como lo escribe el banco"""
    if not sms:
        return None
    familia = sms.get("familia")
    if familia == "transferencia_enviada":
        tipo = "celular" if sms.get("destino_es_celular") else "cuenta"
        crudo = sms.get("destino")
    elif familia == "pago_qr":
        tipo, crudo = "llave", sms.get("destino")
    elif familia in ("transferencia_recibida", "compra_tarjeta"):
        tipo, crudo = "nombre_banco", sms.get("contraparte_nombre")
    else:
        return None
    valor = normalizar(tipo, crudo)
    return (tipo, valor) if valor else None


def medio_de_payload(sms_meta):
    """(tipo, valor) del medio de pago que un borrador guardó en payload["sms"].
    Los borradores anteriores a esta etapa no traen "medio": se deriva —igual de
    determinista— de la familia, el destino y la contraparte que sí guardaron."""
    if not sms_meta:
        return None
    m = sms_meta.get("medio")
    if isinstance(m, dict) and m.get("tipo") in TIPOS and m.get("valor"):
        return (m["tipo"], str(m["valor"]))
    destino = sms_meta.get("destino")
    return medio_de_sms({
        "familia": sms_meta.get("familia"),
        "destino": destino,
        "destino_es_celular": bool(re.fullmatch(r"3\d{9}", str(destino or ""))),
        "contraparte_nombre": sms_meta.get("contraparte"),
    })


_TIPOS_DE_UN_CELULAR = ("celular", "llave", "cuenta")


def _equivalentes(tipo, valor):
    """Un número de celular es UN solo medio aunque se escriba de tres formas:
    celular (Nequi/Daviplata), llave Bre-B o «cuenta» (así lo llama el SMS:
    «a la cuenta *3213795458»). → [(tipo, valor), …] con el exacto primero.
    Lo que no tiene forma de celular solo equivale a sí mismo."""
    if tipo in _TIPOS_DE_UN_CELULAR and re.fullmatch(r"3\d{9}", valor or ""):
        return [(tipo, valor)] + [(t, valor) for t in _TIPOS_DE_UN_CELULAR if t != tipo]
    return [(tipo, valor)]


# ══════════════════════════════════════════════════════════════════════════════
# Mitad con BD (reciben el cursor del llamador; no hacen commit)
# ══════════════════════════════════════════════════════════════════════════════

def _fila_a_medio(r):
    return {"id": r[0], "third_party_id": r[1], "tipo": r[2], "valor": r[3], "banco": r[4],
            "etiqueta": r[5], "origen": r[6], "created_at": str(r[7]) if r[7] else None,
            "descripcion": describir(r[2], r[3])}


def dueno(cur, tipo, valor):
    """Dueño de (tipo, valor) o de su equivalente (un celular registrado como
    llave o como cuenta es el mismo medio). → {"id", "name"} | None"""
    for t, v in _equivalentes(tipo, valor):
        cur.execute("""
            SELECT tp.id, tp.name
              FROM third_party_accounts a JOIN third_parties tp ON tp.id = a.third_party_id
             WHERE a.tipo = %s AND a.valor = %s
        """, (t, v))
        row = cur.fetchone()
        if row:
            return {"id": row[0], "name": str(row[1]).strip()}
    return None


def buscar_tercero(cur, tipo, valor):
    """Tercero dueño de ese medio de pago (o de su equivalente: _equivalentes).
    → dict listo para el payload del borrador, o None."""
    for t, v in _equivalentes(tipo, valor):
        cur.execute("""
            SELECT tp.id, tp.identification_type, tp.identification_number, tp.name, tp.phone
              FROM third_party_accounts a JOIN third_parties tp ON tp.id = a.third_party_id
             WHERE a.tipo = %s AND a.valor = %s
        """, (t, v))
        row = cur.fetchone()
        if row:
            d = {"id": row[0], "identification_type": row[1] or "NIT",
                 "identification_number": str(row[2]), "name": str(row[3]).strip()}
            if row[4]:
                d["phone"] = str(row[4]).strip()
            return d
    return None


def buscar_tercero_seguro(cur, tipo, valor):
    """Igual que buscar_tercero pero a prueba de instalaciones sin migrar:
    si la tabla aún no existe, el error NO envenena la transacción del
    llamador (SAVEPOINT) y simplemente no hay cruce."""
    try:
        cur.execute("SAVEPOINT medio_pago")
        encontrado = buscar_tercero(cur, tipo, valor)
        cur.execute("RELEASE SAVEPOINT medio_pago")
        return encontrado
    except Exception as e:
        try:
            cur.execute("ROLLBACK TO SAVEPOINT medio_pago")
        except Exception:
            pass
        print(f"⚠️ [TERCEROS] cruce por medio de pago no disponible: {e}")
        return None


def listar(cur, third_party_id):
    cur.execute("""
        SELECT id, third_party_id, tipo, valor, banco, etiqueta, origen, created_at
          FROM third_party_accounts WHERE third_party_id = %s ORDER BY id
    """, (third_party_id,))
    return [_fila_a_medio(r) for r in cur.fetchall()]


def agregar(cur, third_party_id, tipo, valor, banco=None, etiqueta=None, origen="web"):
    """Registra un medio de pago en la ficha de un tercero.
    → {"ok": True, "medio": {...}, "ya_existia": bool}
    → {"ok": False, "codigo": str, "error": str, "dueno": {"id","name"} | None}
      codigo: tipo_invalido · valor_invalido · tercero_no_existe · tercero_generico · de_otro"""
    if tipo not in TIPOS:
        return {"ok": False, "codigo": "tipo_invalido", "dueno": None,
                "error": f"Tipo inválido. Válidos: {', '.join(TIPOS)}."}
    v = normalizar(tipo, valor)
    if not v:
        ayuda = {"celular": "10 dígitos que empiezan por 3", "cuenta": "entre 4 y 20 dígitos",
                 "llave": "entre 3 y 80 caracteres", "nombre_banco": "al menos 2 letras"}[tipo]
        return {"ok": False, "codigo": "valor_invalido", "dueno": None,
                "error": f"Valor inválido para {tipo}: se espera {ayuda}."}
    cur.execute("SELECT identification_number FROM third_parties WHERE id = %s", (third_party_id,))
    row = cur.fetchone()
    if not row:
        return {"ok": False, "codigo": "tercero_no_existe", "dueno": None,
                "error": "Ese tercero no existe."}
    if str(row[0]) == TERCERO_GENERICO:
        return {"ok": False, "codigo": "tercero_generico", "dueno": None,
                "error": "«Sin especificar» es el tercero genérico: no puede tener medios de pago."}
    origen = origen if origen in ("web", "bot") else "web"
    # Un medio pertenece a UNA sola ficha, también cuando el mismo celular está
    # escrito con otro tipo (llave / cuenta): el UNIQUE(tipo, valor) no lo ve.
    actual = dueno(cur, tipo, v)
    if actual and actual["id"] != third_party_id:
        return {"ok": False, "codigo": "de_otro", "dueno": actual,
                "error": f"{describir(tipo, v)} ya está registrado en la ficha de {actual['name']}."}
    cur.execute("""
        INSERT INTO third_party_accounts (third_party_id, tipo, valor, banco, etiqueta, origen)
        VALUES (%s, %s, %s, %s, %s, %s)
        ON CONFLICT (tipo, valor) DO NOTHING
        RETURNING id, third_party_id, tipo, valor, banco, etiqueta, origen, created_at
    """, (third_party_id, tipo, v, (banco or "").strip()[:60] or None,
          (etiqueta or "").strip()[:80] or None, origen))
    fila = cur.fetchone()
    if fila:
        return {"ok": True, "medio": _fila_a_medio(fila), "ya_existia": False}
    actual = dueno(cur, tipo, v)
    if actual and actual["id"] == third_party_id:
        cur.execute("""
            SELECT id, third_party_id, tipo, valor, banco, etiqueta, origen, created_at
              FROM third_party_accounts WHERE tipo = %s AND valor = %s
        """, (tipo, v))
        return {"ok": True, "medio": _fila_a_medio(cur.fetchone()), "ya_existia": True}
    nombre = actual["name"] if actual else "otro tercero"
    return {"ok": False, "codigo": "de_otro", "dueno": actual,
            "error": f"{describir(tipo, v)} ya está registrado en la ficha de {nombre}."}


def eliminar(cur, medio_id, third_party_id) -> bool:
    cur.execute("DELETE FROM third_party_accounts WHERE id = %s AND third_party_id = %s",
                (medio_id, third_party_id))
    return cur.rowcount > 0


def mover(cur, tipo, valor, nuevo_third_party_id, origen="bot") -> bool:
    """Cambia de dueño un medio ya registrado (decisión explícita del humano).
    Se lleva también sus equivalentes (el mismo celular escrito como llave o
    como cuenta): un medio no puede quedar repartido entre dos fichas."""
    v = normalizar(tipo, valor)
    if not v:
        return False
    movidos = 0
    for t, val in _equivalentes(tipo, v):
        cur.execute("""
            UPDATE third_party_accounts SET third_party_id = %s, origen = %s
             WHERE tipo = %s AND valor = %s
        """, (nuevo_third_party_id, origen if origen in ("web", "bot") else "bot", t, val))
        movidos += max(cur.rowcount, 0)
    return movidos > 0
