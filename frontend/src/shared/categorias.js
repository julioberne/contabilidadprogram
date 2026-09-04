/* ============================================================
   categorias.js — Categorías operativas por tipo de registro.
   Los MISMOS nombres de las posting_rules del kernel (seed_puc.py):
   así cada registro matchea su regla contable y asienta en la
   cuenta PUC correcta sin que el usuario toque el COA.
   Vive en shared/ para que Contabilidad y la bandeja del Bot la
   compartan SIN importarse entre sí (rompía el code-splitting:
   el ciclo ContabilidadApp ↔ BotDraftsPanel fusionaba chunks).
   ============================================================ */
export const CATEGORIAS = {
  INGRESO: ['Ventas', 'Servicios Prestados', 'Intereses', 'Otros Ingresos'],
  GASTO: ['Alimentación', 'Transporte', 'Servicios', 'Suscripciones', 'Infraestructura',
          'Publicidad', 'Papelería', 'Gastos Bancarios', 'Nómina', 'Otros Gastos'],
  TRANSFERENCIA: ['Transferencia'],
};
