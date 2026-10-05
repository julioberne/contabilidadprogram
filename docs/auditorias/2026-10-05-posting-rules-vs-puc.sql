-- =====================================================================
-- posting_rules → PUC (Decreto 2650/1993) · PROPUESTA del 05-oct-2026
-- Informe: docs/auditorias/2026-10-05-posting-rules-vs-puc.md
--
-- NO EJECUTADO. Solo con aprobación de Andrés (idealmente con el contador).
-- Dónde: Supabase → SQL Editor. La BD es la MISMA en local y en producción.
-- Efecto: solo asientos FUTUROS (la caché de reglas expira en 60 s).
-- No toca asientos existentes, ni el esquema, ni chart_of_accounts.
-- Cada UPDATE exige el valor viejo: si la regla ya cambió, no hace nada.
-- =====================================================================


-- ── PASO 0 · Foto previa (solo lectura). Guarda el resultado. ─────────
SELECT id, rule_name, category, transaction_type,
       debit_account_code, credit_account_code, is_active
  FROM posting_rules ORDER BY id;


-- ── PASO 1 · Cambios (todo o nada) ───────────────────────────────────
BEGIN;

-- Gastos: cambia el DÉBITO
UPDATE posting_rules SET debit_account_code = '519595' WHERE id = 10 AND debit_account_code = '519515'; -- Otros Gastos: Música ambiental → Diversos-Otros
UPDATE posting_rules SET debit_account_code = '519595' WHERE id = 19 AND debit_account_code = '5105';   -- Fallback gasto: Gastos de personal → Diversos-Otros
UPDATE posting_rules SET debit_account_code = '519560' WHERE id = 3  AND debit_account_code = '519525'; -- Alimentación: Aseo y cafetería → Casino y restaurante
UPDATE posting_rules SET debit_account_code = '512010' WHERE id = 4  AND debit_account_code = '522005'; -- Infraestructura: Arrend. ventas-Terrenos → Arrend. admón-Construcciones
UPDATE posting_rules SET debit_account_code = '513595', rule_name = 'Servicios Generales'
                                                       WHERE id = 1  AND debit_account_code = '513520'; -- Servicios: Proc. electrónico de datos → Servicios-Otros (y deja de llamarse igual que id 22)
UPDATE posting_rules SET debit_account_code = '513595' WHERE id = 22 AND debit_account_code = '513525'; -- Servicios Públicos: Acueducto → Servicios-Otros
UPDATE posting_rules SET debit_account_code = '513520' WHERE id = 2  AND debit_account_code = '513535'; -- Suscripciones: Teléfono → Proc. electrónico de datos
UPDATE posting_rules SET debit_account_code = '519545' WHERE id = 5  AND debit_account_code = '513530'; -- Transporte: Energía eléctrica → Taxis y buses
UPDATE posting_rules SET debit_account_code = '523560' WHERE id = 6  AND debit_account_code = '519530'; -- Publicidad: Útiles y papelería → Publicidad, propaganda y promoción
UPDATE posting_rules SET debit_account_code = '519530' WHERE id = 7  AND debit_account_code = '519520'; -- Papelería: Gastos de representación → Útiles, papelería y fotocopias
UPDATE posting_rules SET debit_account_code = '530505' WHERE id = 8  AND debit_account_code = '519505'; -- Gastos Bancarios: Comisiones (admón) → Gastos bancarios (financieros)

-- Ingresos: cambia el CRÉDITO
UPDATE posting_rules SET credit_account_code = '413595' WHERE id = 11 AND credit_account_code = '413505'; -- Ventas: código inexistente → Venta de otros productos
UPDATE posting_rules SET credit_account_code = '413595' WHERE id = 21 AND credit_account_code = '413505'; -- Venta de Productos (duplicado)
UPDATE posting_rules SET credit_account_code = '415550' WHERE id = 12 AND credit_account_code = '417505'; -- Servicios Prestados: Devoluciones en ventas → Consultoría
UPDATE posting_rules SET credit_account_code = '415550' WHERE id = 20 AND credit_account_code = '417505'; -- Servicios Profesionales (duplicado)
UPDATE posting_rules SET credit_account_code = '429595' WHERE id = 18 AND credit_account_code = '417505'; -- Fallback ingreso: Devoluciones en ventas → Diversos-Otros (no operacional)

-- Reglas nuevas para categorías que hoy caen al fallback
INSERT INTO posting_rules (rule_name, category, transaction_type, debit_account_code, credit_account_code, description, portfolio_id, is_active)
VALUES ('Otros Ingresos',      'Otros Ingresos', 'INGRESO', '__BANK__', '429595', 'Ingresos no operacionales diversos', NULL, TRUE),
       ('Servicios (ingreso)', 'Servicios',      'INGRESO', '__BANK__', '415550', 'Categoría "Servicios" de la plantilla estándar', NULL, TRUE)
ON CONFLICT DO NOTHING;

-- PENDIENTES DE DECISIÓN DEL CONTADOR (no se ejecutan; quitar el "--" si se aprueban):
-- UPDATE posting_rules SET credit_account_code = '413595' WHERE id = 14 AND credit_account_code = '413505'; -- Crear CXC: ¿qué ingreso es la venta de lotes?
-- Crear CXP (id 15): el débito depende de lo comprado → requiere "tipo de CXP" (código), no un UPDATE.

COMMIT;   -- Si algo falla, Postgres revierte todo el bloque.


-- ── PASO 2 · Verificación (solo lectura) ─────────────────────────────
-- Esperado: 24 reglas (16 con código nuevo + 2 nuevas) y viejas_que_quedan = 1
-- (la 14 "Crear CXC", que sigue en 413505 hasta que decida el contador).
SELECT id, rule_name, category, transaction_type, debit_account_code, credit_account_code
  FROM posting_rules ORDER BY id;
SELECT COUNT(*) AS viejas_que_quedan FROM posting_rules
 WHERE is_active AND (debit_account_code IN ('519515','5105','519525','522005','513525','513535','513530','519520','519505')
                   OR credit_account_code IN ('417505','413505'));


-- ── ROLLBACK (solo si hay que deshacer el PASO 1) ────────────────────
-- BEGIN;
-- UPDATE posting_rules SET debit_account_code = '519515' WHERE id = 10 AND debit_account_code = '519595';
-- UPDATE posting_rules SET debit_account_code = '5105'   WHERE id = 19 AND debit_account_code = '519595';
-- UPDATE posting_rules SET debit_account_code = '519525' WHERE id = 3  AND debit_account_code = '519560';
-- UPDATE posting_rules SET debit_account_code = '522005' WHERE id = 4  AND debit_account_code = '512010';
-- UPDATE posting_rules SET debit_account_code = '513520', rule_name = 'Servicios Públicos' WHERE id = 1 AND debit_account_code = '513595';
-- UPDATE posting_rules SET debit_account_code = '513525' WHERE id = 22 AND debit_account_code = '513595';
-- UPDATE posting_rules SET debit_account_code = '513535' WHERE id = 2  AND debit_account_code = '513520';
-- UPDATE posting_rules SET debit_account_code = '513530' WHERE id = 5  AND debit_account_code = '519545';
-- UPDATE posting_rules SET debit_account_code = '519530' WHERE id = 6  AND debit_account_code = '523560';
-- UPDATE posting_rules SET debit_account_code = '519520' WHERE id = 7  AND debit_account_code = '519530';
-- UPDATE posting_rules SET debit_account_code = '519505' WHERE id = 8  AND debit_account_code = '530505';
-- UPDATE posting_rules SET credit_account_code = '413505' WHERE id IN (11, 21) AND credit_account_code = '413595';
-- UPDATE posting_rules SET credit_account_code = '417505' WHERE id IN (12, 20) AND credit_account_code = '415550';
-- UPDATE posting_rules SET credit_account_code = '417505' WHERE id = 18 AND credit_account_code = '429595';
-- DELETE FROM posting_rules WHERE portfolio_id IS NULL AND transaction_type = 'INGRESO'
--    AND ((category = 'Otros Ingresos' AND credit_account_code = '429595')
--      OR (category = 'Servicios'      AND credit_account_code = '415550'));
-- COMMIT;
