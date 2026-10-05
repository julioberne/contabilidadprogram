# Frente: analisis-exportacion
Estado: ACTIVO · Actualizado: 2026-10-05 · Rama/commit: claude/project-status-review-5e1694 @ (este commit, sobre origin/master 01c5a36)

## Objetivo
Cerrar el último escalón del plan "Mejor que Excel" (B5): submódulo desplegable 📦 EXPORTACIÓN dentro de ∑ Análisis
(spec `docs/specs/13-analisis/13.5-submodulo-exportacion.md`, APROBADO 05-oct con las 5 decisiones de §10). Termina con
13.5 HECHO, desplegado y visto en el navegador.

## Estado actual
- 13.4 motor HECHO y EN PRODUCCIÓN (`bf03177`, 05-oct): `GET /api/analytics/export.xlsx` (owner/admin/contador) → 10 libros
  por período o relación de transacciones elegidas. Falta solo que Andrés abra un libro en Excel (CA-134-01).
- 13.5 SIN CÓDIGO. En la web NO hay nada nuevo todavía (Andrés lo preguntó: el submódulo aún no existe).
- Pendiente de push: el commit de docs de este cierre.

## Próximo paso (concreto) — 13.5-a backend del organizador (orden de §9 del spec)
1. `scripts/migrate_exports.py` (NUEVO, idempotente): tablas `accounting_files`, `accounting_folders`, `accounting_doc_types`
   (+ defaults: Libros, Estados financieros, Impuestos, Cartera, Bancos, Relaciones, Soportes), `analytics_export_paquetes`.
   Columnas exactas en §4.4. Archivos en `bytea` (D-135-01). Correrla ANTES del deploy (BD compartida local↔prod).
2. `fin_sys_core/accounting_files_driver.py` (NUEVO): archivar (folio `EXP-AAAA-NNNN` por secuencia, SHA-256, huella de datos
   §4.6), listar, ficha + vigencia, preview (openpyxl read_only), subir (tope 10 MB, MIME PDF/PNG/JPG/XLSX/CSV), purga 90 días
   en cada INSERT (no toca fijados ni subidos), carpetas y tipos.
3. `routers/accounting_files.py` (NUEVO) con los endpoints de §4.5 + `include_router` en `server.py` (junto a `server.py:116`).
   `POST /api/analytics/export` reutiliza `export_xlsx.armar_libro` y archiva.
4. Tests puros `tests/test_accounting_files.py` (FakeConn) + al CI. Luego 13.5-b (organizador web), c (nueva exportación +
   selección en el Libro Diario), d (vigencia + calendario de cierres), cada uno verificado en el navegador con capturas.

## Decisiones tomadas (y por qué)
- Archivos en Postgres bytea: el bucket `hr-docs` es PÚBLICO y el Storage usa la llave anónima.
- Retención 90 días para lo generado no fijado; fijados y subidos para siempre. Ver/generar: owner/admin/contador; borrar: admin.
- Organizador = MISMO patrón UX que el de RRHH pero código propio en `frontend/src/analisis/exportacion/` (RRHH es paleta oscura
  y su chunk tuvo un import circular; no importar sus componentes). Chunk perezoso, montado con 1 línea en AnalisisApp.
- Motor: filtros finos solo en hojas de transacciones (D-134-07); nombres de cuenta = plan de cuentas > PUC estándar
  (`shared/puc_estandar.py`, scripts/ no viaja en la imagen) > nombre del asiento (D-134-09).

## Archivos clave
- `fin_sys_core/export_xlsx.py:139` normalizar_receta · `:447` recolectar · `:1217` construir_libro · `:1363` armar_libro
- `routers/analytics.py:205` export_xlsx · `server.py:116` include_router(analytics)
- UI 13.5: `frontend/src/analisis/AnalisisApp.jsx:406` (explorador; el panel va debajo) · `LibroDiario.jsx:105-110` (clic de
  fila expande, doble clic edita: la casilla no debe disparar ninguno) · patrón a imitar:
  `frontend/src/project-hub/features/members/tabs/DocumentsTab.jsx:29` + `tabs/docs/` (FolderCard, FileCard, PreviewModal…)

## Cómo verificar
- `python -m unittest tests.test_export_xlsx` (36) · `tests.test_export_xlsx_db` (3, solo lectura, necesita .env)
- Worktree sin .venv/.env: usar el python del checkout principal y cargar su .env en solo lectura (lanzador propio en el
  scratchpad); servidor local con `cmd /c "cd /d <principal> && .venv\Scripts\python.exe …"` (sirve el código del principal).
- Prod: https://finsys-andres.duckdns.org — `GET /api/analytics/export.xlsx` sin sesión = 401.

## Bloqueos y riesgos
- La migración de 13.5 crea tablas en la BD de PRODUCCIÓN (compartida): pedir el OK de Andrés antes de correrla.
- Hallazgo contable abierto en otra sesión (task_eeafa2c5): reglas que mandan categorías a cuentas PUC de otro significado.
- `launch.json` del worktree tiene arreglos solo locales (rutas absolutas al checkout principal): no commitear.
