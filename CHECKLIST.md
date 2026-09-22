# CHECKLIST — FIN-SYS OS v2.0

> **Único archivo de estado vivo.** Aquí: qué hay, qué falta, cómo arrancar.
> Lo que ya pasó (con verificación) va a `docs/checkpoints.md` — un checkpoint por sesión.
> Última actualización: **15 Sep 2026**.

---

## 1. Estado actual

| Dónde | Estado |
|---|---|
| rama `claude/intelligent-ellis-79a132` (worktree) | **Análisis Inteligente hito 2 (B1) SIN push** (21-sep): insights automáticos (`insight_engine.py` + tarjetas en la Home) · resumen periódico por Telegram (tick en el poller, `ANALYTICS_RESUMEN_HORAS`, default 24h) · pestaña 🗒 BITÁCORA en el módulo · métrica 9 `conteo_terceros` (nacida de la bitácora). Verificado e2e en :8000 contra Supabase real. Push: `git push origin claude/intelligent-ellis-79a132:master` → deploy `scratch/deploy_prod.py` |
| `origin/master` = producción :8080 | desplegado y verificado 15 sep (`b4e7379`): cimientos (un solo pool, dashboard 1 viaje, TX+asiento atómicos, contra-asiento, auth en GETs) + módulo 12 Contadores. Deploy: `scratch/deploy_prod.py` (agente, tras cada push); push: Andrés |
| BD Supabase | compartida local↔prod · **reiniciada con `feat(reset)`: 0 TXs** · 6 entidades CT (2 vinculadas) · 5 cuentas · 4 portafolios · patrimonio $1.000.000 (verificado 26 ago) |

### Módulos

| # | Módulo | Estado | Ruta |
|---|---|---|---|
| 01–06 | Contabilidad (unificado) | ✅ COMPLETO | `frontend/src/contabilidad-v2/` |
| 07 | Control Tower | ✅ COMPLETO | `frontend/src/control-tower/` |
| 08 / 08c | Project Hub · RRHH/Empresas | ✅ EN USO | `frontend/src/project-hub/` |
| — | Zero-COA Kernel | ✅ Fase 1+2 | `kernel/` |
| 09 | Bot IA (Telegram + Groq) | ✅ Etapas A–E en producción · 🔵 **09.F SMS Bancolombia → borradores** en curso (22-sep) · 09.G completar tercero/concepto · 09.H OCR — specs en `docs/specs/09-bot-ia/` | `fin_sys_core/bot_*.py`, `fin_sys_core/sms_bancolombia.py`, `routers/bot.py`, `routers/webhooks_sms.py` |
| 10 | Trading NASDAQ | 🔵 PLANIFICADO | — |
| 11 | Reportes PDF/Excel · Facturación B2B | 🔵 PLANIFICADO | — |
| 12 | Contadores (bandeja de asientos BORRADOR→CONTABILIZADO, diario, plan de cuentas, reglas, reportes, cierres) | ✅ v1 (15-sep) — rol `contador` | `frontend/src/contadores/`, `routers/contadores.py`, `kernel/kernel_journal_workflow.py`, `kernel/kernel_periods.py`, `kernel/kernel_reports.py`, `fin_sys_core/coa_admin_driver.py` |
| 13 | Análisis Inteligente (catálogo de 9 métricas whitelisted · explorador Perspective WASM · preguntas en español con sello de origen y gráfica matplotlib · insights automáticos en la Home · resumen por Telegram · bitácora de preguntas 30 días) | ✅ hito 1 web (15-sep) · ✅ hito 2 insights+Telegram (21-sep) · hito 3: bot pregunta/foto | `fin_sys_core/metrics_catalog.py`, `fin_sys_core/analytics_qa.py`, `fin_sys_core/insight_engine.py`, `routers/analytics.py`, `frontend/src/analisis/` |

---

## 2. Pendientes abiertos

### Deuda técnica

| ID | Problema | Prioridad |
|---|---|---|
| DT-01 | Balance Efectivo -$11.2M (TXs legacy sin `account_id`) | Media |
| DT-03 | CT: CXP/CXC en KPIs parcial | Media |
| DT-06 | Bundle ~1.7MB sin code splitting (meta: chunk principal <500KB) | Media |
| DT-07 | Fuentes Kanban/TaskModal (CSS classes sin aplicar) | Baja |
| DT-08 | Integración contabilidad↔nómina (totalizar gasto nómina en COA) | Media |
| DT-09 | Comprobante nómina: integrar con tablas contables al generarse | Baja |
| DT-10 | Webhook GitHub→Dokploy confirmado MUERTO por 4ª vez (push `21c4bb3` del 02 sep no disparó nada en 2+ min). Tras cada push: `scratch/deploy_prod.py` (el agente tiene permiso para correrlo — vía operativa estándar) | Baja |
| DT-11 | Fase 5 remediación: print→logging, TRM 4000 hardcodeada, float→Decimal (lifespan ✅ hecho 26 ago) | Media |
| DT-15 | Renombrar `contabilidad-v2/` → `contabilidad/` (parar el watcher de Vite antes: lock en Windows) | Baja |
| DT-16 | Rotar el GitHub PAT del provider de Dokploy (expuesto en una sesión) | Media |
| DT-17 | Rama por defecto de GitHub sigue en `main` (vacía) — cambiarla a `master` en Settings | Media |
| DT-18 | Queda 1 worktree obsoleto (`admin-dashboard-user-credentials-2aab9b`) + 2 ramas muertas del commit raíz huérfano. Comandos listos en checkpoint 26 ago (el clasificador los bloquea al agente) | Baja |
| DT-20 | Voz web (`.webm`) no queda adjunta como evidencia; la de Telegram (`.ogg`) sí. ¿Deliberado? | Baja |
| DT-29 | Evidencias → Supabase Storage (08-sep): las NUEVAS (web ✅ y bot ✅ 09-sep — fotos y voz) van a `hr-docs/evidence/` (URL pública en BD, un solo mundo local↔prod). Lista blanca del bucket ampliada 09-sep: webp/gif/ogg/webm/mp3 ✅. **Queda solo (a)**: 7 notas de voz `.ogg` viejas de TXs del bot viven SOLO en el volumen de prod — correr `scripts/migrate_evidence_to_storage.py` DENTRO del contenedor prod (best-effort, idempotente; el bucket ya acepta audio). Pillow solo para conversiones del script (`uv pip install pillow`) | Baja |
| ~~DT-22~~ | **CERRADA 02 sep** — pooler en transaction mode `6543` en local Y en Dokploy (verificado por API) + redeploy hecho. NUNCA volver a 5432 | ✅ |
| DT-21 | Endpoints huérfanos (stubs `NOT_IMPLEMENTED` en `routers/hr.py`): `POST /api/hr/storage/sign-upload`, `POST /api/hr/salary/calculate` — remover o activar con DT-09 | Baja |
| DT-23 | Fugas de conexión "solo en except" (~40 funciones patrón release-en-try): `control_tower_driver` (16 fn, además responden MOCK silencioso al fallar), `database_driver` (~20 fn), `inventory_driver`, `org_driver`. Las fugas 100% y las estructurales YA corregidas 04-sep | Media |
| ~~DT-24~~ | ✅ CERRADA 15-sep: `_get_conn` de `hr_documents_driver` presta del pool y lo devuelve (antes abría conexiones directas y NUNCA las cerraba) | — |
| ~~DT-25~~ | ✅ CERRADA 04-sep: el arranque ABORTA si Postgres no responde (FINSYS_ALLOW_MOCK=1 solo dev) | — |
| ~~DT-26~~ | ✅ CERRADA 04-sep: el arranque ABORTA si DB_PORT falta o es 5432 (FINSYS_ALLOW_5432=1 override) | — |
| ~~DT-27~~ | ✅ CERRADA 15-sep: `/api/dashboard-data` y `/api/accounts` en UN viaje (`fin_sys_core/dashboard_query.py`, paridad 0 diffs con `scripts/verify_dashboard_parity.py`); 2.1 s → 0.28 s local. `DASHBOARD_FAST=0` en Dokploy = ruta legacy sin redeploy. Además el bloque COA consultaba `coa_accounts` (inexistente) y FUGABA una conexión por request (pool muerto a los ~8 dashboards) — corregido | — |
| DT-30 | El COA sembrado (23 cuentas de plantilla, códigos cortos) NO contiene los códigos PUC de 6 dígitos que usan las posting_rules (522005, 513520, 130505…); `scripts/seed_puc.py` se salta si el portafolio ya tiene cuentas. El contador puede crearlas en Contadores → Plan de cuentas, o adaptar el seed para insertar solo las faltantes | Media |
| DT-31 | Recurrencia: `is_recurring/recurrence_*` se guardan pero NINGÚN proceso materializa las ocurrencias (no hay scheduler) | Media |
| ~~DT-32~~ | ✅ CERRADA 15-sep: la Home usa `/api/dashboard-data/balance` (consolidado, misma matemática del dashboard) y `GET /api/hr/employees/summary` ya existe (daba 404 en cada carga). `/api/portfolios/balance` sigue existiendo para otros consumidores | — |
| DT-33 | GETs de `hub/*`, `hr/*` y `tags/*` siguen sin `require_auth` (los de dinero ya exigen sesión desde 15-sep) | Media |
| DT-34 | Registrar una TX sigue costando 8-12 sentencias en serie (~0.4 s en prod). Opcionales pendientes del plan A3: `_asegurar_tercero` en una sentencia con CTEs y `aplicar_delta_incremental` con un solo UPDATE | Baja |
| ~~DT-28~~ | ✅ CERRADA 07-sep (autorizada por Andrés): 18 fallbacks mock gateados con `mock_policy.mock_permitido()` (org ×5, database ×6, inventory ×7) — fallo de BD ⇒ error visible; mock SOLO con `FINSYS_ALLOW_MOCK=1`. El modo simulación explícito (`IS_POSTGRES_ACTIVE=False`) se conserva. UI: chip rojo "⚠ SIN CONEXIÓN BD" en el consolidado + reintento 30s. Tests en CI (`test_mock_policy`). **Resto**: `control_tower_driver` aún tiene MOCK_ENTITIES en su except (16 fn, Zero-Impact CT) — misma receta cuando se toque | — |

- [x] **Failover automático de canal de BD** ✅ IMPLEMENTADO Y DESPLEGADO 09-sep (probado bajo recaída real): si :6543 no fluye, db_pool cae solo a :5432 con pools mínimos y el vigía regresa al sanar (2 aciertos/45s). Regla del puente manual (si algún día vuelve): NO usar scratch/deploy_prod.py mientras esté activo (su guard-rail revierte DB_PORT). Respaldo completo de la BD en backups/ (gitignored)
- **DT-30** ✅ CERRADA 11-sep (mismo día): el pool se CONTAMINABA — hub_driver/pooled_connection pegaban `cursor_factory=RealDictCursor` a la conexión y la devolvían así; el siguiente caller recibía dicts donde esperaba tuplas (`row[0]` → KeyError '0'; mató el primer eliminar-con-clave y explicaba 500s intermitentes tras usar RRHH). Cura central en db_pool: personalidad neutra al prestar Y devolver + test de regresión
- [ ] **DT-31 — Endpoints de escritura SIN auth** (hallado 11-sep): ✅ CÓDIGO LISTO en `7c7d91c` (integra la rama `seguridad/auth-guards-endpoints` de la sesión paralela + guards en los 2 endpoints nuevos del día; 74 unittest + 51 vitest + build en verde). **Falta SOLO push + deploy, y hay que hacerlo CON Andrés presente**: cambia el contrato de toda la API mutadora (Bearer obligatorio; el frontend lo inyecta con installAuthFetch) — verificar en vivo login → registrar → editar comprobante → bandeja bot tras desplegar. Los GET siguen abiertos a propósito (siguiente fase). El bot NO usa la API HTTP (escribe vía fin_sys_core) — no le afecta
- [ ] **PRIMERO LA PRÓXIMA SESIÓN — Descuadre cuenta 2 "Bancolombia Ahorros 3037 julian"**: current_balance = $101.170.000 pero inicial ($0) + TXs reales = $1.170.000 → **$100M fantasma**. Forense 11-sep: el respaldo del 09-sep YA mostraba $99.77M sin ninguna TX ≥$50M — es herencia vieja (¿TX borrada por el `feat(reset)`? ¿saldo puesto a mano?), NO lo causó el 🗑 (las otras 5 cuentas cuadran a $0.00 exacto, reversa verificada). DECISIÓN DE ANDRÉS: (A) si el banco real tiene ~$101M → poner initial_balance=100.000.000 y reconciliar; (B) si el saldo real es $1.17M → correr la reconciliación directa (`POST /api/reconcile-balances`, admin; recalcula desde inicial+TXs). Query de medición en el checkpoint 11-sep

### Funcional / calidad

- [ ] **TC022** — Libro Diario sin buscador (brecha de spec TestSprite; decidir si se agrega)
- [ ] **TestSprite**: re-correr sobre el build actual y avanzar TC031–TC050 (última corrida 29 jul: 25/30 ✅)
- [ ] **Bot IA**: ✅ funcionando en producción (gpt-oss-120b) · Etapa C COMPLETA (bandeja web) · **Etapa E COMPLETA 08-sep** (fotos→Storage, botones inline, `/empresa`, rechazo de grupos; verificada EN VIVO por Andrés — evidencia adjunta al #51) · **Etapa E.2 08-sep**: 🏷️ botón Etiquetas (toggle contra `tag_definitions`, fuente de verdad del módulo web), 💤 Dejar en borrador, 📍 ubicación de Telegram → geo_maps_link del borrador/TX, botonera regresa tras adjuntar evidencia, y FIX: la confirmación del bot ahora SÍ pasa tags+geo a la transacción (antes se perdían). E2E driver draft 58 · **Etapa E.3 08-sep**: MÚLTIPLES evidencias por transacción (bot: replies acumulan en `transaction_drafts.media_paths`; web: input multiple; tabla `transaction_evidences` al confirmar, `evidence_file_path` sigue = principal; visor con galería N archivos incl. PDF/audio), tercero COMPLETO dictado por voz (LLM extrae phone/email/address, upsert con COALESCE que rellena sin destruir), labels 📍/📎N en la bandeja. E2E driver draft 70 (2 fotos + PDF + tel/dirección). Quedan B.5 (RAG) y D/F
- [ ] **Cartera Fase 2**: recordatorios personalizables por Telegram (tick en el poller, `cartera_reminders`, resumen periódico) — el diseño está en el checkpoint 03-sep
- [x] **Pipeline de etiquetas** ✅ CERRADO 08-sep: `transactions.tags TEXT[]` (migrate_transaction_tags.py, aplicada), TransactionInput.tags, INSERT/SELECT, transaction_service; chips en fila expandida del Libro Diario (ya existían) + sección 🏷️ en el comprobante. Verificado e2e (TX 14). El bot las guarda cuando se editan en la bandeja
- [x] **Eliminar transacciones** ✅ CERRADO 11-sep: 🗑 en la fila expandida del Libro Diario → DELETE /api/transactions/{id} con la clave del admin/owner re-verificada en CADA intento (bcrypt vía hub_users) + reversa contable completa (revierte saldos, borra cartera asociada y evidencias). Las TXs de prueba #13/#14 ya tienen salida. También 11-sep: terceros sin duplicados (buscador en formulario + `_asegurar_tercero`: reutiliza por nombre o crea con número provisional SN-; el genérico 999999999 jamás se renombra), 📎 adjuntar evidencias a TX existente, campo dirección del tercero
- [ ] **Limpieza de datos por Andrés**: borrar tercero "TERCERO PRUEBA MODAL" (id 34, 🗑 del panel Terceros) · SQL del zombie "MI EMPRESA" (id 3) en Supabase · bot de DESARROLLO en @BotFather (token compartido sigue siendo mina)
- [ ] **Portafolios**: la columna de vínculos se retiró del consolidado (02 sep) — reubicar con mejor funcionamiento. 07-sep: "Finanzas Personales Julian" YA reclama el portafolio 1 "Negocio A" (sus gastos reales viven ahí). Fase pendiente: portafolio propio por empresa + renombrar "Negocio A" (hardcodeado como default en ~10 sitios — no renombrar sin migrarlos)
- [ ] **Borrar portafolio zombie "MI EMPRESA" (id 3)**: cero referencias auditadas en todas las FKs; el clasificador bloquea el DELETE al agente. SQL para Andrés (editor SQL de Supabase): `DELETE FROM portfolios WHERE id = 3 AND name = 'MI EMPRESA';`
- [ ] **NumInput en Control Tower** (`CTSidePanel`, `CTApprovalsCenter`): esperando aprobación Zero-Impact de Andrés
- [ ] Andrés dejó un "punto 2" sin terminar en el chat del 02 sep — preguntarle qué era
- [ ] Módulo 10 Trading (cuando Andrés lo priorice)

---

## 3. Arranque rápido

```powershell
# Backend (raíz del proyecto — SIEMPRE el venv, no el python global)
.venv\Scripts\python.exe server.py

# Frontend (desde frontend/)
npm run dev -- --port 5173

# Salud completa (7 checks)
python scripts/health_check.py
```

- Si `:8000` está ocupado → hay uvicorn huérfano: `Get-NetTCPConnection -LocalPort 8000 | Select OwningProcess` y matar ese PID.
- Con Claude Code: `preview_start` con la config `finsys-backend` (`.claude/launch.json`).

### Local al día con producción (regla del 11-sep)

`localhost:8000` sirve `frontend/dist`, un build CONGELADO: no cambia solo con el
código (ese día "los cambios no se veían" y RRHH pedía chunks ya inexistentes).
Producción sí se reconstruye en cada deploy. Para cerrar la brecha en un paso:

```powershell
.venv\Scripts\python.exe scripts\sync_local.py   # pull --ff-only + npm run build
```

y luego `Ctrl+Shift+R` en la pestaña (suelta la caché). Señal típica de build
viejo: error "Failed to fetch dynamically imported module" al abrir un módulo.
El agente corre esto (o su equivalente) tras cada deploy; este botón es para
cuando Andrés lo necesite por su cuenta. `localhost:5173` (vite dev) no sufre
esto — siempre sirve el código vivo.

### Verificación mínima antes de dar algo por bueno

```powershell
python -m kernel.test_kernel                                                   # 6/6 partida doble (+ anulación espejo)
python tests/test_core.py                                                      # 5/5 motor matemático
python -m unittest tests.test_single_module_identity tests.test_tx_atomica tests.test_dashboard_snapshot tests.test_db_pool_fallback   # un solo pool, TX+asiento atómicos, snapshot
python -m unittest tests.test_bot_driver tests.test_bot_confirmation tests.test_bot_resolvers
python -m unittest tests.test_sms_bancolombia tests.test_bot_sms tests.test_webhooks_sms tests.test_bot_sms_db tests.test_bot_retencion   # 09.F SMS Bancolombia: parser, mapeo por id, webhook, tick (BD) y retención 30/60/90 (BD)
python -m unittest tests.test_analytics_catalog tests.test_analytics_qa tests.test_insight_engine   # 55/55 Análisis: catálogo + traductor (LLM mockeado) + gráfica + insights/tick Telegram
python tests/test_contadores.py                                                # 15/15 módulo Contadores (BD real, limpia sus filas)
python scripts/verify_dashboard_parity.py                                      # 0 diffs legacy vs rápido
python tests/test_e2e.py                                                       # ⚠️ crea y BORRA una TX real — FINSYS_BASE=http://127.0.0.1:8001 y FINSYS_ADMIN_PASSWORD=... para probar el borrado por API
cd frontend; npx vitest run; npm run build                                     # 56 tests y build de producción
# /api/health ahora expone "pool": used/free/fallback — used debe volver a 0 en reposo; log "[req] METHOD ruta status ms" por request
```

- `GET http://127.0.0.1:8000/docs` responde · `GET /api/org/consolidated` → 200 (si 404, backend viejo)
- Ojo: la BD es **compartida con producción** — un borrado local borra en prod.

---

## 4. Referencia (accesos y deploy)

- **Login shell y Control Tower**: `andres@finsys.os` / `admin123` (las cuentas `@finsys.io` no existen; doc que las mencione está obsoleto). Otras: `and123@gmail.com`, `testuser@finsys.os` (member).
- **Supabase**: proyecto `sciorfjvdqxvcwgvnmbv` (us-east-2) · bucket `hr-docs` (público).
- **Producción**: http://159.223.156.50:8080 · Panel Dokploy :3000 · compose único `finsys-app`.
- **Deploy** = push de Andrés → el agente corre `scratch/deploy_prod.py` (el webhook está MUERTO, DT-10) → verifica contenedores/health → sincroniza `master` local y el build de `:8000`. Push clásico: `git push origin master` desde la carpeta principal; si la sesión de Claude trabaja en un worktree con rama propia, el botón es `git push origin <rama>:master` (mismo efecto: directo a master, un clic).
- **Workspace Hub**: Inversiones FIN-SYS (`37888f92-8bef-4528-b187-2064c6f0049c`).

### Zero-Impact Policy (regla de oro)

Funcionalidad nueva = archivos nuevos. **Prohibido sin aprobación explícita**:
`fin_sys_core/database_driver.py` · `fin_sys_core/control_tower_driver.py` ·
`frontend/src/control-tower/*` · `.env` · alterar schema de tablas existentes.

### Cierre de sesión (obligatorio)

1. Agregar checkpoint a `docs/checkpoints.md` (qué se hizo, cómo se verificó).
2. Actualizar **este archivo**: tabla de estado, pendientes cerrados/nuevos.
3. Nada más — los demás .md no se tocan por rutina (los históricos viven en `docs/archive/`).
