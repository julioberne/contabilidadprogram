"""
hr_driver.py — CRUD para el Módulo de Recursos Humanos (08c)
=============================================================
Tablas gestionadas:
  - hr_profiles          → ficha personal del trabajador
  - hr_salaries          → nómina colombiana discriminada
  - hr_employee_companies → vinculación trabajador ↔ empresas CT

Cálculo automático de nómina:
  - devengado_total   = base + auxilio + bonos + comisiones + vacaciones + prima
  - deduccion_empleado = salud_emp + pension_emp + retención + descuentos voluntarios
  - neto              = devengado_total - deduccion_empleado
  - costo_empleador   = salud_emp + pension_emp + ARL + caja + ICBF + SENA
"""

import os
import psycopg2
import psycopg2.extras
from datetime import datetime


class _PooledConn:
    """Wrapper que devuelve la conexión al pool al salir del `with`."""
    def __init__(self):
        from fin_sys_core.db_pool import get_conn, put_conn
        self._get = get_conn
        self._put = put_conn
        self._conn = None

    def __enter__(self):
        self._conn = self._get()
        self._conn.cursor_factory = psycopg2.extras.RealDictCursor
        return self._conn

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._conn:
            try:
                if exc_type:
                    self._conn.rollback()
                else:
                    self._conn.commit()
            except Exception:
                pass
            self._put(self._conn)
            self._conn = None
        return False

def _get_conn():
    """SOL-02: Retorna context manager que usa pool centralizado.
    Uso: with _get_conn() as conn: ..."""
    return _PooledConn()

def _put_conn(conn):
    """SOL-02: Devuelve conexión al pool (uso directo sin with)."""
    from fin_sys_core.db_pool import put_conn
    put_conn(conn)


# ─── PERFIL RRHH ──────────────────────────────────────────────────────────────

def get_hr_profile(user_id: str, workspace_id: str) -> dict:
    """Retorna el perfil RRHH de un trabajador; crea uno vacío si no existe."""
    with _get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT * FROM hr_profiles WHERE user_id = %s AND workspace_id = %s",
                (user_id, workspace_id)
            )
            row = cur.fetchone()
            if row:
                return dict(row)
            # Auto-crear perfil vacío
            cur.execute(
                """INSERT INTO hr_profiles (user_id, workspace_id)
                   VALUES (%s, %s) RETURNING *""",
                (user_id, workspace_id)
            )
            conn.commit()
            return dict(cur.fetchone())


def update_hr_profile(user_id: str, workspace_id: str, data: dict) -> dict:
    """Actualiza el perfil RRHH. Solo actualiza los campos presentes en data."""
    allowed = {
        "cedula", "phone", "address", "birth_date", "hire_date",
        "job_title", "department", "status", "emergency_contact", "notes",
        # Nuevos campos expandidos
        "role_description", "email", "contract_type",
        "bank_name", "bank_account_type", "bank_account_number",
        "eps", "pension_fund", "social_security_no",
        "country", "city", "marital_status", "education_level",
        "skills", "avatar_url",
    }
    fields = {k: v for k, v in data.items() if k in allowed}
    if not fields:
        return get_hr_profile(user_id, workspace_id)

    fields["updated_at"] = datetime.utcnow()
    set_clause = ", ".join(f"{k} = %s" for k in fields)
    values = list(fields.values()) + [user_id, workspace_id]

    with _get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                f"""UPDATE hr_profiles SET {set_clause}
                    WHERE user_id = %s AND workspace_id = %s
                    RETURNING *""",
                values
            )
            if cur.rowcount == 0:
                # No existía → insertar
                conn.rollback()
                cur.execute(
                    "INSERT INTO hr_profiles (user_id, workspace_id) VALUES (%s, %s)",
                    (user_id, workspace_id)
                )
                conn.commit()
                return update_hr_profile(user_id, workspace_id, data)
            conn.commit()
            return dict(cur.fetchone())


# ─── SALARIO ───────────────────────────────────────────────────────────────────

def get_hr_salary(user_id: str, workspace_id: str) -> dict:
    """Retorna la ficha salarial; crea una con defaults si no existe."""
    with _get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT * FROM hr_salaries WHERE user_id = %s AND workspace_id = %s",
                (user_id, workspace_id)
            )
            row = cur.fetchone()
            if row:
                result = dict(row)
            else:
                cur.execute(
                    "INSERT INTO hr_salaries (user_id, workspace_id) VALUES (%s, %s) RETURNING *",
                    (user_id, workspace_id)
                )
                conn.commit()
                result = dict(cur.fetchone())

            result["calculated"] = _calculate_payroll(result)
            return result


def update_hr_salary(user_id: str, workspace_id: str, data: dict) -> dict:
    """Actualiza la ficha salarial."""
    allowed = {
        "salary_type", "base_amount", "transport_allowance", "bonuses",
        "commissions", "vacation_provision", "severance_provision",
        "health_employee_pct", "pension_employee_pct", "tax_withholding",
        "voluntary_deductions", "health_employer_pct", "pension_employer_pct",
        "arl_pct", "family_comp_pct", "icbf_pct", "sena_pct",
        "ipc_adjustment_pct", "ipc_effective_date", "currency"
    }
    fields = {k: v for k, v in data.items() if k in allowed}
    if not fields:
        return get_hr_salary(user_id, workspace_id)

    fields["updated_at"] = datetime.utcnow()
    set_clause = ", ".join(f"{k} = %s" for k in fields)
    values = list(fields.values()) + [user_id, workspace_id]

    with _get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                f"""INSERT INTO hr_salaries (user_id, workspace_id)
                    VALUES (%s, %s)
                    ON CONFLICT (user_id, workspace_id) DO UPDATE SET {set_clause}
                    RETURNING *""",
                [user_id, workspace_id] + list(fields.values())
            )
            conn.commit()
            result = dict(cur.fetchone())
            result["calculated"] = _calculate_payroll(result)
            return result


def _calculate_payroll(s: dict) -> dict:
    """
    Calcula la nómina colombiana completa.
    Retorna dict con devengado, deducciones, neto y costo empleador.
    """
    base        = float(s.get("base_amount", 0) or 0)
    transport   = float(s.get("transport_allowance", 0) or 0)
    bonuses     = float(s.get("bonuses", 0) or 0)
    commissions = float(s.get("commissions", 0) or 0)
    vacations   = float(s.get("vacation_provision", 0) or 0)
    severance   = float(s.get("severance_provision", 0) or 0)

    # Devengado total
    devengado = base + transport + bonuses + commissions + vacations + severance

    # Deducciones empleado
    health_emp   = base * float(s.get("health_employee_pct", 4.0) or 4.0) / 100
    pension_emp  = base * float(s.get("pension_employee_pct", 4.0) or 4.0) / 100
    tax_ret      = float(s.get("tax_withholding", 0) or 0)
    vol_ded      = float(s.get("voluntary_deductions", 0) or 0)
    total_deductions = health_emp + pension_emp + tax_ret + vol_ded

    # Neto empleado
    neto = devengado - total_deductions

    # Aportes empleador (sobre salario base)
    health_er  = base * float(s.get("health_employer_pct", 8.5) or 8.5) / 100
    pension_er = base * float(s.get("pension_employer_pct", 12.0) or 12.0) / 100
    arl        = base * float(s.get("arl_pct", 0.522) or 0.522) / 100
    caja       = base * float(s.get("family_comp_pct", 4.0) or 4.0) / 100
    icbf       = base * float(s.get("icbf_pct", 3.0) or 3.0) / 100
    sena       = base * float(s.get("sena_pct", 2.0) or 2.0) / 100
    total_employer = health_er + pension_er + arl + caja + icbf + sena

    # IPC ajuste
    ipc_pct  = float(s.get("ipc_adjustment_pct", 0) or 0)
    ipc_adj  = base * ipc_pct / 100

    return {
        "devengado_total":    round(devengado, 2),
        "deduccion_empleado": round(total_deductions, 2),
        "neto_a_pagar":       round(neto, 2),
        "costo_empleador":    round(total_employer, 2),
        "costo_total_empresa": round(neto + total_employer, 2),
        "ipc_ajuste":         round(ipc_adj, 2),
        # Desglose
        "detalle": {
            "salud_empleado":    round(health_emp, 2),
            "pension_empleado":  round(pension_emp, 2),
            "retencion":         round(tax_ret, 2),
            "descuentos_vol":    round(vol_ded, 2),
            "salud_empleador":   round(health_er, 2),
            "pension_empleador": round(pension_er, 2),
            "arl":               round(arl, 2),
            "caja_compensacion": round(caja, 2),
            "icbf":              round(icbf, 2),
            "sena":              round(sena, 2),
        }
    }


# ─── EMPRESAS VINCULADAS ──────────────────────────────────────────────────────

def get_employee_companies(user_id: str) -> list:
    """Lista todas las empresas activas vinculadas al trabajador."""
    with _get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT * FROM hr_employee_companies WHERE user_id = %s ORDER BY created_at DESC",
                (user_id,)
            )
            return [dict(r) for r in cur.fetchall()]


def get_all_employee_companies(workspace_id: str) -> list:
    """Lista TODOS los vínculos empleado↔empresa del workspace (para el Mapa de Empresas).
    Filtra por workspace obteniendo los user_ids que pertenecen al workspace vía hr_profiles."""
    with _get_conn() as conn:
        with conn.cursor() as cur:
            # Obtener user_ids que tienen perfil HR en este workspace
            cur.execute(
                "SELECT user_id FROM hr_profiles WHERE workspace_id = %s",
                (workspace_id,)
            )
            ws_user_ids = [row['user_id'] for row in cur.fetchall()]
            if not ws_user_ids:
                # Fallback: devolver todos los links (workspace pequeño)
                cur.execute(
                    """SELECT id, user_id, entity_id, entity_name,
                              role_in_company, start_date, is_active, created_at
                       FROM hr_employee_companies
                       ORDER BY entity_id, created_at"""
                )
            else:
                placeholders = ','.join(['%s'] * len(ws_user_ids))
                cur.execute(
                    f"""SELECT id, user_id, entity_id, entity_name,
                               role_in_company, start_date, is_active, created_at
                        FROM hr_employee_companies
                        WHERE user_id IN ({placeholders})
                        ORDER BY entity_id, created_at""",
                    ws_user_ids
                )
            return [dict(r) for r in cur.fetchall()]


def add_employee_company(user_id: str, entity_id: int, entity_name: str,
                         role: str = None, start_date: str = None) -> dict:
    """Vincula un trabajador a una empresa."""
    with _get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """INSERT INTO hr_employee_companies
                   (user_id, entity_id, entity_name, role_in_company, start_date)
                   VALUES (%s, %s, %s, %s, %s) RETURNING *""",
                (user_id, entity_id, entity_name, role, start_date)
            )
            conn.commit()
            return dict(cur.fetchone())


def remove_employee_company(link_id: str, user_id: str) -> bool:
    """Elimina la vinculación empresa-trabajador."""
    with _get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "DELETE FROM hr_employee_companies WHERE id = %s AND user_id = %s",
                (link_id, user_id)
            )
            conn.commit()
            return cur.rowcount > 0


def update_employee_company(link_id: str, data: dict) -> dict:
    """Actualiza rol o fecha de inicio en la vinculación."""
    allowed = {"role_in_company", "start_date", "is_active"}
    fields = {k: v for k, v in data.items() if k in allowed}
    if not fields:
        return {}
    set_clause = ", ".join(f"{k} = %s" for k in fields)
    with _get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                f"UPDATE hr_employee_companies SET {set_clause} WHERE id = %s RETURNING *",
                list(fields.values()) + [link_id]
            )
            conn.commit()
            row = cur.fetchone()
            return dict(row) if row else {}

# ─── CATEGORÍAS DE DOCUMENTOS ──────────────────────────────────────────────────

DEFAULT_DOC_CATEGORIES = [
    ('contrato',     'Contrato laboral',    '#0EA5E9', 1),
    ('cedula',       'Cedula / ID',         '#10B981', 2),
    ('hoja_vida',    'Hoja de vida',        '#8B5CF6', 3),
    ('fotos',        'Fotos',               '#F59E0B', 4),
    ('clinico',      'Historial clinico',   '#EF4444', 5),
    ('certificados', 'Certificados',        '#06B6D4', 6),
    ('nomina',       'Desprendibles nomina','#84CC16', 7),
    ('financiero',   'Info financiera',     '#F97316', 8),
    ('paz_salvo',    'Paz y salvos',        '#EC4899', 9),
    ('cartas',       'Cartas / Notas',      '#A78BFA', 10),
    ('general',      'General',             '#64748b', 11),
]

def get_doc_categories(workspace_id: str) -> list:
    with _get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT * FROM hr_doc_categories WHERE workspace_id = %s ORDER BY sort_order, name",
                (workspace_id,)
            )
            db_rows = [dict(r) for r in cur.fetchall()]

    # Los defaults se gestionan solo en memoria (la tabla usa UUID, no string IDs)
    # Siempre incluimos los defaults + los custom de BD (merge en memoria)
    default_list = [
        {'id': cid, 'workspace_id': workspace_id, 'name': name, 'color': color,
         'sort_order': order, 'is_default': True, 'created_at': None}
        for cid, name, color, order in DEFAULT_DOC_CATEGORIES
    ]

    # IDs de defaults para no duplicar si alguien los hubiera guardado en BD
    default_ids = {c[0] for c in DEFAULT_DOC_CATEGORIES}
    custom_rows = [r for r in db_rows if r['id'] not in default_ids]

    merged = default_list + custom_rows
    merged.sort(key=lambda r: (r.get('sort_order') or 99, r.get('name') or ''))
    return merged


def add_doc_category(workspace_id: str, name: str, color: str, sort_order: int) -> dict:
    with _get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO hr_doc_categories (workspace_id, name, color, sort_order) VALUES (%s, %s, %s, %s) RETURNING *",
                (workspace_id, name, color, sort_order)
            )
            conn.commit()
            return dict(cur.fetchone())

def update_doc_category(cat_id: str, workspace_id: str, name: str, color: str, sort_order: int) -> dict:
    with _get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE hr_doc_categories SET name=%s, color=%s, sort_order=%s WHERE id=%s AND workspace_id=%s RETURNING *",
                (name, color, sort_order, cat_id, workspace_id)
            )
            conn.commit()
            row = cur.fetchone()
            return dict(row) if row else {}

def delete_doc_category(cat_id: str, workspace_id: str) -> bool:
    with _get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "DELETE FROM hr_doc_categories WHERE id=%s AND workspace_id=%s",
                (cat_id, workspace_id)
            )
            conn.commit()
            return cur.rowcount > 0


# ─── HISTORIAL DE PAGOS ────────────────────────────────────────────────────────

def get_payment_records(user_id: str, workspace_id: str) -> list:
    with _get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT * FROM hr_payment_records WHERE user_id = %s AND workspace_id = %s ORDER BY period_year DESC, period_month DESC",
                (user_id, workspace_id)
            )
            return [dict(r) for r in cur.fetchall()]

def add_payment_record(user_id: str, workspace_id: str, data: dict) -> dict:
    allowed = {'period_label','period_month','period_year','base_amount',
               'devengado_total','deduccion_empleado','neto_a_pagar','costo_empleador','payment_date'}
    fields = {k: v for k, v in data.items() if k in allowed and v is not None}
    fields['user_id'] = user_id
    fields['workspace_id'] = workspace_id
    cols = ', '.join(fields.keys())
    phs  = ', '.join(['%s'] * len(fields))
    with _get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                f'INSERT INTO hr_payment_records ({cols}) VALUES ({phs}) RETURNING *',
                list(fields.values())
            )
            conn.commit()
            return dict(cur.fetchone())

def attach_payment_voucher(record_id: str, doc_id: str) -> dict:
    with _get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                'UPDATE hr_payment_records SET voucher_document_id=%s WHERE id=%s RETURNING *',
                (doc_id, record_id)
            )
            conn.commit()
            row = cur.fetchone()
            return dict(row) if row else {}


# ─── CATEGORÍAS DE DOCUMENTOS ──────────────────────────────────────────────────

_DEFAULT_DOC_CATS = [
    ('contrato',     'Contrato laboral',     '#0EA5E9', 1),
    ('cedula',       'Cedula / ID',          '#10B981', 2),
    ('hoja_vida',    'Hoja de vida',         '#8B5CF6', 3),
    ('fotos',        'Fotos',                '#F59E0B', 4),
    ('clinico',      'Historial clinico',    '#EF4444', 5),
    ('certificados', 'Certificados',         '#06B6D4', 6),
    ('nomina',       'Desprendibles nomina', '#84CC16', 7),
    ('financiero',   'Info financiera',      '#F97316', 8),
    ('paz_salvo',    'Paz y salvos',         '#EC4899', 9),
    ('cartas',       'Cartas / Notas',       '#A78BFA', 10),
    ('general',      'General',              '#64748b', 11),
]


def get_doc_categories(workspace_id: str) -> list:
    """Retorna SIEMPRE las 11 categorías por defecto + las custom del workspace."""
    with _get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT * FROM hr_doc_categories WHERE workspace_id = %s ORDER BY sort_order, name",
                (workspace_id,)
            )
            db_rows = [dict(r) for r in cur.fetchall()]

    # Defaults siempre en memoria (la tabla usa UUID, no acepta IDs tipo string)
    default_ids = {c[0] for c in _DEFAULT_DOC_CATS}
    custom_rows = [r for r in db_rows if r['id'] not in default_ids]

    defaults = [
        {'id': cid, 'workspace_id': workspace_id, 'name': name, 'color': color,
         'sort_order': order, 'is_default': True, 'created_at': None}
        for cid, name, color, order in _DEFAULT_DOC_CATS
    ]

    merged = defaults + [dict(r, is_default=False) for r in custom_rows]
    merged.sort(key=lambda r: (r.get('sort_order') or 99, r.get('name') or ''))
    return merged



def add_doc_category(workspace_id: str, name: str, color: str, sort_order: int) -> dict:
    with _get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO hr_doc_categories (workspace_id, name, color, sort_order) VALUES (%s, %s, %s, %s) RETURNING *",
                (workspace_id, name, color, sort_order)
            )
            conn.commit()
            return dict(cur.fetchone())


def update_doc_category(cat_id: str, workspace_id: str, name: str, color: str, sort_order: int) -> dict:
    with _get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE hr_doc_categories SET name=%s, color=%s, sort_order=%s WHERE id=%s AND workspace_id=%s RETURNING *",
                (name, color, sort_order, cat_id, workspace_id)
            )
            conn.commit()
            row = cur.fetchone()
            return dict(row) if row else {}


def delete_doc_category(cat_id: str, workspace_id: str) -> bool:
    with _get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "DELETE FROM hr_doc_categories WHERE id=%s AND workspace_id=%s",
                (cat_id, workspace_id)
            )
            conn.commit()
            return cur.rowcount > 0

