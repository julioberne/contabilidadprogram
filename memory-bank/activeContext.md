# Contexto Activo — FIN-SYS OS v2.0

> **ACTUALIZAR al inicio Y al final de cada sesión de trabajo con el AI.**
> Este archivo le dice al agente exactamente qué puede y no puede tocar HOY.

---

## Estado: 21 Ago 2026 — MÓDULO 09 EN MVP · MERGEADO A `master` · **FALTA EL PUSH**

**Fase actual**: los módulos 01–08c están en producción y el **Módulo 09 (Bot IA / Telegram)
está terminado a nivel MVP**, junto con el cierre del Módulo 01 (Registro completo) y el
consolidado real por empresa.

**Lo único que falta para que agosto llegue a producción**: un `git push origin master`.

| Dónde | Commit | Estado |
|---|---|---|
| `master` local | ver `git log -1` | ✅ todo agosto + WIP + docs + cherry-pick del package-lock |
| `origin/master` | `64badb6` (29 jul) | ⏳ **sin actualizar** — el push lo bloqueó el clasificador de permisos |
| Producción :8080 | `64badb6` | ⏳ sigue sirviendo el build del 29 jul |
| Working tree | limpio | — |

**El desarrollo continúa en `master`**: la rama `modulo-09-bot-ia` se eliminó tras el merge.

```powershell
git push origin master     # <- lo corre Andrés; dispara el webhook de Dokploy (ojo DT-10)
```

### Cerrado en la sesión del 21 ago

- **Desfase frontend↔backend resuelto** (`bc86acf`): `DashboardPanel.jsx` ya llamaba
  `GET /api/org/consolidated` y `ContextPanel.jsx` ya exponía `createItem`, pero el endpoint
  y el botón de `TercerosTab.jsx` seguían sin commitear. Desplegar así habría dado 404.
- **Vinculación entidad ↔ portafolio aplicada** (ver más abajo): el panel de empresas ya no
  muestra $0.
- **Datos `TS-TEST-*` eliminados** de la BD real, revirtiendo saldos con la función de la app.
- **`.gitignore` corregido**: el patrón de TestSprite usaba backslashes y no ignoraba nada.
  Ahora quedan fuera `tmp/` (API key en `config.json`), los `TC*.py` y `standard_prd.json`,
  que traen la contraseña del admin hardcodeada. Se versionan solo el reporte y el plan.

---

## Módulos Activos

| # | Módulo | Estado | Archivos clave |
|---|---|---|---|
| 01–06 | **Contabilidad (unificado)** | ✅ ACTIVO — Módulo 01 completado 10 ago (impuestos con autorización humana, secciones avanzadas) | `frontend/src/contabilidad-v2/` |
| 07 | Control Tower | ✅ COMPLETO | `control-tower/`, `control_tower_driver.py` |
| 08 | Project Hub | ✅ COMPLETO | `project-hub/`, `hub_driver.py` |
| 08c | RRHH / Empresas / Documentos / Historial | ✅ EN USO | `project-hub/features/members/`, `hr_driver.py` |
| — | Zero-COA Kernel | ✅ Fase 1+2 | `kernel/`, `routers/zero_coa.py` |
| 09 | **Bot IA (Telegram + Groq)** | 🟡 **MVP en rama, sin merge/deploy** | `bot_driver.py`, `bot_telegram.py`, `routers/bot.py`, `draft_builder.py`, `transaction_service.py` |
| 10 | Trading NASDAQ (PnL, velas, heatmap) | 🔵 PLANIFICADO | — |

### Módulo 09 — qué quedó construido (commits `591907b` → `f5559f7`)

- Borradores persistentes en BD + confirmación determinista (nada se contabiliza sin un sí explícito).
- `draft_builder.py` unifica **voz web ⇄ bot**: un solo camino para armar el borrador.
- Impuestos **solo con autorización humana** (nunca se infieren solos).
- Resolutores reales: portafolio del usuario, método de pago dicho por él, tipos UUID.
- `scripts/bot_link_code.py` (vincular chat↔usuario), `scripts/migrate_bot_tables.py`,
  `scripts/repair_missing_journal.py`.
- Tests: `tests/test_bot_driver.py`, `test_bot_confirmation.py`, `test_bot_resolvers.py`.

---

## Calidad — TestSprite (última corrida: 29 Jul 2026)

**30 de 50 casos ejecutados · ✅ 25 · ❌ 5 → 83.33%**. Reporte: `testsprite_tests/testsprite-mcp-test-report.md`.

| # | Hallazgo | Estado |
|---|---|---|
| 1 | Consolidado de empresas en $0 (TC003) | ✅ **Resuelto 21 ago** — vinculación aplicada (ver abajo) |
| 2 | "O crear nuevo" en Terceros no creaba nada (TC025) | ✅ Corregido y commiteado (`bc86acf`) |
| 3 | Cartera mostraba `$NaN` (TC021) | ✅ Corregido y commiteado (`bc86acf`) |
| 4 | KPIs de Control Tower "sin cargar" (TC019) | ❌ Falso positivo, descartado |
| 5 | Libro Diario sin buscador (TC022) | 🟡 Abierto — brecha de spec, decidir si se agrega |
| 6 | `module_flags` acumula filas duplicadas por toggle (no hace upsert) | 🟡 Abierto — cosmético de backend (DT-12) |
| 7 | Datos `TS-TEST-*` en la BD real (2 TX + 1 tarea) | ✅ **Eliminados 21 ago** con reversión de saldos |

### Vinculación entidad ↔ portafolio (decidida por Andrés, 21 ago)

| Entidad (Control Tower) | Portafolio (contabilidad) |
|---|---|
| Mi Holding Principal (1) | Negocio Principal (4) |
| GRUPO EMPRESARIAL PEGASUS SAS (14) | EMPRESA INFANTIL PEGASUS (2) |
| URBANIZACION BONAIRE (17) | Negocio A (1) — único con movimientos |
| CONSTRUCTORA BLU SAS (16) · PRESCOLAR PEGASUS SAS (15) · IMPORTEX AMARU (18) | **sin vincular a propósito** |
| — | MI EMPRESA (3) queda libre (portafolio vacío, sin dueño claro) |

Las no vinculadas muestran "sin vincular", **nunca $0** — un cero se leería como "esta empresa
no facturó". El holding agrega su subárbol sin contar dos veces el mismo portafolio.

---

## Deploy

- Producción: http://159.223.156.50:8080 · Panel Dokploy: :3000 · UN solo compose `finsys-app`.
- **Deploy = push a `master`** → webhook Dokploy. Ojo DT-10: el webhook ha fallado antes;
  respaldo manual `POST /api/compose.deploy` con la key de `scratch/dokploy.env`.
- Producción sirve `64badb6` (29 jul): **tres semanas de trabajo sin desplegar**.

---

## Estado de Salud del Sistema (health_check, 21 Ago 2026 — 16:57 COT)

```
❌ Frontend (React/Vite)     → :5173 y :5174 CAÍDOS
❌ Backend (FastAPI)          → :8000 CAÍDO
✅ PostgreSQL (Supabase)      → 11 TXs (tras borrar las TS-TEST) | 6 entidades CT (3 vinculadas) | 5 cuentas | 4 portafolios
✅ Motor Matemático            → IVA=19.000 | GMF=400
⚠️  Control Tower API           → OMITIDO (backend caído)
⚠️  Project Hub API             → OMITIDO (backend caído)
✅ Integridad de datos         → Sin anomalías
✅ Producción :8080            → responde 200 (build de 29 jul)
```

**Arrancar servicios (PowerShell):**

```powershell
python -m uvicorn server:app --host 127.0.0.1 --port 8000 --reload   # Terminal 1
cd frontend; npm run dev -- --port 5173                              # Terminal 2
python scripts/health_check.py                                       # Re-verificar
```

---

## Orden de Trabajo — Próxima Sesión

1. **`git push origin master`** (lo corre Andrés) y verificar que el webhook de Dokploy disparó;
   si no, deploy manual `POST /api/compose.deploy` (DT-10). Confirmar con
   `curl -sI http://159.223.156.50:8080/` que el build es nuevo, y que
   `GET /api/org/consolidated` responde en producción.
2. **Re-correr TestSprite** sobre el build con los fixes (y avanzar TC031–TC050).
3. Buscador del Libro Diario (TC022) · upsert de `module_flags` (DT-12).
4. Módulo 10 Trading · Fase 5 de remediación (DT-11).

✅ Hechos el 21 ago: commit del WIP · merge a `master` en local · vinculación
entidad↔portafolio · limpieza de los `TS-TEST-*`.

---

## Archivos Permitidos en Próxima Sesión

### Módulo 09 (Bot IA) — foco actual

```
fin_sys_core/bot_driver.py · bot_telegram.py · draft_builder.py · transaction_service.py
routers/bot.py
scripts/bot_link_code.py · migrate_bot_tables.py
tests/test_bot_*.py
```

### Contabilidad unificada

```
frontend/src/contabilidad-v2/**
frontend/src/registry/moduleRegistry.js       ← solo si se registra módulo nuevo
routers/org.py · routers/cartera.py · fin_sys_core/org_driver.py   ← WIP en curso
```

### RRHH (módulo 08c)

```
frontend/src/project-hub/features/members/**
fin_sys_core/hr_driver.py · hr_documents_driver.py    ← solo agregar
```

### Módulo 10 (Trading, si se arranca)

```
fin_sys_core/trading_driver.py            (NUEVO)
frontend/src/trading/TradingApp.jsx       (NUEVO)
frontend/src/registry/moduleRegistry.js   (entrada trading)
```

## Archivos PROHIBIDOS (Zero-Impact Policy)

```
frontend/src/control-tower/*            ← NO tocar
fin_sys_core/database_driver.py         ← NO tocar (aprobación explícita)
fin_sys_core/control_tower_driver.py    ← NO tocar (aprobación explícita)
.env                                    ← NUNCA tocar bajo ninguna circunstancia
Tablas de BD existentes                 ← NO alterar schema sin aprobación explícita
```

(`frontend/src/App.jsx` ya no existe: se eliminó en la unificación de contabilidad de julio.)

---

## Deuda Técnica Pendiente

| ID | Problema | Prioridad |
|---|---|---|
| DT-01 | Balance Efectivo -$11.2M (legacy sin account_id) | Media |
| DT-02 | `on_event` deprecation → migrar a `lifespan` FastAPI | Baja |
| DT-03 | CT: CXP/CXC en KPIs parcial | Media |
| ~~DT-04~~ | ~~MD5 en workspace_users → bcrypt~~ ✅ **RESUELTO 2026-07-26** | — |
| ~~DT-05~~ | ~~SHA-256 en hub_users → bcrypt~~ ✅ **RESUELTO 2026-07-26** | — |
| DT-06 | Bundle ~1.7MB sin code splitting | Media |
| DT-07 | Fuentes Kanban/TaskModal pendientes (CSS classes no aplicadas) | Baja |
| DT-08 | Integración contabilidad-nómina (totalizar gasto nómina en CoA) | Media |
| DT-09 | Comprobante nómina: integrar con tablas contables al generarse | Baja |
| DT-10 | Webhook GitHub→Dokploy poco confiable: el push a master puede NO desplegar | Alta |
| DT-11 | Fase 5 de la remediación sin ejecutar: print→logging, lifespan (=DT-02), TRM 4000 hardcodeada, float→Decimal en capa Python | Media |
| DT-12 | `module_flags` inserta fila nueva por toggle en vez de upsert (5 filas para `bot`) | Baja |
| DT-13 | ~~Rama sin merge~~ → merge hecho en local; **falta `git push origin master` + verificar deploy** | **Alta** |
| ~~DT-14~~ | ~~Entidades CT sin `portfolio_id` → consolidado en $0~~ ✅ **RESUELTO 2026-08-21** | — |
| DT-15 | Renombrar `contabilidad-v2/` → `contabilidad/` (Vite lock en Windows: detener el watcher) | Baja |
| DT-16 | Rotar el GitHub PAT del provider de Dokploy (quedó expuesto en una sesión) | Media |
| DT-17 | GitHub tiene `main` como rama por defecto, pero `main` solo es el "Initial commit" vacío: **todo el proyecto vive en `master`**. PRs y clones nuevos apuntan a una rama sin código | Media |
| DT-18 | 4 worktrees obsoletos y 6 ramas `claude/*` + `gilded-mask` colgando del commit raíz huérfano; borrarlos requiere correr los comandos a mano (el clasificador los bloquea al agente) | Baja |
| DT-19 | `uploads/`: 10 audios huérfanos (875 KB) que ninguna transacción referencia; decidir si se conservan | Baja |

---

## Instrucción al Agente al Inicio de Próxima Sesión

1. Leer este archivo completo y el checkpoint más reciente de `docs/checkpoints.md`.
2. Leer `docs/PRD.md` para la intención de negocio (fuente de verdad, no técnica).
3. Correr `python scripts/health_check.py`.
4. `git status` + `git log master..HEAD --oneline` — confirmar si el WIP y la rama siguen sin cerrar.
5. **ANTES** de cualquier cambio: listar archivos a modificar y esperar aprobación.
6. Zero-Impact Policy: módulos nuevos = nuevas carpetas.

---

## Datos de Acceso

**Login único del shell (post-remediación 2026-07-26/27)**: `andres@finsys.os` / `admin123`
— rol `owner` en `hub_users`. Las 5 cuentas demo `@finsys.io` del seed **fueron eliminadas**;
cualquier documento que las mencione está obsoleto. Otras cuentas con login:
`and123@gmail.com` (member) y `testuser@finsys.os` (member).

**Control Tower**: `andres@finsys.os` / `admin123` (bcrypt en `workspace_users`).
**Workspace Hub**: Inversiones FIN-SYS (`37888f92-8bef-4528-b187-2064c6f0049c`)
**Supabase Project**: `sciorfjvdqxvcwgvnmbv` (us-east-2) — compartida entre local y producción.
**Storage Bucket**: `hr-docs` (público)

---

## Contexto RRHH (referencia)

Módulo 08c: `CompanyMapTab.jsx` (árbol Holding→Empresa→Subsidiaria→Proyecto) ·
`MemberProfile.jsx` (Documentos | Historial) · `DocumentsTab.jsx` (drive-style, preview HTML) ·
`HistorialTab.jsx` (pagos + generación de comprobantes) · `RRHHView.jsx`.

**Flujo comprobante**: Generar en Historial → HTML sube a `hr-docs` como
`application/octet-stream` → metadata en `POST /api/hr/documents/{user_id}` → vínculo
`PUT /api/hr/payments/{user_id}/{rec_id}/voucher?doc_id=` → tarjeta 🧾 en Documentos.

**Ojo — tres nociones de "empresa" conviven**: `hub_entities` (proyectos/tareas), entidades del
Control Tower (vínculos laborales y organigrama) y `portfolios` (contabilidad). El WIP de esta
sesión construye el puente CT↔portafolio; `hub_entities` sigue aparte.

---

## Trabajo previo documentado

- **2026-07-05:** fixes críticos RRHH (comprobantes, storage) — `docs/checkpoints.md`
- **2026-07-19/20:** unificación de Contabilidad v1+v2 · pipeline de deploy restaurado
- **2026-07-26:** remediación de auditoría F1–F4 — `docs/remediacion_2026-07.md`
- **2026-07-29:** corrida TestSprite (30 casos) + fixes verificados · `docs/PRD.md` creado
- **2026-08-09/10:** Módulo 09 Bot IA MVP + Módulo 01 completo + consolidado por empresa
- **2026-08-21:** revisión de estado y actualización de checkpoints/memoria (esta sesión)
