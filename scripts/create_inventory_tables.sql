-- ══════════════════════════════════════════════════════════════════
--  FIN-SYS OS — Módulo Inventario: Tablas y índices
--  Ejecutar una sola vez contra Supabase PostgreSQL
-- ══════════════════════════════════════════════════════════════════

-- inventory_items: Catálogo de productos/artículos
CREATE TABLE IF NOT EXISTS inventory_items (
  id SERIAL PRIMARY KEY,
  portfolio_name TEXT NOT NULL,
  company_id INTEGER REFERENCES entities(id),
  name TEXT NOT NULL,
  sku TEXT,
  category TEXT DEFAULT 'General',
  unit TEXT DEFAULT 'unidad',
  cost_price NUMERIC(15,2) DEFAULT 0,
  sell_price NUMERIC(15,2) DEFAULT 0,
  current_stock INTEGER DEFAULT 0,
  min_stock INTEGER DEFAULT 0,
  status TEXT DEFAULT 'ACTIVO',
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- inventory_movements: Registro de entradas/salidas
CREATE TABLE IF NOT EXISTS inventory_movements (
  id SERIAL PRIMARY KEY,
  item_id INTEGER NOT NULL REFERENCES inventory_items(id),
  type TEXT NOT NULL CHECK (type IN ('ENTRADA', 'SALIDA', 'AJUSTE')),
  quantity INTEGER NOT NULL,
  unit_price NUMERIC(15,2),
  total NUMERIC(15,2),
  reference TEXT,
  transaction_id INTEGER REFERENCES transactions(id),
  third_party_id INTEGER,
  notes TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Índices para consultas frecuentes
CREATE INDEX IF NOT EXISTS idx_inventory_items_company ON inventory_items(company_id);
CREATE INDEX IF NOT EXISTS idx_inventory_items_portfolio ON inventory_items(portfolio_name);
CREATE INDEX IF NOT EXISTS idx_inventory_movements_item ON inventory_movements(item_id);
