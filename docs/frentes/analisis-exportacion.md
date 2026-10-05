# Frente: analisis-exportacion
Estado: ACTIVO · Actualizado: 2026-10-05 · Rama/commit: claude/project-status-review-5e1694 (sobre origin/master aa99293)

## Objetivo
Cerrar el último escalón del plan "Mejor que Excel" (B5): los libros del contador en .xlsx real (13.4, motor) y el
submódulo desplegable 📦 EXPORTACIÓN dentro de ∑ Análisis (13.5): organizador contable con el patrón del de RRHH +
exportación por período o por transacciones seleccionadas (también desde el Libro Diario). Termina con 13.4 y 13.5
HECHOS y desplegados.

## Estado actual
- 13.4 motor IMPLEMENTADO y verificado en local contra la BD real (05-oct): `fin_sys_core/export_xlsx.py` +
  `GET /api/analytics/export.xlsx` (owner/admin/contador). 36 unit + 3 integración + e2e HTTP.
- 13.5: spec v1.1 APROBADO (las 5 decisiones de §10 con las recomendaciones). Sin código.
- En producción: no (prod hoy responde 404 en la ruta nueva).
- Pendiente de push: el commit del motor + el de docs.

## Próximo paso (concreto, ejecutable sin releer todo)
1. Andrés: `git push origin claude/project-status-review-5e1694:master` → yo: `scratch/deploy_prod.py` → sonda
   `GET /api/analytics/export.xlsx` sin token = 401 (antes 404) → Andrés abre un libro en Excel (CA-134-01).
2. 13.5-a backend del organizador: `scripts/migrate_exports.py` (4 tablas `accounting_*` + paquetes, idempotente,
   ANTES del deploy), `fin_sys_core/accounting_files_driver.py`, `routers/accounting_files.py` + include_router.

## Decisiones tomadas (y por qué)
- openpyxl en backend (npm `xlsx` congelado con CVEs). El motor no calcula: viste kernel_reports + diario + TXs.
- Filtros finos solo en hojas de transacciones; los libros oficiales nunca se filtran (D-134-07).
- Mayor = saldo anterior del balance + líneas del diario, sin una consulta por cuenta (D-134-08).
- Nombres de cuenta: plan de cuentas de la empresa > PUC estándar > nombre del asiento (D-134-09). La lista PUC
  vive en `shared/puc_estandar.py` (scripts/ no viaja en la imagen); `seed_puc.py` la importa.
- 13.5: archivos en Postgres bytea (bucket `hr-docs` es PÚBLICO); mismo patrón UX que RRHH pero código propio.

## Archivos clave
- `fin_sys_core/export_xlsx.py` (normalizar_receta → recolectar → construir_libro → armar_libro)
- `routers/analytics.py` (export_xlsx al final) · `shared/puc_estandar.py` · `tests/test_export_xlsx*.py`
- Para 13.5: `frontend/src/analisis/AnalisisApp.jsx`, `frontend/src/contabilidad-v2/modules/diario/LibroDiario.jsx`
  (clic de fila expande, doble clic edita: la casilla no debe disparar ninguno), patrón a imitar (NO importar):
  `frontend/src/project-hub/features/members/tabs/DocumentsTab.jsx` + `docs/`

## Cómo verificar
- `python -m unittest tests.test_export_xlsx` (36) · `tests.test_export_xlsx_db` (3, necesita .env)
- Worktree sin .env: lanzador de solo lectura del .env principal (ver checkpoint 2026-10-05) y servidor con autoPort.

## Bloqueos y riesgos
- Hallazgo contable abierto: reglas que mandan categorías a cuentas PUC de otro significado (519515, 513520,
  417505) — ahora visible en los libros; tarea aparte.
- master local de otra sesión tiene 2 commits de docs sin push (b44deb8, db4facc) que tocan CHECKLIST/checkpoints:
  al integrarse, conflicto menor posible (secciones distintas).
