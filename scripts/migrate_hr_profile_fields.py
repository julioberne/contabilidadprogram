# -*- coding: utf-8 -*-
"""
migrate_hr_profile_fields.py — Enriquece la ficha RRHH (hr_profiles).

Agrega campos para capturar la mayor información posible del trabajador:
identidad ampliada, salud/datos físicos, núcleo familiar y dotación.

Idempotente: usa ADD COLUMN IF NOT EXISTS. Correr las veces que sea.

Uso:  python scripts/migrate_hr_profile_fields.py
"""
import sys
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

# Columnas nuevas (todas TEXT para máxima flexibilidad de captura)
NEW_COLUMNS = [
    # Identidad ampliada
    "id_type",                 # Tipo de identificación (CC, CE, TI, Pasaporte, NIT)
    "gender",                  # Género
    "nationality",             # Nacionalidad
    "birth_place",             # Lugar de nacimiento
    "personal_email",          # Correo electrónico personal (distinto del laboral)
    "occupation",              # Ocupación / profesión
    "work_address",            # Domicilio laboral
    "driver_license",          # Licencia de conducción (categoría)
    # Salud y datos físicos
    "blood_type",              # Tipo de sangre y RH (ej. O+)
    "height_cm",               # Estatura
    "weight_kg",               # Peso
    "preexisting_conditions",  # Enfermedades preexistentes
    "allergies",               # Alergias
    "disability",              # Discapacidad / condición médica especial
    # Núcleo familiar y dotación
    "lives_with",              # Con quién vive
    "dependents_count",        # Personas a cargo / dependientes
    "uniform_shirt_size",      # Talla de camisa (dotación)
    "uniform_pants_size",      # Talla de pantalón (dotación)
    "shoe_size",               # Talla de calzado (dotación)
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
