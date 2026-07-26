# -*- coding: utf-8 -*-
"""
kernel_accounting.py — Motor Contable de Partida Doble (K4)
==============================================================
Este es el CORAZÓN del ERP. Toda acción económica de cualquier módulo
pasa por aquí para registrar asientos de partida doble.

REGLA FUNDAMENTAL:
  En cada asiento: sum(débitos) == sum(créditos)
  Si no cuadra, se rechaza la operación.

CÓMO LO USAN LOS MÓDULOS:
  Los módulos NO llaman esta función directamente.
  Emiten un evento al bus → el bus llama a registrar_asiento().

  # Forma correcta (via event bus):
  event_bus.emit('fin.transaccion.registrada', {
      'workspace_id': 'abc-123',
      'fecha': '2026-06-19',
      'modulo_origen': 'fin',
      'referencia': 'TX-42',
      'descripcion': 'Pago servicios de consultoría',
      'asientos': [
          {'cuenta_codigo': '5105', 'debito': 1000000, 'credito': 0},
          {'cuenta_codigo': '1110', 'debito': 0,       'credito': 1000000},
      ]
  })

TABLA QUE USA:
  kernel_journal_entries — cada fila es una línea de asiento (una cuenta)
"""

import logging
import uuid
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Dict, Any, List, Optional
from psycopg2.extras import RealDictCursor

logger = logging.getLogger("kernel.accounting")

# Importar pool de conexiones centralizado
from fin_sys_core.db_pool import get_conn, put_conn

# Un centavo: todo monto se normaliza a 2 decimales con Decimal (nunca float)
_CENT = Decimal("0.01")

# Tipo de cuenta según el primer dígito del PUC colombiano
_PUC_TIPO = {
    "1": "ACTIVO", "2": "PASIVO", "3": "PATRIMONIO",
    "4": "INGRESO", "5": "GASTO", "6": "GASTO", "7": "GASTO",
}


def _monto(valor: Any) -> Decimal:
    """Convierte a Decimal de 2 decimales. str(x) evita el ruido binario de float."""
    try:
        return Decimal(str(valor if valor is not None else 0)).quantize(_CENT, rounding=ROUND_HALF_UP)
    except (InvalidOperation, ValueError):
        raise PartidaDobleError(f"Monto inválido en asiento: {valor!r}")


def derivar_tipo_puc(cuenta_codigo: str) -> str:
    """Deriva ACTIVO/PASIVO/... del primer dígito del código PUC."""
    return _PUC_TIPO.get(str(cuenta_codigo or "")[:1], "")


# ══════════════════════════════════════════════════════════════════════════════
# EXCEPCIONES
# ══════════════════════════════════════════════════════════════════════════════

class PartidaDobleError(Exception):
    """Se lanza cuando un asiento no cumple Debe = Haber."""
    pass


class CuentaNoExisteError(Exception):
    """Se lanza cuando un código de cuenta no existe en el COA del portafolio."""
    pass


# ══════════════════════════════════════════════════════════════════════════════
# INICIALIZACIÓN — Crear tabla si no existe
# ══════════════════════════════════════════════════════════════════════════════

def init_journal_entries_table():
    """
    Crea la tabla kernel_journal_entries en PostgreSQL si no existe.
    Llamar al iniciar el servidor (dentro del lifespan).
    """
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute("""
        CREATE TABLE IF NOT EXISTS kernel_journal_entries (
            id SERIAL PRIMARY KEY,
            
            -- Identificación
            entry_group_id VARCHAR(50) NOT NULL,
            
            -- Temporal
            fecha DATE NOT NULL,
            
            -- Cuenta contable
            cuenta_codigo VARCHAR(50) NOT NULL,
            cuenta_nombre VARCHAR(150),
            cuenta_tipo VARCHAR(20),
            
            -- Partida doble
            debito NUMERIC(18, 2) NOT NULL DEFAULT 0,
            credito NUMERIC(18, 2) NOT NULL DEFAULT 0,
            
            -- Trazabilidad
            modulo_origen VARCHAR(30) NOT NULL,
            referencia VARCHAR(100),
            descripcion TEXT,
            
            -- Metadata
            created_at TIMESTAMPTZ DEFAULT NOW()
        );
        """)

        # Idempotencia: número de línea dentro del grupo + índice ÚNICO parcial.
        # Un re-emit del mismo (modulo, referencia) choca en la línea 1 y se
        # rechaza completo — imposible duplicar asientos de una misma TX.
        cur.execute("""
        ALTER TABLE kernel_journal_entries
            ADD COLUMN IF NOT EXISTS linea INTEGER;
        """)
        cur.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS uq_journal_modulo_ref_linea
            ON kernel_journal_entries(modulo_origen, referencia, linea)
            WHERE referencia IS NOT NULL AND referencia <> '' AND linea IS NOT NULL;
        """)

        # Índices para consultas frecuentes
        cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_journal_entry_group
            ON kernel_journal_entries(entry_group_id);
        """)
        cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_journal_fecha
            ON kernel_journal_entries(fecha);
        """)
        cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_journal_cuenta
            ON kernel_journal_entries(cuenta_codigo);
        """)
        cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_journal_modulo
            ON kernel_journal_entries(modulo_origen);
        """)

        conn.commit()
        cur.close()
        logger.info("✅ Tabla kernel_journal_entries inicializada")
        print("✅ Kernel: tabla kernel_journal_entries lista")
    except Exception as e:
        conn.rollback()
        logger.error(f"❌ Error inicializando kernel_journal_entries: {e}")
        print(f"⚠️ Error creando kernel_journal_entries: {e}")
    finally:
        put_conn(conn)


# ══════════════════════════════════════════════════════════════════════════════
# FUNCIÓN CENTRAL — Registrar Asiento de Partida Doble
# ══════════════════════════════════════════════════════════════════════════════

def registrar_asiento(evento: Dict[str, Any]) -> Dict[str, Any]:
    """
    Recibe un Evento Contable y crea los asientos de partida doble.
    
    REGLA: sum(débitos) == sum(créditos) — si no, rechaza.
    
    Args:
        evento: {
            'fecha': '2026-06-19',
            'modulo_origen': 'fin',          # quién genera el evento
            'referencia': 'TX-42',           # ID interno del módulo origen
            'descripcion': 'Pago consultoría',
            'asientos': [
                {'cuenta_codigo': '5105', 'debito': 1000000, 'credito': 0},
                {'cuenta_codigo': '1110', 'debito': 0,       'credito': 1000000},
            ]
        }
    
    Returns:
        {'status': 'ok', 'entry_group_id': 'JE-20260619-001', 'lineas': 2}
    
    Raises:
        PartidaDobleError: Si débitos ≠ créditos
    """
    asientos = evento.get("asientos", [])

    if not asientos:
        raise PartidaDobleError("El evento no contiene asientos")

    # ── Validar partida doble con Decimal y tolerancia CERO ──────────────────
    # float acumula error binario (0.1+0.2 != 0.3); en contabilidad Debe=Haber
    # es exacto o el asiento se rechaza.
    total_debito = sum((_monto(a.get("debito", 0)) for a in asientos), Decimal("0"))
    total_credito = sum((_monto(a.get("credito", 0)) for a in asientos), Decimal("0"))

    if total_debito != total_credito:
        raise PartidaDobleError(
            f"Partida doble no cuadra: Débitos={total_debito:,.2f} ≠ Créditos={total_credito:,.2f}"
        )

    fecha = evento.get("fecha", "1900-01-01")
    modulo = evento.get("modulo_origen", "unknown")
    referencia = evento.get("referencia", "")
    descripcion = evento.get("descripcion", "")

    conn = get_conn()
    try:
        cur = conn.cursor()

        # ── Idempotencia (chequeo rápido) ─────────────────────────────────────
        # Si este módulo ya asentó esta referencia, no se duplica. El índice
        # único uq_journal_modulo_ref_linea cubre además la carrera concurrente.
        if referencia:
            cur.execute("""
                SELECT entry_group_id FROM kernel_journal_entries
                WHERE modulo_origen = %s AND referencia = %s LIMIT 1
            """, (modulo, referencia))
            existente = cur.fetchone()
            if existente:
                logger.info(f"↩️ Asiento ya existente para {modulo}/{referencia} — omitido (idempotencia)")
                return {
                    "status": "skipped_duplicate",
                    "entry_group_id": existente[0],
                    "lineas": 0,
                }

        # ── Validar que las cuentas existen ───────────────────────────────────
        # Un código es válido si está en el catálogo (chart_of_accounts) O si
        # una posting rule activa lo declara (el COA por portafolio suele estar
        # incompleto respecto a las reglas Zero-COA, que son la fuente de verdad).
        codigos = sorted({str(a.get("cuenta_codigo", "")).strip() for a in asientos})
        if any(not c for c in codigos):
            raise CuentaNoExisteError("Asiento con cuenta_codigo vacío")
        cur.execute("""
            SELECT DISTINCT code FROM chart_of_accounts WHERE code = ANY(%(c)s)
            UNION
            SELECT DISTINCT debit_account_code FROM posting_rules
                WHERE is_active AND debit_account_code = ANY(%(c)s)
            UNION
            SELECT DISTINCT credit_account_code FROM posting_rules
                WHERE is_active AND credit_account_code = ANY(%(c)s)
        """, {"c": codigos})
        existentes = {r[0] for r in cur.fetchall()}
        faltantes = [c for c in codigos if c not in existentes]
        if faltantes:
            raise CuentaNoExisteError(
                f"Cuentas inexistentes (ni en COA ni en posting rules): {', '.join(faltantes)}. "
                f"Carga el plan de cuentas o corrige la posting rule."
            )

        # ── ID de grupo sin COUNT+1 (el COUNT era una condición de carrera) ──
        fecha_clean = str(fecha).replace("-", "")
        entry_group_id = f"JE-{fecha_clean}-{uuid.uuid4().hex[:6].upper()}"

        # ── Insertar cada línea del asiento ───────────────────────────────────
        for num_linea, asiento in enumerate(asientos, start=1):
            cuenta_codigo = str(asiento.get("cuenta_codigo", "")).strip()
            cuenta_nombre = asiento.get("cuenta_nombre", "")
            cuenta_tipo = asiento.get("cuenta_tipo") or derivar_tipo_puc(cuenta_codigo)
            debito = _monto(asiento.get("debito", 0))
            credito = _monto(asiento.get("credito", 0))

            cur.execute("""
                INSERT INTO kernel_journal_entries
                    (entry_group_id, fecha, cuenta_codigo, cuenta_nombre, cuenta_tipo,
                     debito, credito, modulo_origen, referencia, descripcion, linea)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                entry_group_id, fecha, cuenta_codigo, cuenta_nombre, cuenta_tipo,
                debito, credito, modulo, referencia, descripcion, num_linea
            ))

        conn.commit()
        cur.close()

        logger.info(
            f"✅ Asiento {entry_group_id}: {len(asientos)} líneas | "
            f"Db={total_debito:,.2f} Cr={total_credito:,.2f} | "
            f"Módulo={modulo} Ref={referencia}"
        )

        return {
            "status": "ok",
            "entry_group_id": entry_group_id,
            "lineas": len(asientos),
            "total_debito": float(total_debito),
            "total_credito": float(total_credito),
        }

    except (PartidaDobleError, CuentaNoExisteError):
        conn.rollback()
        raise
    except Exception as e:
        conn.rollback()
        # Carrera perdida contra el índice único = otro proceso ya asentó esto
        if "uq_journal_modulo_ref_linea" in str(e):
            logger.info(f"↩️ Asiento duplicado bloqueado por índice único: {modulo}/{referencia}")
            return {"status": "skipped_duplicate", "entry_group_id": None, "lineas": 0}
        logger.error(f"❌ Error registrando asiento: {e}")
        raise
    finally:
        put_conn(conn)


# ══════════════════════════════════════════════════════════════════════════════
# CONSULTAS — Leer asientos del libro diario
# ══════════════════════════════════════════════════════════════════════════════

def obtener_asientos(
    fecha_desde: Optional[str] = None,
    fecha_hasta: Optional[str] = None,
    modulo_origen: Optional[str] = None,
    cuenta_codigo: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
) -> List[Dict[str, Any]]:
    """
    Consulta asientos del libro diario con filtros opcionales.
    Retorna las líneas individuales agrupables por entry_group_id.
    """
    conn = get_conn()
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        conditions = []
        params = []
        
        if fecha_desde:
            conditions.append("fecha >= %s")
            params.append(fecha_desde)
        if fecha_hasta:
            conditions.append("fecha <= %s")
            params.append(fecha_hasta)
        if modulo_origen:
            conditions.append("modulo_origen = %s")
            params.append(modulo_origen)
        if cuenta_codigo:
            conditions.append("cuenta_codigo = %s")
            params.append(cuenta_codigo)
        
        where = ""
        if conditions:
            where = "WHERE " + " AND ".join(conditions)
        
        query = f"""
            SELECT id, entry_group_id, fecha, cuenta_codigo, cuenta_nombre,
                   cuenta_tipo, debito, credito, modulo_origen, referencia,
                   descripcion, created_at
            FROM kernel_journal_entries
            {where}
            ORDER BY fecha DESC, entry_group_id, id
            LIMIT %s OFFSET %s
        """
        params.extend([limit, offset])
        
        cur.execute(query, params)
        rows = cur.fetchall()
        cur.close()
        return [dict(r) for r in rows]
    except Exception as e:
        logger.error(f"Error consultando asientos: {e}")
        return []
    finally:
        put_conn(conn)


def obtener_balance_por_cuenta(
    fecha_desde: Optional[str] = None,
    fecha_hasta: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Genera un balance de sumas y saldos agrupado por cuenta.
    Para cada cuenta: total_debito, total_credito, saldo (Db - Cr).
    
    Esto es la base para generar:
    - Balance General (cuentas 1, 2, 3)
    - Estado de Resultados / P&L (cuentas 4, 5)
    """
    conn = get_conn()
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        conditions = []
        params = []
        
        if fecha_desde:
            conditions.append("fecha >= %s")
            params.append(fecha_desde)
        if fecha_hasta:
            conditions.append("fecha <= %s")
            params.append(fecha_hasta)
        
        where = ""
        if conditions:
            where = "WHERE " + " AND ".join(conditions)
        
        query = f"""
            SELECT 
                cuenta_codigo,
                cuenta_nombre,
                cuenta_tipo,
                SUM(debito) as total_debito,
                SUM(credito) as total_credito,
                SUM(debito) - SUM(credito) as saldo
            FROM kernel_journal_entries
            {where}
            GROUP BY cuenta_codigo, cuenta_nombre, cuenta_tipo
            ORDER BY cuenta_codigo
        """
        
        cur.execute(query, params)
        rows = cur.fetchall()
        cur.close()
        return [dict(r) for r in rows]
    except Exception as e:
        logger.error(f"Error generando balance: {e}")
        return []
    finally:
        put_conn(conn)


def obtener_resumen_financiero(
    fecha_desde: Optional[str] = None,
    fecha_hasta: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Genera resumen financiero básico: Activos, Pasivos, Patrimonio, Ingresos, Gastos.
    Base para P&L y Balance General.
    """
    balances = obtener_balance_por_cuenta(fecha_desde, fecha_hasta)
    
    resumen = {
        "activos": 0.0,
        "pasivos": 0.0,
        "patrimonio": 0.0,
        "ingresos": 0.0,
        "gastos": 0.0,
        "utilidad_neta": 0.0,
        "ecuacion_contable": True,  # Activos = Pasivos + Patrimonio
    }
    
    for cuenta in balances:
        tipo = (cuenta.get("cuenta_tipo") or "").upper()
        saldo = float(cuenta.get("saldo", 0))
        
        if tipo == "ACTIVO":
            resumen["activos"] += saldo
        elif tipo == "PASIVO":
            resumen["pasivos"] += abs(saldo)  # Pasivos tienen saldo acreedor
        elif tipo == "PATRIMONIO":
            resumen["patrimonio"] += abs(saldo)
        elif tipo == "INGRESO":
            resumen["ingresos"] += abs(saldo)
        elif tipo == "GASTO":
            resumen["gastos"] += saldo
    
    resumen["utilidad_neta"] = resumen["ingresos"] - resumen["gastos"]
    
    # Verificar ecuación contable: A = P + Pt + (I - G)
    lado_izq = resumen["activos"]
    lado_der = resumen["pasivos"] + resumen["patrimonio"] + resumen["utilidad_neta"]
    resumen["ecuacion_contable"] = abs(lado_izq - lado_der) < 0.01
    
    return resumen
