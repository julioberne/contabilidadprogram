# -*- coding: utf-8 -*-
"""
migrate_hr_profile_fields_v2.py — Ficha RRHH: desarrollo profesional + bienestar.

Segunda tanda de campos para la ficha del trabajador:
  3. Desarrollo Profesional y Talento
  4. Gestión Operativa y Bienestar

Idempotente: ADD COLUMN IF NOT EXISTS. Correr las veces que sea.

Uso:  python scripts/migrate_hr_profile_fields_v2.py
"""
import sys
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

NEW_COLUMNS = [
    # 3. Desarrollo Profesional y Talento
    "languages",             # Idiomas y nivel de dominio (Ej. Inglés B2)
    "certifications",        # Certificaciones y cursos vigentes
    "software_skills",       # Manejo de software / herramientas
    "development_plan",      # Planes de capacitación / objetivos de desarrollo
    # 4. Gestión Operativa y Bienestar
    "socioeconomic_level",   # Nivel socioeconómico / estrato
    "transport_mode",        # Medio de desplazamiento
    "vehicle_info",          # Vehículo propio (placa / modelo)
    "dependents_detail",     # Hijos / dependientes: nombres, edades, fechas
    "benefits_exemptions",   # Beneficios / exenciones (retención en la fuente, etc.)
]


def _load_env():
    """Carga .env a os.environ sin depender de python-dotenv."""
    env_path = os.path.join(ROOT, ".env")
    if not os.path.exists(env_path):
        return
    with open(env_path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, val = line.partition("=")
            os.environ.setdefault(key.strip(), val.strip().strip('"').strip("'"))


def run():
    _load_env()
    from fin_sys_core.db_pool import get_conn, put_conn
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            for col in NEW_COLUMNS:
                cur.execute(f"ALTER TABLE hr_profiles ADD COLUMN IF NOT EXISTS {col} TEXT;")
        conn.commit()
        print(f"OK — {len(NEW_COLUMNS)} columnas aseguradas en hr_profiles:")
        print("     " + ", ".join(NEW_COLUMNS))
    finally:
        put_conn(conn)


if __name__ == "__main__":
    run()
