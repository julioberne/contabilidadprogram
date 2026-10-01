# Frente: panel-contexto-crud
Estado: ACTIVO · Actualizado: 2026-10-01 16:00 · Rama/commit: claude/eager-mcnulty-92ede8 @ a4b18d9 (= origin/master 3bd3cd5 + 5 commits)

## Objetivo
Que los botones ✎/🗑 del panel de contexto de Contabilidad (👤 Terceros, 🏷️ Tags, 📈 Tasas) hagan lo que dicen y que ningún fallo se trague en silencio. Termina cuando el código esté en producción y Andrés haya borrado con el 🗑 el tercero #34 «TERCERO PRUEBA MODAL» y las etiquetas basura (`dfghj`, `nm`, `bnm,`).

## Estado actual
- Hecho (30-sep): `DELETE /api/third-parties/{id}` (admin) en `routers/cartera.py` + regla en `fin_sys_core/terceros_borrado.py`; `ContextPanel.deleteItem` muestra el `detail` del servidor en un aviso fijo bajo las pestañas. La otra sesión lo integró en master (hoy es `e205146`, antes `cc9ed85`).
- Hecho (1-oct, `a4b18d9`): `PUT/DELETE /api/tags/{id}` y `PUT/DELETE /api/custom-taxes/{id}` en `routers/tags_taxes.py`; lógica de etiquetas en `fin_sys_core/etiquetas.py`; `updateItem` avisa y cierra la fila solo con OK; `ImpuestosTab` con fila de edición real; `EtiquetasTab` con segunda confirmación.
- En producción: **no** (nada de este frente está desplegado).
- Pendiente de push/deploy: toda la rama (5 commits: specs 09.I ×2, Terceros, Mini App 09.I v1, Tags/Tasas). Andrés ya hizo `git pull --rebase origin master` en el worktree → la rama es `origin/master` + 5, el push es fast-forward.

## Próximo paso (concreto)
1. Andrés: `git push origin claude/eager-mcnulty-92ede8:master`.
2. Agente: `scratch/deploy_prod.py` (vive en el checkout principal) → sondas sin token: `DELETE /api/third-parties/0` → 401 (código viejo: 405), `DELETE /api/tags/0` → 401 (viejo: 405), `/api/health` → `db: connected`.
3. Checkout principal: su `master` (`6518318`) quedó con copias viejas de 4 commits → `git -C <main> pull --rebase origin master` cuando la sesión 09.I no tenga cambios sin commit; luego `npm run build` ahí (`localhost:8000` sirve `dist` congelado).
4. Andrés en la web: 👤 Terceros → 🗑 del #34; 🏷️ Tags → 🗑 de `dfghj`, `nm` y `bnm,` (esta última está en 1 TX: pedirá la segunda confirmación). Si todo responde, frente CERRADO + línea en CHECKLIST.
5. Pendiente menor (requiere su autorización, endpoint existente): `POST /api/custom-taxes` lee `tax_type` pero la web manda `type` → toda plantilla nace ADDITIVE (una línea en `routers/tags_taxes.py`).

## Decisiones tomadas (y por qué)
- Tercero con historia (TX, cartera, inventario, borradores abiertos del bot) → 409 con conteo; nada se reasigna ni se deja en NULL: `transactions.third_party_id` y `cxp_cxc_ledger.third_party_id` son NOT NULL + ON DELETE RESTRICT (Regla 5). Andrés rechazó "pasar la historia a Sin especificar". Genérico `999999999` intocable.
- `database_driver.eliminar_tercero` / `actualizar_tag` / `eliminar_tag` quedan sin usar (la primera ponía FKs NOT NULL en NULL); `database_driver.py` no se toca (🔴). Deuda: retirarlas en limpieza técnica.
- Etiqueta en uso → 409 con conteo y **segunda confirmación** en la web que repite con `?forzar=1` (la quita de `transactions.tags` y de los borradores abiertos). **Renombrar NO propaga**: las TX conservan el nombre viejo (decisión de Andrés, 1-oct).
- Plantillas de impuesto: nadie las referencia → PUT/DELETE directos vía driver con validación (422/400/404).
- El DELETE de terceros vive en `routers/cartera.py` junto al POST/PUT existentes para no tocar `server.py`.

## Archivos clave
- `fin_sys_core/terceros_borrado.py` (`eliminar`, `uso_de_tercero`, `describir_uso`) · `routers/cartera.py:439` (DELETE)
- `fin_sys_core/etiquetas.py` (`actualizar`, `eliminar(forzar)`) · `routers/tags_taxes.py` (+4 rutas, `_con_transaccion`, `_validar_impuesto`)
- `frontend/src/contabilidad-v2/components/ContextPanel.jsx:92` (`deleteItem` con `{confirmarReintento, reintentarCon}`, `updateItem`, aviso `panelError`) · `tabs/EtiquetasTab.jsx` · `tabs/ImpuestosTab.jsx`
- Tests: `tests/test_terceros_borrado(.py|_db.py)`, `tests/test_etiquetas(.py|_db.py)`, `frontend/src/contabilidad-v2/components/ContextPanel.test.jsx`
- Docs: `docs/api_spec.md` §7 y §9 · `docs/checkpoints.md` «Checkpoint 2026-09-30 (b)» · `CHECKLIST.md` pendiente «El 🗑 de la tabla de Terceros»

## Cómo verificar
- Puros (lista de `.github/workflows/ci.yml`, incluye `test_terceros_borrado` y `test_etiquetas`): 282 OK. Con BD (crean filas con sufijo único y las borran; los casos con TX en rollback): `.venv\Scripts\python.exe -m unittest tests.test_terceros_borrado_db tests.test_etiquetas_db` → 10 OK.
- Frontend: `npx vitest run` (89) y `npm run build` en `frontend/`.
- Prod tras el deploy: sondas del paso 2 y el flujo del paso 4.

## Bloqueos y riesgos
- `master` del checkout principal divergido de origin (paso 3); la sesión 09.I trabaja ahí con cambios sin commit: no rebasar su checkout sin avisarle.
- `deleteItem`/`updateItem` son compartidos por Terceros, Tags, Tasas y Recursos: un cambio ahí afecta a los cuatro.
- Sobra el worktree `affectionate-mestorf-f204bc` (chip arrancado y abandonado); lo quita Andrés (`git worktree remove`, bloqueado al agente).
