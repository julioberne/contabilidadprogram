# 🗄️ Guía de Conexión y Troubleshooting de Base de Datos — FIN-SYS OS v2.0

> **Última actualización**: 09 Junio 2026
> **Motor**: PostgreSQL 17 en Supabase · **Proyecto**: `FIN-SYS OS v2.0` (sciorfjvdqxvcwgvnmbv) · **Región**: us-east-2

---

## 1. Configuración de Conexión

Las credenciales se cargan desde `.env` en la raíz del proyecto. El driver `database_driver.py` usa `psycopg2`.

```env
DB_HOST=aws-0-us-east-2.pooler.supabase.com
DB_PORT=5432
DB_NAME=postgres
DB_USER=postgres.sciorfjvdqxvcwgvnmbv
DB_PASSWORD=<contraseña real en .env local>
```

**Verificación rápida**:
```bash
python scripts/health_check.py
# ✅ [3/5] PostgreSQL (Supabase) → Conectado | TXs: 18 | Entidades: 7
```

---

## 2. Mecanismo de Fallback en Memoria

Si la conexión a Supabase falla, el sistema activa automáticamente el **Modo Simulación** usando datos en memoria (`mock_db.json`).

- La variable `IS_POSTGRES_ACTIVE` en `database_driver.py` indica el modo activo.
- En los logs del servidor se puede ver: `⚠️ Modo Simulación Activo` o `✅ PostgreSQL Conectado`
- **Riesgo**: Si la escritura falla silenciosamente y cae al mock, las transacciones parecen no guardarse porque el frontend sigue leyendo de Supabase.

---

## 3. IDs de Cuentas — Estado Actual en Supabase

> ⚠️ **Importante**: Los IDs de cuentas en Supabase son fijos y no deben cambiar. El frontend los usa directamente.

| ID | Nombre | Tipo | Moneda | Balance Inicial |
|---|---|---|---|---|
| 1 | Efectivo | Efectivo | COP | $50.000 |
| 2 | Bancolombia Ahorros | Ahorros | COP | $1.500.000 |
| 3 | Nequi | Billetera | COP | $200.000 |
| 4 | Davivienda Crédito | Crédito | COP | -$500.000 |
| 5 | Binance USDT | Crypto | USD | $100 |
| 6 | Efectivo USD | Efectivo | USD | $50 |
| 7 | Bancolombia Corriente | Corriente | COP | $3.000.000 |

**Portafolios activos**:
| ID | Nombre |
|---|---|
| 1 | Negocio A |
| 2 | EMPRESA INFANTIL PEGASUS |
| 3 | Personal |
| 4 | Negocio Principal |

---

## 4. Troubleshooting: Transacciones que No Aparecen

### Síntoma: Registro exitoso en UI pero no aparece en Libro Diario

**Causa más común**: Desincronización de `account_id` — el frontend envía un ID que no existe en Supabase (error FK silencioso → fallback al mock).

**Diagnóstico**:
```bash
# En Supabase MCP o SQL Editor:
SELECT id, name FROM user_accounts ORDER BY id;
SELECT COUNT(*) FROM transactions WHERE account_id IS NULL;
```

**Solución A (desde el frontend)**:
1. Buscar botón **`⚠️ Reiniciar`** en la barra superior de la app
2. Click → llama a `/reset_db` → TRUNCATE CASCADE + re-seed de cuentas con IDs 1–5

**Solución B (SQL manual en Supabase)**:
```sql
-- Paso 1: Limpiar en cascada
TRUNCATE cxp_cxc_ledger RESTART IDENTITY CASCADE;
TRUNCATE transactions RESTART IDENTITY CASCADE;
TRUNCATE user_accounts RESTART IDENTITY CASCADE;
TRUNCATE user_profiles RESTART IDENTITY CASCADE;

-- Paso 2: Re-seed de cuentas con IDs fijos
INSERT INTO user_accounts (id, name, type, currency, initial_balance, current_balance) VALUES
  (1, 'Efectivo', 'Efectivo', 'COP', 50000.0, 50000.0),
  (2, 'Bancolombia Ahorros', 'Ahorros', 'COP', 1500000.0, 1500000.0),
  (3, 'Nequi', 'Billetera', 'COP', 200000.0, 200000.0),
  (4, 'Davivienda Crédito', 'Crédito', 'COP', 0.0, -500000.0),
  (5, 'Binance USDT', 'Crypto', 'USD', 100.0, 100.0);

-- Paso 3: Fijar secuencia para que las nuevas cuentas empiecen en ID 6
SELECT setval('user_accounts_id_seq', 7);
```

> **Nota**: No truncar `entities`, `workspace_users`, `resource_ids`, `approvals_queue` ni `entity_members` — son datos del Control Tower que deben preservarse.

---

## 5. Troubleshooting: Balance Efectivo Negativo (-$11.2M)

**Causa**: Transacciones legacy registradas antes de que el campo `account_id` fuera obligatorio. Están vinculadas a un portafolio pero no a ninguna cuenta, lo que distorsiona el cálculo de saldo de Efectivo.

**Diagnóstico**:
```sql
SELECT COUNT(*) FROM transactions WHERE account_id IS NULL;
-- Resultado esperado: ~15 transacciones legacy
```

**Fix pendiente (deuda técnica)**:
```sql
-- Asignar las TXs de COP sin cuenta a "Efectivo" (id=1)
UPDATE transactions
SET account_id = 1
WHERE account_id IS NULL AND transaction_currency = 'COP';

-- Asignar las TXs de USD sin cuenta a "Binance USDT" (id=5)
UPDATE transactions
SET account_id = 5
WHERE account_id IS NULL AND transaction_currency = 'USD';

-- Recalcular balances
SELECT recalcular_saldos_cuentas();  -- función en database_driver.py
```

---

## 6. Acceso Directo al MCP de Supabase

Para consultas SQL directas sin abrir el panel web de Supabase, usar el MCP integrado con el agente:
- **Project ID**: `sciorfjvdqxvcwgvnmbv`
- Herramienta: `execute_sql` del servidor MCP `supabase`

```
Ejemplo: listar todas las entidades del CT
→ SELECT id, name, type, portfolio_id FROM entities ORDER BY id;
```

> **Restricción conocida**: No es posible conectar directo a Postgres desde scripts locales (psycopg2 desde PowerShell) sin el `.env` cargado correctamente. Usar siempre el MCP o el endpoint de la API para operaciones de BD desde el agente.
