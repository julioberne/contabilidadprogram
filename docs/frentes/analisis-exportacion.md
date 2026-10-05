# Frente: analisis-exportacion
Estado: BLOQUEADO (espera aprobación del plan) · Actualizado: 2026-10-05 · Rama/commit: claude/project-status-review-5e1694 @ (este commit, sobre origin/master aa99293)

## Objetivo
Cerrar el último escalón del plan "Mejor que Excel" (B5): exportar los libros del contador a .xlsx real desde un submódulo desplegable 📦 EXPORTACIÓN dentro de ∑ Análisis — armado selectivo + 🗂 ARCHIVO tipo drive + 🗓 calendario de cierres. Termina cuando 13.4 y 13.5 están HECHOS y desplegados.

## Estado actual
- Hecho: specs escritos — `docs/specs/13-analisis/SPEC.md` (módulo), `13.4-export-xlsx.md` v1.1 (motor), `13.5-submodulo-exportacion.md` (interfaz + archivo). Cero código.
- En producción: no (hitos 1–3 del módulo sí, desde 16 y 22-sep).
- Pendiente de push: este commit de docs.

## Próximo paso (concreto, ejecutable sin releer todo)
1. Andrés responde las 4 decisiones de §10 del spec 13.5 (almacenamiento bytea vs bucket privado; retención 90 días + fijados; quién ve el archivo; NIT desde Control Tower).
2. Con la aprobación: implementar en el orden de §9 de 13.5 — primero 13.4 motor (`fin_sys_core/export_xlsx.py`, `openpyxl==3.1.5` en requirements y en el `.venv`, `GET /api/analytics/export.xlsx`, `tests/test_export_xlsx.py`), verificable con curl.

## Decisiones tomadas (y por qué)
- openpyxl en el backend: el npm `xlsx` está congelado con CVEs; la verdad vive en Python; openpyxl escribe y lee (vista previa del archivo y tests).
- El motor no inventa cifras: viste `kernel_reports` (mayor, balance de prueba, ER, BG) + `kernel_journal_entries` + `obtener_transacciones`.
- Propuesto (sin aprobar): archivos en Postgres `bytea` — el bucket `hr-docs` es PÚBLICO y la llave de Storage es la anónima.
- La parte Excel del módulo 11 la absorbe 13.5.

## Archivos clave
- `kernel/kernel_reports.py` (libro_mayor :34, balance_prueba :75, estado_resultados :157, balance_general :167)
- `routers/analytics.py` (agregar endpoints) · `frontend/src/analisis/AnalisisApp.jsx` (montar el panel, 1 línea)
- `frontend/src/shell/useRoute.js:60` conserva subrutas → `/analisis/archivo` funciona

## Cómo verificar
- Motor: `curl.exe -H "Authorization: Bearer <token>" -o libro.xlsx "http://127.0.0.1:<puerto>/api/analytics/export.xlsx?desde=2026-09-01&hasta=2026-09-30"`
- Puertos 8000/8001/8002 los usan otras sesiones: servidor de verificación con `autoPort`.

## Bloqueos y riesgos
- Bloqueo: aprobación de Andrés (protocolo de AGENTS.md).
- Riesgo: `master` local de otra sesión lleva 2 commits de docs sin push (b44deb8, db4facc) que también tocan CHECKLIST.md → al integrarse, posible conflicto menor en CHECKLIST (filas distintas).
- DT-30: cuentas sin código PUC → el Mayor/Balances las mostraría sin código; la carátula lo advierte.
