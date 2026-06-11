# -*- coding: utf-8 -*-
"""
FIN-SYS OS v2.0 - Adaptador de Base de Datos PostgreSQL (database_driver.py)
--------------------------------------------------------------------------
Este módulo gestiona la conexión, inicialización de tablas y las operaciones
CRUD relacionales contra la base de datos PostgreSQL/Supabase.
Incluye un MODO SIMULACIÓN en memoria para desarrollo local sin base de datos activa.
"""

import os
import psycopg2
from psycopg2.extras import RealDictCursor
from typing import List, Dict, Any, Optional
import json

# Cargar variables de entorno por defecto (también soportado vía .env en FastAPI)
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_NAME = os.getenv("DB_NAME", "fin_sys_db")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "postgres")
DB_PORT = os.getenv("DB_PORT", "5432")

# --- MODO SIMULACIÓN: Lista en memoria local en caso de que Postgres no esté activo ---
MOCK_TRANSACTIONS: List[Dict[str, Any]] = [
    {
        "id": 1,
        "type": "INGRESO",
        "amount": 125000.00,
        "concept": "Honorarios Consultoría v2",
        "identification_number": "900.120.456-1",
        "third_party_name": "Consultores SAS",
        "transaction_date": "2026-06-02",
        "payment_method": "Banco M",
        "category": "Servicios",
        "tax_iva_amount": 23750.00,
        "tax_gmf_amount": 0.00,
        "net_value": 148750.00,
        "portfolio_name": "Negocio A",
        "geo_maps_link": None,
        "evidence_file_path": None,
        "account_id": 2,
        "dest_account_id": None,
        "trm": 1.0,
        "transaction_currency": "COP"
    },
    {
        "id": 2,
        "type": "GASTO",
        "amount": 74500.00,
        "concept": "Compra Licencias Servidor",
        "identification_number": "500.001.222-3",
        "third_party_name": "Servidores Cloud",
        "transaction_date": "2026-06-02",
        "payment_method": "Tarjeta C",
        "category": "Infraestructura",
        "tax_iva_amount": 0.00,
        "tax_gmf_amount": 298.00,
        "net_value": 74202.00,
        "portfolio_name": "Negocio A",
        "geo_maps_link": None,
        "evidence_file_path": None,
        "account_id": 4,
        "dest_account_id": None,
        "trm": 1.0,
        "transaction_currency": "COP"
    }
]


MOCK_USER_PROFILE = {
    "name": "Andrés",
    "email": "andres@finsys.os",
    "role": "Administrador Contable",
    "avatar_style": "pixel-grid"
}

MOCK_USER_ACCOUNTS = [
    {
        "id": 1,
        "name": "Efectivo",
        "type": "Efectivo",
        "currency": "COP",
        "initial_balance": 50000.0,
        "current_balance": 50000.0
    },
    {
        "id": 2,
        "name": "Bancolombia Ahorros",
        "type": "Ahorros",
        "currency": "COP",
        "initial_balance": 1500000.0,
        "current_balance": 1500000.0
    },
    {
        "id": 3,
        "name": "Nequi",
        "type": "Billetera",
        "currency": "COP",
        "initial_balance": 200000.0,
        "current_balance": 200000.0
    },
    {
        "id": 4,
        "name": "Davivienda Crédito",
        "type": "Crédito",
        "currency": "COP",
        "initial_balance": 0.0,
        "current_balance": -500000.0
    },
    {
        "id": 5,
        "name": "Binance USDT",
        "type": "Crypto",
        "currency": "USD",
        "initial_balance": 100.0,
        "current_balance": 100.0
    }
]

MOCK_PORTFOLIOS = [
    {"id": 1, "name": "Simulación A", "industry_type": "ESTANDAR", "sub_industry_type": "General"},
    {"id": 2, "name": "Simulación B", "industry_type": "ESTANDAR", "sub_industry_type": "Comercial"}
]

MOCK_DB_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "mock_db.json")

def load_mock_db():
    global MOCK_TRANSACTIONS, MOCK_USER_PROFILE, MOCK_USER_ACCOUNTS, MOCK_PORTFOLIOS
    if os.path.exists(MOCK_DB_FILE):
        try:
            with open(MOCK_DB_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if "transactions" in data:
                    MOCK_TRANSACTIONS.clear()
                    MOCK_TRANSACTIONS.extend(data["transactions"])
                if "profile" in data:
                    MOCK_USER_PROFILE.update(data["profile"])
            if "accounts" in data:
                MOCK_USER_ACCOUNTS.clear()
                MOCK_USER_ACCOUNTS.extend(data["accounts"])
            if "portfolios" in data:
                MOCK_PORTFOLIOS.clear()
                MOCK_PORTFOLIOS.extend(data["portfolios"])
        except Exception as e:
            print(f"Error cargando mock DB: {e}")

def save_mock_db():
    data = {
        "transactions": MOCK_TRANSACTIONS,
        "profile": MOCK_USER_PROFILE,
        "accounts": MOCK_USER_ACCOUNTS,
        "portfolios": MOCK_PORTFOLIOS
    }
    try:
        with open(MOCK_DB_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Error guardando mock DB: {e}")

load_mock_db()


IS_POSTGRES_ACTIVE = True


def get_db_connection():
    """Establece y devuelve una conexión a la base de datos PostgreSQL."""
    global IS_POSTGRES_ACTIVE
    if not IS_POSTGRES_ACTIVE:
        raise ConnectionError("PostgreSQL está desconectado (Modo Simulación Activo).")
    return psycopg2.connect(
        host=DB_HOST,
        database=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
        port=DB_PORT,
        connect_timeout=10
    )


def init_db():
    """
    Inicializa las tablas de la base de datos si no existen,
    y activa la extensión pgvector para el RAG inteligente de la IA.
    """
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # 1. Habilitar la extensión de vectores (pgvector)
        try:
            cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")
            conn.commit()
        except Exception as e:
            conn.rollback()
            print(f"⚠️ [AVISO] pgvector no pudo ser inicializado (Omitido para desarrollo local): {e}")

        # 2. Tabla de Portafolios
        cur.execute("""
        CREATE TABLE IF NOT EXISTS portfolios (
            id SERIAL PRIMARY KEY,
            name VARCHAR(50) NOT NULL UNIQUE,
            industry_type VARCHAR(50) DEFAULT 'ESTANDAR',
            sub_industry_type VARCHAR(100) DEFAULT '',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """)

        # Migración temporal para agregar la columna si no existe
        try:
            cur.execute("ALTER TABLE portfolios ADD COLUMN sub_industry_type VARCHAR(100) DEFAULT '';")
            conn.commit()
        except Exception:
            conn.rollback() # La columna ya existe

        # [NEW] Tabla de Perfil de Usuario
        cur.execute("""
        CREATE TABLE IF NOT EXISTS user_profiles (
            id SERIAL PRIMARY KEY,
            name VARCHAR(100) NOT NULL DEFAULT 'Andrés',
            email VARCHAR(100) NOT NULL DEFAULT 'andres@finsys.os',
            role VARCHAR(50) NOT NULL DEFAULT 'Administrador Contable',
            avatar_style VARCHAR(50) NOT NULL DEFAULT 'pixel-grid',
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """)

        # [NEW] Tabla de Cuentas del Usuario
        cur.execute("""
        CREATE TABLE IF NOT EXISTS user_accounts (
            id SERIAL PRIMARY KEY,
            name VARCHAR(100) NOT NULL UNIQUE,
            type VARCHAR(50) NOT NULL,
            currency VARCHAR(10) NOT NULL DEFAULT 'COP',
            initial_balance DECIMAL(15, 2) NOT NULL DEFAULT 0.00,
            current_balance DECIMAL(15, 2) NOT NULL DEFAULT 0.00,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """)

        # 3. Tabla de Terceros ( NIT/CC Mandatorio )
        cur.execute("""
        CREATE TABLE IF NOT EXISTS third_parties (
            id SERIAL PRIMARY KEY,
            identification_type VARCHAR(10) NOT NULL,
            identification_number VARCHAR(30) NOT NULL UNIQUE,
            name VARCHAR(100) NOT NULL,
            email VARCHAR(100),
            phone VARCHAR(30),
            website VARCHAR(150),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """)

        # 4. Tabla de Pockets (Aislamiento de Capital)
        cur.execute("""
        CREATE TABLE IF NOT EXISTS pockets (
            id SERIAL PRIMARY KEY,
            portfolio_id INTEGER NOT NULL REFERENCES portfolios(id) ON DELETE CASCADE,
            name VARCHAR(50) NOT NULL,
            allocated_budget DECIMAL(15, 2) NOT NULL DEFAULT 0.00,
            current_balance DECIMAL(15, 2) NOT NULL DEFAULT 0.00
        );
        """)

        # 5. Tabla de Transacciones
        cur.execute("""
        CREATE TABLE IF NOT EXISTS transactions (
            id SERIAL PRIMARY KEY,
            portfolio_id INTEGER NOT NULL REFERENCES portfolios(id) ON DELETE RESTRICT,
            pocket_id INTEGER REFERENCES pockets(id) ON DELETE SET NULL,
            third_party_id INTEGER NOT NULL REFERENCES third_parties(id) ON DELETE RESTRICT,
            type VARCHAR(15) NOT NULL,
            amount DECIMAL(15, 2) NOT NULL,
            concept VARCHAR(255) NOT NULL,
            transaction_date DATE NOT NULL,
            payment_method VARCHAR(50) NOT NULL,
            category VARCHAR(150) NOT NULL,
            
            tax_iva_percentage DECIMAL(5, 2) DEFAULT 0.00,
            tax_iva_amount DECIMAL(15, 2) DEFAULT 0.00,
            tax_gmf_percentage DECIMAL(5, 2) DEFAULT 0.00,
            tax_gmf_amount DECIMAL(15, 2) DEFAULT 0.00,
            custom_tax_amount DECIMAL(15, 2) DEFAULT 0.00,
            net_value DECIMAL(15, 2) NOT NULL,
            is_recurring BOOLEAN DEFAULT FALSE,
            recurrence_interval VARCHAR(50) DEFAULT 'MENSUAL',
            recurrence_days INTEGER DEFAULT 30,
            
            geo_latitude DECIMAL(10, 8),
            geo_longitude DECIMAL(11, 8),
            geo_maps_link TEXT,
            evidence_file_path TEXT,
            embedding vector(1536),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """)

        # [MIGRACIÓN] Agregar columnas de cuentas y TRM a transactions si no existen
        try:
            cur.execute("ALTER TABLE portfolios ADD COLUMN IF NOT EXISTS industry_type VARCHAR(50) DEFAULT 'ESTANDAR';")
            cur.execute("ALTER TABLE transactions ADD COLUMN IF NOT EXISTS account_id INTEGER REFERENCES user_accounts(id);")
            cur.execute("ALTER TABLE transactions ADD COLUMN IF NOT EXISTS dest_account_id INTEGER REFERENCES user_accounts(id);")
            cur.execute("ALTER TABLE transactions ADD COLUMN IF NOT EXISTS trm DECIMAL(12, 4) DEFAULT 1.0000;")
            cur.execute("ALTER TABLE transactions ADD COLUMN IF NOT EXISTS transaction_currency VARCHAR(10) DEFAULT 'COP';")
            cur.execute("ALTER TABLE transactions ADD COLUMN IF NOT EXISTS is_recurring BOOLEAN DEFAULT FALSE;")
            cur.execute("ALTER TABLE transactions ADD COLUMN IF NOT EXISTS recurrence_interval VARCHAR(50) DEFAULT 'MENSUAL';")
            cur.execute("ALTER TABLE transactions ADD COLUMN IF NOT EXISTS recurrence_days INTEGER DEFAULT 30;")
            cur.execute("ALTER TABLE transactions ADD COLUMN IF NOT EXISTS recurrence_max_reps INTEGER DEFAULT NULL;")
            cur.execute("ALTER TABLE transactions ADD COLUMN IF NOT EXISTS recurrence_start_date DATE DEFAULT NULL;")
            cur.execute("ALTER TABLE transactions ADD COLUMN IF NOT EXISTS recurrence_end_date DATE DEFAULT NULL;")
            cur.execute("ALTER TABLE transactions ALTER COLUMN category TYPE VARCHAR(150);")
            conn.commit()
        except Exception as e:
            conn.rollback()
            print(f"⚠️ [AVISO] Columnas adicionales no pudieron ser agregadas a transactions: {e}")

        # 6. Cuentas por Cobrar/Pagar
        cur.execute("""
        CREATE TABLE IF NOT EXISTS cxp_cxc_ledger (
            id SERIAL PRIMARY KEY,
            transaction_id INTEGER REFERENCES transactions(id) ON DELETE SET NULL,
            third_party_id INTEGER NOT NULL REFERENCES third_parties(id) ON DELETE RESTRICT,
            type VARCHAR(10) NOT NULL,
            original_amount DECIMAL(15, 2) NOT NULL,
            remaining_balance DECIMAL(15, 2) NOT NULL,
            due_date DATE NOT NULL,
            term VARCHAR(20) NOT NULL,
            status VARCHAR(20) NOT NULL DEFAULT 'PENDIENTE',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """)

        # 6.5. Activos (Gestión de Activos)
        cur.execute("""
        CREATE TABLE IF NOT EXISTS assets (
            id SERIAL PRIMARY KEY,
            portfolio_id INTEGER NOT NULL REFERENCES portfolios(id) ON DELETE CASCADE,
            name VARCHAR(100) NOT NULL,
            purchase_value DECIMAL(15, 2) NOT NULL,
            purchase_date DATE NOT NULL,
            custom_tag VARCHAR(50),
            is_passive_income_generator BOOLEAN NOT NULL DEFAULT FALSE,
            recurrence_interval_days INTEGER,
            recurrence_amount DECIMAL(15, 2),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """)

        # 7. Catálogo de Cuentas (COA)
        cur.execute("""
        CREATE TABLE IF NOT EXISTS chart_of_accounts (
            id SERIAL PRIMARY KEY,
            portfolio_id INTEGER NOT NULL REFERENCES portfolios(id) ON DELETE CASCADE,
            code VARCHAR(50) NOT NULL,
            name VARCHAR(150) NOT NULL,
            account_type VARCHAR(20) NOT NULL,
            parent_id INTEGER REFERENCES chart_of_accounts(id) ON DELETE CASCADE,
            is_group BOOLEAN NOT NULL DEFAULT FALSE,
            description TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE (portfolio_id, code)
        );
        """)
        conn.commit()


        # Seeding de Perfil
        try:
            cur.execute("SELECT COUNT(*) FROM user_profiles;")
            if cur.fetchone()[0] == 0:
                cur.execute("""
                INSERT INTO user_profiles (name, email, role, avatar_style)
                VALUES ('Andrés', 'andres@finsys.os', 'Administrador Contable', 'pixel-grid');
                """)
                conn.commit()
        except Exception as e:
            conn.rollback()
            print(f"⚠️ Error al semillar perfil de usuario: {e}")

        # Seeding de Cuentas
        try:
            cur.execute("SELECT COUNT(*) FROM user_accounts;")
            if cur.fetchone()[0] == 0:
                default_accounts = [
                    ('Efectivo', 'Efectivo', 'COP', 50000.0, 50000.0),
                    ('Bancolombia Ahorros', 'Ahorros', 'COP', 1500000.0, 1500000.0),
                    ('Nequi', 'Billetera', 'COP', 200000.0, 200000.0),
                    ('Davivienda Crédito', 'Crédito', 'COP', 0.0, -500000.0),
                    ('Binance USDT', 'Crypto', 'USD', 100.0, 100.0)
                ]
                for name, type_val, curr, init, curr_bal in default_accounts:
                    cur.execute("""
                    INSERT INTO user_accounts (name, type, currency, initial_balance, current_balance)
                    VALUES (%s, %s, %s, %s, %s);
                    """, (name, type_val, curr, init, curr_bal))
                conn.commit()
        except Exception as e:
            conn.rollback()
            print(f"⚠️ Error al semillar cuentas de usuario: {e}")

        conn.commit()
        print("✅ Base de datos PostgreSQL conectada e inicializada correctamente.")
        cur.close()
        conn.close()
    except Exception as e:
        global IS_POSTGRES_ACTIVE
        IS_POSTGRES_ACTIVE = False
        print(f"⚠️ [AVISO] PostgreSQL no detectado en localhost. FIN-SYS correrá en MODO SIMULACIÓN en memoria. Detalle: {e}")


def registrar_transaccion(tx_data: Dict[str, Any]) -> int:
    """
    Registra una transacción contable.
    Si falla la conexión con Postgres, se almacena en memoria local (Mock).
    """
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # 1. Asegurar la existencia del tercero (NIT/CC)
        third_party = tx_data["third_party"]
        cur.execute("""
        INSERT INTO third_parties (identification_type, identification_number, name, email, phone, website)
        VALUES (%s, %s, %s, %s, %s, %s)
        ON CONFLICT (identification_number) 
        DO UPDATE SET name = EXCLUDED.name
        RETURNING id;
        """, (
            third_party["identification_type"],
            third_party["identification_number"],
            third_party["name"],
            third_party.get("email"),
            third_party.get("phone"),
            third_party.get("website")
        ))
        third_party_id = cur.fetchone()[0]

        # 2. Obtener el id del portafolio por nombre
        cur.execute("SELECT id FROM portfolios WHERE name = %s;", (tx_data["portfolio_name"],))
        portfolio_row = cur.fetchone()
        if not portfolio_row:
            cur.execute("INSERT INTO portfolios (name) VALUES (%s) RETURNING id;", (tx_data["portfolio_name"],))
            portfolio_id = cur.fetchone()[0]
        else:
            portfolio_id = portfolio_row[0]

        # 3. Registrar la transacción principal
        cur.execute("""
        INSERT INTO transactions (
            portfolio_id, pocket_id, third_party_id, type, amount, concept, transaction_date, 
            payment_method, category, tax_iva_percentage, tax_iva_amount, tax_gmf_percentage, 
            tax_gmf_amount, custom_tax_amount, net_value, geo_latitude, geo_longitude, 
            geo_maps_link, evidence_file_path,
            account_id, dest_account_id, trm, transaction_currency, is_recurring, recurrence_interval, recurrence_days, recurrence_max_reps, recurrence_start_date, recurrence_end_date
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING id;
        """, (
            portfolio_id,
            tx_data.get("pocket_id"),
            third_party_id,
            tx_data["type"],
            tx_data["amount"],
            tx_data["concept"],
            tx_data["transaction_date"],
            tx_data["payment_method"],
            tx_data["category"],
            tx_data.get("tax_iva_percentage", 0.0),
            tx_data.get("tax_iva_amount", 0.0),
            tx_data.get("tax_gmf_percentage", 0.0),
            tx_data.get("tax_gmf_amount", 0.0),
            tx_data.get("custom_tax_amount", 0.0),
            tx_data["net_value"],
            tx_data.get("geo_latitude"),
            tx_data.get("geo_longitude"),
            tx_data.get("geo_maps_link"),
            tx_data.get("evidence_file_path"),
            tx_data.get("account_id"),
            tx_data.get("dest_account_id"),
            tx_data.get("trm", 1.0),
            tx_data.get("transaction_currency", "COP"),
            tx_data.get("is_recurring", False),
            tx_data.get("recurrence_interval", "MENSUAL"),
            tx_data.get("recurrence_days", 30),
            tx_data.get("recurrence_max_reps"),
            tx_data.get("recurrence_start_date"),
            tx_data.get("recurrence_end_date")
        ))
        transaction_id = cur.fetchone()[0]
        
        # [NEW] Registrar Cartera (CXC / CXP) si se envía
        cxc_cxp = tx_data.get("cxc_cxp")
        if cxc_cxp:
            cur.execute("""
            INSERT INTO cxp_cxc_ledger (
                transaction_id, third_party_id, type, original_amount, remaining_balance, due_date, term, status
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s);
            """, (
                transaction_id,
                third_party_id,
                cxc_cxp["type"],
                tx_data["amount"],
                tx_data["amount"],
                cxc_cxp["due_date"],
                cxc_cxp["term"],
                "PENDIENTE"
            ))

        # [NEW] Registrar Activo si se envía y tiene check de establish_as_asset
        asset = tx_data.get("asset")
        if asset and asset.get("establish_as_asset"):
            cur.execute("""
            INSERT INTO assets (
                portfolio_id, name, purchase_value, purchase_date, custom_tag, is_passive_income_generator, recurrence_interval_days, recurrence_amount
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s);
            """, (
                portfolio_id,
                asset["name"],
                asset["purchase_value"],
                tx_data["transaction_date"],
                asset["custom_tag"],
                asset.get("is_passive_income_generator", False),
                asset.get("recurrence_interval_days", 30) if asset.get("is_passive_income_generator", False) else None,
                asset.get("recurrence_amount", 0.0) if asset.get("is_passive_income_generator", False) else None
            ))
        
        # Recalcular saldos de cuentas
        recalcular_saldos_cuentas(conn)
        
        conn.commit()
        cur.close()
        conn.close()
        return transaction_id
    except Exception as e:
        import traceback
        print("❌ ERROR REGISTRANDO TRANSACCIÓN EN BD:")
        traceback.print_exc()
        # Fallback de Simulación en Memoria
        print(f"🔌 [MODO SIMULACIÓN] Registrando transacción local en memoria: {tx_data['concept']}")
        transaction_id = len(MOCK_TRANSACTIONS) + 1
        new_tx = {
            "id": transaction_id,
            "type": tx_data["type"],
            "amount": tx_data["amount"],
            "concept": tx_data["concept"],
            "transaction_date": tx_data["transaction_date"],
            "payment_method": tx_data["payment_method"],
            "category": tx_data["category"],
            "tax_iva_amount": tx_data.get("tax_iva_amount", 0.0),
            "tax_gmf_amount": tx_data.get("tax_gmf_amount", 0.0),
            "net_value": tx_data["net_value"],
            "portfolio_name": tx_data["portfolio_name"],
            "identification_number": tx_data["third_party"]["identification_number"],
            "third_party_name": tx_data["third_party"]["name"],
            "geo_maps_link": tx_data.get("geo_maps_link"),
            "evidence_file_path": tx_data.get("evidence_file_path"),
            "account_id": tx_data.get("account_id"),
            "dest_account_id": tx_data.get("dest_account_id"),
            "trm": tx_data.get("trm", 1.0),
            "transaction_currency": tx_data.get("transaction_currency", "COP"),
            "is_recurring": tx_data.get("is_recurring", False),
            "recurrence_interval": tx_data.get("recurrence_interval", "MENSUAL"),
            "recurrence_days": tx_data.get("recurrence_days", 30),
            "recurrence_max_reps": tx_data.get("recurrence_max_reps"),
            "recurrence_start_date": tx_data.get("recurrence_start_date"),
            "recurrence_end_date": tx_data.get("recurrence_end_date"),
            "cxc_cxp": tx_data.get("cxc_cxp"),
            "asset": tx_data.get("asset")
        }
        MOCK_TRANSACTIONS.append(new_tx)
        recalcular_saldos_cuentas()
        save_mock_db()
        return transaction_id


def obtener_transacciones(portfolio_name: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Obtiene las transacciones filtrando opcionalmente por portafolio.
    Si falla Postgres, lee de la lista en memoria (Mock).
    """
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        query = """
        SELECT 
            t.id, t.type, t.amount, t.concept, t.transaction_date, t.payment_method, t.category,
            t.tax_iva_amount, t.tax_gmf_amount, t.net_value, t.geo_maps_link, t.evidence_file_path,
            t.account_id, t.dest_account_id, t.trm, t.transaction_currency, t.is_recurring,
            t.recurrence_interval, t.recurrence_days, t.recurrence_max_reps, t.recurrence_start_date, t.recurrence_end_date,
            p.name as portfolio_name, p.industry_type as portfolio_industry, p.sub_industry_type as portfolio_sub_industry,
            tp.identification_type, tp.identification_number, tp.name as third_party_name,
            a.name as account_name,
            da.name as dest_account_name,
            cxc.type as cxc_type, cxc.due_date as cxc_due_date, cxc.term as cxc_term, cxc.status as cxc_status,
            ast.name as asset_name, ast.custom_tag as asset_tag, ast.is_passive_income_generator as asset_is_passive, ast.recurrence_amount as asset_recurrence_amount
        FROM transactions t
        JOIN portfolios p ON t.portfolio_id = p.id
        LEFT JOIN third_parties tp ON t.third_party_id = tp.id
        LEFT JOIN user_accounts a ON t.account_id = a.id
        LEFT JOIN user_accounts da ON t.dest_account_id = da.id
        LEFT JOIN cxp_cxc_ledger cxc ON t.id = cxc.transaction_id
        LEFT JOIN assets ast ON t.portfolio_id = ast.portfolio_id AND t.transaction_date = ast.purchase_date AND t.amount = ast.purchase_value
        """
        params = []
        if portfolio_name:
            query += " WHERE p.name = %s"
            params.append(portfolio_name)
            
        query += " ORDER BY t.transaction_date DESC, t.id DESC;"
        cur.execute(query, params)
        rows = cur.fetchall()
        cur.close()
        conn.close()
        return [dict(r) for r in rows]
    except Exception:
        # Fallback de Simulación en Memoria
        results = []
        for tx in MOCK_TRANSACTIONS:
            if portfolio_name and tx.get("portfolio_name") != portfolio_name:
                continue
            
            # Resolver nombres de cuentas en Mock
            acc_name = None
            dest_acc_name = None
            acc_id = tx.get("account_id")
            dest_id = tx.get("dest_account_id")
            for acc in MOCK_USER_ACCOUNTS:
                if acc["id"] == acc_id:
                    acc_name = acc["name"]
                if acc["id"] == dest_id:
                    dest_acc_name = acc["name"]
                    
            results.append({
                **tx,
                "account_name": acc_name,
                "dest_account_name": dest_acc_name,
                "portfolio_industry": "SERVICIOS",
                "portfolio_sub_industry": "Desarrollo de Software",
                "cxc_type": tx.get("cxc_cxp", {}).get("type") if tx.get("cxc_cxp") else None,
                "cxc_due_date": tx.get("cxc_cxp", {}).get("due_date") if tx.get("cxc_cxp") else None,
                "cxc_term": tx.get("cxc_cxp", {}).get("term") if tx.get("cxc_cxp") else None,
                "cxc_status": "PENDIENTE" if tx.get("cxc_cxp") else None,
                "asset_name": tx.get("asset", {}).get("name") if tx.get("asset") else None,
                "asset_tag": tx.get("asset", {}).get("custom_tag") if tx.get("asset") else None,
                "asset_is_passive": tx.get("asset", {}).get("is_passive_income_generator") if tx.get("asset") else None,
                "asset_recurrence_amount": tx.get("asset", {}).get("recurrence_amount") if tx.get("asset") else None
            })
        return results


def actualizar_transaccion(tx_id: int, update_data: Dict[str, Any]) -> bool:
    """
    Actualiza campos específicos de una transacción y su tercero asociado.
    Si falla PostgreSQL, actualiza en la lista en memoria (Mock).
    """
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # 1. Obtener el third_party_id asociado a la transaccion
        cur.execute("SELECT third_party_id FROM transactions WHERE id = %s;", (tx_id,))
        row = cur.fetchone()
        if not row:
            raise ValueError(f"Transacción con ID {tx_id} no encontrada.")
        third_party_id = row[0]
        
        # 2. Actualizar datos en transactions
        tx_fields = []
        tx_params = []
        for col in ["type", "amount", "concept", "transaction_date", "payment_method", "category", "net_value", "account_id", "dest_account_id", "trm", "transaction_currency", "is_recurring", "recurrence_interval", "recurrence_days", "recurrence_max_reps", "recurrence_start_date", "recurrence_end_date"]:
            if col in update_data and update_data[col] is not None:
                tx_fields.append(f"{col} = %s")
                tx_params.append(update_data[col])
        
        if tx_fields:
            tx_params.append(tx_id)
            query = f"UPDATE transactions SET {', '.join(tx_fields)} WHERE id = %s;"
            cur.execute(query, tx_params)
        
        # 3. Actualizar datos en third_parties si corresponde
        tp_fields = []
        tp_params = []
        if "third_party_name" in update_data and update_data["third_party_name"] is not None:
            tp_fields.append("name = %s")
            tp_params.append(update_data["third_party_name"])
        if "identification_number" in update_data and update_data["identification_number"] is not None:
            tp_fields.append("identification_number = %s")
            tp_params.append(update_data["identification_number"])
            
        if tp_fields:
            tp_params.append(third_party_id)
            query = f"UPDATE third_parties SET {', '.join(tp_fields)} WHERE id = %s;"
            cur.execute(query, tp_params)
        
        # Recalcular saldos de cuentas
        recalcular_saldos_cuentas(conn)
        
        conn.commit()
        cur.close()
        conn.close()
        return True
    except Exception as e:
        print(f"🔌 [MODO SIMULACIÓN] Actualizando transacción local en memoria ID {tx_id}")
        for tx in MOCK_TRANSACTIONS:
            if tx.get("id") == tx_id:
                for k, v in update_data.items():
                    if v is not None:
                        # Mapeo de campos del driver de Postgres a Mock
                        if k == "third_party_name":
                            tx["third_party_name"] = v
                        else:
                            tx[k] = v
                recalcular_saldos_cuentas()
                save_mock_db()
                return True
        raise e


def recalcular_saldos_cuentas(conn=None):
    """
    Recalcula el saldo actual (current_balance) de todas las cuentas a partir
    del saldo inicial y todas las transacciones registradas.
    Soporta multi-moneda (COP/USD) y TRM manual para conversiones.
    """
    global IS_POSTGRES_ACTIVE
    if not IS_POSTGRES_ACTIVE:
        for acc in MOCK_USER_ACCOUNTS:
            acc["current_balance"] = acc["initial_balance"]
        
        for tx in MOCK_TRANSACTIONS:
            tx_type = tx.get("type", "").upper()
            acc_id = tx.get("account_id")
            dest_id = tx.get("dest_account_id")
            trm = float(tx.get("trm") or 1.0)
            tx_curr = tx.get("transaction_currency", "COP")
            net_val = float(tx.get("net_value") or 0.0)
            amount = float(tx.get("amount") or 0.0)
            
            acc_obj = next((a for a in MOCK_USER_ACCOUNTS if a["id"] == acc_id), None)
            dest_obj = next((a for a in MOCK_USER_ACCOUNTS if a["id"] == dest_id), None)
            
            if tx_type == "INGRESO" and acc_obj:
                val_in_acc = net_val
                acc_curr = acc_obj["currency"]
                if tx_curr != acc_curr:
                    if tx_curr == "USD" and acc_curr == "COP":
                        val_in_acc = net_val * trm
                    elif tx_curr == "COP" and acc_curr == "USD":
                        val_in_acc = net_val / trm if trm > 0 else 0.0
                acc_obj["current_balance"] += val_in_acc
                
            elif tx_type == "GASTO" and acc_obj:
                val_in_acc = net_val
                acc_curr = acc_obj["currency"]
                if tx_curr != acc_curr:
                    if tx_curr == "USD" and acc_curr == "COP":
                        val_in_acc = net_val * trm
                    elif tx_curr == "COP" and acc_curr == "USD":
                        val_in_acc = net_val / trm if trm > 0 else 0.0
                acc_obj["current_balance"] -= val_in_acc
                
            elif tx_type == "TRANSFERENCIA" and acc_obj:
                acc_curr = acc_obj["currency"]
                acc_obj["current_balance"] -= amount
                
                if dest_obj:
                    dest_curr = dest_obj["currency"]
                    val_in_dest = amount
                    if acc_curr != dest_curr:
                        if acc_curr == "USD" and dest_curr == "COP":
                            val_in_dest = amount * trm
                        elif acc_curr == "COP" and dest_curr == "USD":
                            val_in_dest = amount / trm if trm > 0 else 0.0
                    dest_obj["current_balance"] += val_in_dest
        return

    close_conn = False
    if conn is None:
        try:
            conn = get_db_connection()
            close_conn = True
        except Exception:
            return
        
    try:
        cur = conn.cursor()
        cur.execute("SELECT id, currency, initial_balance FROM user_accounts;")
        accounts = {row[0]: {"currency": row[1], "initial_balance": float(row[2]), "current_balance": float(row[2])} for row in cur.fetchall()}
        
        cur.execute("""
            SELECT type, account_id, dest_account_id, trm, transaction_currency, net_value, amount 
            FROM transactions 
            ORDER BY transaction_date ASC, id ASC;
        """)
        txs = cur.fetchall()
        
        for row in txs:
            tx_type, acc_id, dest_id, trm, tx_curr, net_val, amount = row
            trm = float(trm or 1.0)
            net_val = float(net_val or 0.0)
            amount = float(amount or 0.0)
            
            if tx_type == "INGRESO" and acc_id in accounts:
                acc_obj = accounts[acc_id]
                val_in_acc = net_val
                acc_curr = acc_obj["currency"]
                if tx_curr != acc_curr:
                    if tx_curr == "USD" and acc_curr == "COP":
                        val_in_acc = net_val * trm
                    elif tx_curr == "COP" and acc_curr == "USD":
                        val_in_acc = net_val / trm if trm > 0 else 0.0
                acc_obj["current_balance"] += val_in_acc
                
            elif tx_type == "GASTO" and acc_id in accounts:
                acc_obj = accounts[acc_id]
                val_in_acc = net_val
                acc_curr = acc_obj["currency"]
                if tx_curr != acc_curr:
                    if tx_curr == "USD" and acc_curr == "COP":
                        val_in_acc = net_val * trm
                    elif tx_curr == "COP" and acc_curr == "USD":
                        val_in_acc = net_val / trm if trm > 0 else 0.0
                acc_obj["current_balance"] -= val_in_acc
                
            elif tx_type == "TRANSFERENCIA" and acc_id in accounts:
                acc_obj = accounts[acc_id]
                acc_curr = acc_obj["currency"]
                acc_obj["current_balance"] -= amount
                
                if dest_id in accounts:
                    dest_obj = accounts[dest_id]
                    dest_curr = dest_obj["currency"]
                    val_in_dest = amount
                    if acc_curr != dest_curr:
                        if acc_curr == "USD" and dest_curr == "COP":
                            val_in_dest = amount * trm
                        elif acc_curr == "COP" and dest_curr == "USD":
                            val_in_dest = amount / trm if trm > 0 else 0.0
                    dest_obj["current_balance"] += val_in_dest
                    
        for acc_id, acc_data in accounts.items():
            cur.execute("""
                UPDATE user_accounts 
                SET current_balance = %s 
                WHERE id = %s;
            """, (acc_data["current_balance"], acc_id))
            
        conn.commit()
        cur.close()
    except Exception as e:
        print(f"Error al recalcular saldos en BD: {e}")
        if conn:
            conn.rollback()
    finally:
        if close_conn:
            conn.close()


def obtener_perfil_usuario() -> Dict[str, Any]:
    global IS_POSTGRES_ACTIVE
    if not IS_POSTGRES_ACTIVE:
        return MOCK_USER_PROFILE
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("SELECT name, email, role, avatar_style FROM user_profiles ORDER BY id ASC LIMIT 1;")
        row = cur.fetchone()
        cur.close()
        conn.close()
        if row:
            return dict(row)
        return MOCK_USER_PROFILE
    except Exception:
        return MOCK_USER_PROFILE


def actualizar_perfil_usuario(data: Dict[str, Any]) -> bool:
    global IS_POSTGRES_ACTIVE
    if not IS_POSTGRES_ACTIVE:
        for k, v in data.items():
            if k in MOCK_USER_PROFILE:
                MOCK_USER_PROFILE[k] = v
        save_mock_db()
        return True
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("""
            UPDATE user_profiles 
            SET name = %s, email = %s, role = %s, avatar_style = %s 
            WHERE id = (SELECT id FROM user_profiles ORDER BY id ASC LIMIT 1);
        """, (data.get("name"), data.get("email"), data.get("role"), data.get("avatar_style")))
        conn.commit()
        cur.close()
        conn.close()
        return True
    except Exception as e:
        print(f"Error al actualizar perfil en BD: {e}")
        return False


def obtener_cuentas() -> List[Dict[str, Any]]:
    global IS_POSTGRES_ACTIVE
    if not IS_POSTGRES_ACTIVE:
        return MOCK_USER_ACCOUNTS
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("SELECT id, name, type, currency, initial_balance, current_balance FROM user_accounts ORDER BY id ASC;")
        rows = cur.fetchall()
        cur.close()
        conn.close()
        return [dict(r) for r in rows]
    except Exception:
        return MOCK_USER_ACCOUNTS


def crear_cuenta(data: Dict[str, Any]) -> int:
    global IS_POSTGRES_ACTIVE
    if not IS_POSTGRES_ACTIVE:
        new_id = max([a["id"] for a in MOCK_USER_ACCOUNTS], default=0) + 1
        new_acc = {
            "id": new_id,
            "name": data["name"],
            "type": data["type"],
            "currency": data.get("currency", "COP"),
            "initial_balance": float(data.get("initial_balance", 0.0)),
            "current_balance": float(data.get("initial_balance", 0.0))
        }
        MOCK_USER_ACCOUNTS.append(new_acc)
        recalcular_saldos_cuentas()
        save_mock_db()
        return new_id
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO user_accounts (name, type, currency, initial_balance, current_balance)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id;
        """, (data["name"], data["type"], data.get("currency", "COP"), float(data.get("initial_balance", 0.0)), float(data.get("initial_balance", 0.0))))
        new_id = cur.fetchone()[0]
        conn.commit()
        cur.close()
        conn.close()
        recalcular_saldos_cuentas()
        return new_id
    except Exception as e:
        print(f"Error al crear cuenta: {e}")
        raise e


def reset_db() -> bool:
    """
    Elimina todas las transacciones, terceros, pockets y cuentas por cobrar/pagar.
    Reinicia los balances de las cuentas a sus valores iniciales.
    Si se está usando PostgreSQL, realiza un TRUNCATE en cascada y vuelve a semillar.
    Si se está usando el modo simulación, vacía las listas en memoria.
    """
    global IS_POSTGRES_ACTIVE, MOCK_TRANSACTIONS, MOCK_USER_ACCOUNTS, MOCK_USER_PROFILE
    
    # 1. Resetear datos locales de simulación
    MOCK_TRANSACTIONS.clear()
    MOCK_USER_PROFILE.clear()
    MOCK_USER_PROFILE.update({
        "name": "Andrés",
        "email": "andres@finsys.os",
        "role": "Administrador Contable",
        "avatar_style": "pixel-grid"
    })
    # Resetear cuentas por defecto
    MOCK_USER_ACCOUNTS.clear()
    MOCK_USER_ACCOUNTS.extend([
        {"id": 1, "name": "Efectivo", "type": "Efectivo", "currency": "COP", "initial_balance": 50000.0, "current_balance": 50000.0},
        {"id": 2, "name": "Bancolombia Ahorros", "type": "Ahorros", "currency": "COP", "initial_balance": 1500000.0, "current_balance": 1500000.0},
        {"id": 3, "name": "Nequi", "type": "Billetera", "currency": "COP", "initial_balance": 200000.0, "current_balance": 200000.0},
        {"id": 4, "name": "Davivienda Crédito", "type": "Crédito", "currency": "COP", "initial_balance": 0.0, "current_balance": -500000.0},
        {"id": 5, "name": "Binance USDT", "type": "Crypto", "currency": "USD", "initial_balance": 100.0, "current_balance": 100.0}
    ])
    
    if not IS_POSTGRES_ACTIVE:
        print("🔌 [MODO SIMULACIÓN] Base de datos en memoria reiniciada a sus valores por defecto.")
        save_mock_db()
        return True

    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Eliminar registros de todas las tablas en orden de dependencias y reiniciar llaves primarias
        cur.execute("TRUNCATE cxp_cxc_ledger RESTART IDENTITY CASCADE;")
        cur.execute("TRUNCATE assets RESTART IDENTITY CASCADE;")
        cur.execute("TRUNCATE transactions RESTART IDENTITY CASCADE;")
        cur.execute("TRUNCATE pockets RESTART IDENTITY CASCADE;")
        cur.execute("TRUNCATE third_parties RESTART IDENTITY CASCADE;")
        cur.execute("TRUNCATE user_accounts RESTART IDENTITY CASCADE;")
        cur.execute("TRUNCATE user_profiles RESTART IDENTITY CASCADE;")

        
        # Volver a semillar los datos iniciales
        cur.execute("""
        INSERT INTO user_profiles (name, email, role, avatar_style)
        VALUES ('Andrés', 'andres@finsys.os', 'Administrador Contable', 'pixel-grid');
        """)
        
        default_accounts = [
            ('Efectivo', 'Efectivo', 'COP', 50000.0, 50000.0),
            ('Bancolombia Ahorros', 'Ahorros', 'COP', 1500000.0, 1500000.0),
            ('Nequi', 'Billetera', 'COP', 200000.0, 200000.0),
            ('Davivienda Crédito', 'Crédito', 'COP', 0.0, -500000.0),
            ('Binance USDT', 'Crypto', 'USD', 100.0, 100.0)
        ]
        for name, type_val, curr, init, curr_bal in default_accounts:
            cur.execute("""
            INSERT INTO user_accounts (name, type, currency, initial_balance, current_balance)
            VALUES (%s, %s, %s, %s, %s);
            """, (name, type_val, curr, init, curr_bal))
            
        conn.commit()
        cur.close()
        conn.close()
        print("✅ Base de datos PostgreSQL reiniciada y semillada a sus valores iniciales.")
        return True
    except Exception as e:
        print(f"Error al resetear base de datos PostgreSQL: {e}")
        if 'conn' in locals() and conn:
            conn.rollback()
        return False


# ==============================================================================
# LÓGICA DEL CATÁLOGO DE CUENTAS (COA)
# ==============================================================================
def obtener_coa_tree(portfolio_name: str) -> List[Dict[str, Any]]:
    """Obtiene el árbol de cuentas de un portafolio"""
    global IS_POSTGRES_ACTIVE
    if not IS_POSTGRES_ACTIVE:
        return [] # Simulación no implementada para COA en memoria en esta versión base

    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("SELECT id FROM portfolios WHERE name = %s", (portfolio_name,))
        res = cur.fetchone()
        if not res:
            return []
        portfolio_id = res['id']

        cur.execute("SELECT id, code, name, account_type, parent_id, is_group, description FROM chart_of_accounts WHERE portfolio_id = %s ORDER BY code", (portfolio_id,))
        accounts = cur.fetchall()
        
        # Build tree
        acc_dict = {a["id"]: {**a, "children": []} for a in accounts}
        tree = []
        for acc_id, node in acc_dict.items():
            parent_id = node.get("parent_id")
            if parent_id and parent_id in acc_dict:
                acc_dict[parent_id]["children"].append(node)
            else:
                tree.append(node)
                
        return tree
    except Exception as e:
        print(f"Error obteniendo COA: {e}")
        return []

def cargar_plantilla_coa(portfolio_name: str, template_name: str = "ESTANDAR"):
    """Carga una plantilla en la base de datos para el portafolio"""
    from coa_test_module import COA_TEMPLATES
    
    global IS_POSTGRES_ACTIVE
    if not IS_POSTGRES_ACTIVE:
        return False
        
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT id FROM portfolios WHERE name = %s", (portfolio_name,))
        res = cur.fetchone()
        if not res:
            return False
        portfolio_id = res[0]

        # Insertar Estándar como base
        for acc in COA_TEMPLATES["ESTANDAR"]:
            _insertar_cuenta_coa(cur, portfolio_id, acc)
            
        if template_name != "ESTANDAR" and template_name in COA_TEMPLATES:
            for acc in COA_TEMPLATES[template_name]:
                _insertar_cuenta_coa(cur, portfolio_id, acc)

        conn.commit()
        return True
    except Exception as e:
        print(f"Error cargando plantilla COA: {e}")
        if 'conn' in locals() and conn:
            conn.rollback()
        return False

def _insertar_cuenta_coa(cur, portfolio_id, acc):
    # Buscar parent_id
    parent_id = None
    if acc.get("parent_code"):
        cur.execute("SELECT id FROM chart_of_accounts WHERE portfolio_id = %s AND code = %s", (portfolio_id, acc["parent_code"]))
        pres = cur.fetchone()
        if pres:
            parent_id = pres[0]

    cur.execute("""
        INSERT INTO chart_of_accounts (portfolio_id, code, name, account_type, is_group, parent_id)
        VALUES (%s, %s, %s, %s, %s, %s)
        ON CONFLICT (portfolio_id, code) DO NOTHING;
    """, (portfolio_id, acc["code"], acc["name"], acc.get("type", acc.get("account_type")), acc["is_group"], parent_id))

def agregar_cuenta_coa(portfolio_name: str, account_data: Dict[str, Any]):
    """Agrega una sola cuenta personalizada al COA"""
    global IS_POSTGRES_ACTIVE
    if not IS_POSTGRES_ACTIVE:
        return False
        
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT id FROM portfolios WHERE name = %s", (portfolio_name,))
        res = cur.fetchone()
        if not res:
            return False
        portfolio_id = res[0]

        _insertar_cuenta_coa(cur, portfolio_id, account_data)
        conn.commit()
        return True
    except Exception as e:
        print(f"Error agregando cuenta al COA: {e}")
        if 'conn' in locals() and conn:
            conn.rollback()
        return False

def obtener_portafolios() -> List[Dict[str, Any]]:
    global IS_POSTGRES_ACTIVE, MOCK_PORTFOLIOS
    if not IS_POSTGRES_ACTIVE:
        return MOCK_PORTFOLIOS
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("SELECT id, name, industry_type, sub_industry_type FROM portfolios ORDER BY id ASC;")
        rows = cur.fetchall()
        cur.close()
        conn.close()
        return [dict(r) for r in rows]
    except Exception as e:
        print(f"Error obteniendo portafolios: {e}")
        return []

def crear_portafolio(name: str, industry_type: str = "ESTANDAR", sub_industry_type: str = "") -> Optional[int]:
    global IS_POSTGRES_ACTIVE, MOCK_PORTFOLIOS
    if not IS_POSTGRES_ACTIVE:
        new_id = len(MOCK_PORTFOLIOS) + 1
        MOCK_PORTFOLIOS.append({
            "id": new_id,
            "name": name,
            "industry_type": industry_type,
            "sub_industry_type": sub_industry_type
        })
        save_mock_db()
        return new_id
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("INSERT INTO portfolios (name, industry_type, sub_industry_type) VALUES (%s, %s, %s) RETURNING id;", (name, industry_type, sub_industry_type))
        new_id = cur.fetchone()[0]
        conn.commit()
        cur.close()
        conn.close()
        # Inicializar el COA correspondiente
        cargar_plantilla_coa(name, industry_type)
        return new_id
    except Exception as e:
        print(f"Error al crear portafolio: {e}")
        return None


def obtener_terceros():
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("SELECT id, identification_type, identification_number, name, email, phone, website FROM third_parties ORDER BY name ASC;")
        rows = cur.fetchall()
        cur.close()
        conn.close()
        return [dict(r) for r in rows]
    except Exception as e:
        print(f"Error obteniendo terceros: {e}")
        # Simulacion mock
        mock_terceros = []
        for tx in MOCK_TRANSACTIONS:
            if "third_party_name" in tx:
                mock_terceros.append({
                    "id": len(mock_terceros) + 1,
                    "identification_type": "NIT",
                    "identification_number": tx.get("identification_number", "0"),
                    "name": tx.get("third_party_name", "Desconocido")
                })
        return mock_terceros

