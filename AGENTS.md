# FIN-SYS OS v2.0 — Instrucciones para el Agente de IA

> Leer este archivo COMPLETO al inicio de cada sesión antes de hacer cualquier cambio.

---

## Stack Tecnológico

| Capa | Tecnología | Archivo / Ruta | Puerto |
|---|---|---|---|
| Backend | FastAPI (Python 3.10+) | `server.py` | `:8000` |
| Frontend | Vite + React 19 | `frontend/` (`src/` = código) | `:5173` |
| Base de Datos | PostgreSQL 17 (Supabase) | Cloud · us-east-2 | — |
| IA Voz / texto | Groq (Whisper + LLM de `GROQ_MODEL`, default `openai/gpt-oss-120b`) | `fin_sys_core/ai_engine.py` | — |
| IA Fallback | Gemini API | `fin_sys_core/ai_engine.py` | — |
| Estilo Visual | Retro-Brutalista | IBM Plex Mono · bordes 2px · 0px radius | — |

---

## Cómo evaluar el estado del proyecto (EJECUTAR AL INICIO Y AL FINAL)

Las fuentes ejecutables son la verdad. Los conteos hardcodeados (tablas, endpoints, TXs) **siempre derivan** — no confiar en números fijos; leerlos del output en vivo.

```bash
# 1. Salud completa del sistema (7 checks): frontend, backend, BD, motor, CT, Hub, integridad
python scripts/health_check.py

# 2. Mantenimiento de sesión — usar SIEMPRE --check (solo verifica, no escribe).
#    ⚠️ Sin argumentos o con --clean BORRA en la BD compartida con producción
#    (hr_documents con URL vacía/localhost, workspaces del Hub sin nombre): solo con
#    aprobación explícita de Andrés y revisando antes qué filas caerían.
python scripts/session_maintenance.py --check

# 3. Tests del motor matemático (deben pasar 5/5)
python tests/test_core.py

# 4. Tests del kernel contable (partida doble Zero-COA)
python -m kernel.test_kernel
python tests/test_e2e.py
```

**Checks del health_check.py (7)** — el orden importa, los posteriores se omiten si fallan los críticos:
1. Frontend Vite `:5173` (si cae, prueba `:5174` → hay proceso Node zombie). Es normal verlo en rojo cuando se trabaja contra `localhost:8000`, que sirve el build `frontend/dist` (ver CHECKLIST → "Local al día con producción")
2. Backend FastAPI `:8000`
3. PostgreSQL (TXs, entidades CT, cuentas, TXs sin `account_id` → alerta DT-01)
4. Motor matemático (IVA=19000, GMF=400 sobre 100000)
5. Control Tower API (`/api/ct/entities`, KPIs holding)
6. Project Hub API (workspaces, usuarios, tareas, notas)
7. Integridad de datos (workspaces sin nombre, portafolios <4, cuentas bancarias = 0)

**Contexto vivo de la sesión**: leer `CHECKLIST.md` (raíz) — estado actual, pendientes y arranque — y el último checkpoint de `docs/checkpoints.md`. Se actualizan cada sesión; sus conteos son más frescos que los de este `AGENTS.md`.

**Deuda técnica**: ver la tabla DT-* en `CHECKLIST.md` (DT-01 = balance -$11.2M por TXs legacy sin `account_id`; DT-04/DT-05 ya resueltas — bcrypt desde 2026-07-26).

---

## Estado de Módulos

| Módulo | Archivos Clave | Estado | Regla |
|---|---|---|---|
| **Shell Unificado** | `frontend/src/main.jsx`, `frontend/src/shell/*` | ✅ ACTIVO | main.jsx consume del registry; no editar switch manual |
| **Registry (SSOT)** | `frontend/src/registry/moduleRegistry.js` | ✅ ACTIVO | Agregar módulos aquí — Sidebar/Home/main.jsx leen automáticamente |
| **Contabilidad (01–06, unificado)** | `frontend/src/contabilidad-v2/` (ContabilidadApp + engine/ + modules/ + components/) | ✅ ACTIVO | UI v1 sobre providers modulares. App.jsx monolítico ELIMINADO (19 Jul 2026) — rollback vía git revert |
| fin_sys_core | `database_driver.py`, `tax_motor.py`, `ledger_math.py`, `ai_engine.py` | ✅ ESTABLE | Solo con aprobación explícita |
| Control Tower (07) | `frontend/src/control-tower/*`, `fin_sys_core/control_tower_driver.py` | ✅ COMPLETO | NO mezclar con el módulo Contabilidad |
| Project Hub (08) | `frontend/src/project-hub/*`, `fin_sys_core/hub_driver.py` | ✅ COMPLETO | NO refactorizar sin permiso |
| RRHH / Empresas (08c) | `project-hub/features/members/tabs/`, `fin_sys_core/hr_driver.py`, `fin_sys_core/hr_documents_driver.py` | ✅ EN USO | Solo agregar, no modificar existentes |
| **Zero-COA** | `server.py` (bloque final), `kernel/`, `scripts/seed_puc.py`, `posting_rules` (BD) | ✅ FASE 1+2 | Emit automático de partida doble |
| **Módulo 09 (Bot IA)** | `fin_sys_core/bot_driver.py`, `bot_telegram.py`, `draft_builder.py`, `bot_sms.py`, `sms_bancolombia.py`, `terceros_cuentas.py`, `bot_retencion.py` · `routers/bot.py`, `routers/webhooks_sms.py`, `routers/third_party_accounts.py` · `frontend/src/bot/*` (bandeja) | ✅ EN PRODUCCIÓN — etapas A–G (30 Sep 2026); H (OCR) planificada | Ver "BOT IA — reglas propias" abajo. Specs por etapa en `docs/specs/09-bot-ia/`; referencia operativa en `docs/bot_ia.md` |
| Módulo 10 (Trading NASDAQ) | `frontend/src/trading/*` (por crear) | 🔵 PLANIFICADO | Crear en carpeta nueva, registrar en registry |
| **Módulo 12 (Contadores)** | `frontend/src/contadores/*`, `routers/contadores.py`, `kernel/kernel_journal_workflow.py`, `kernel/kernel_periods.py`, `kernel/kernel_reports.py`, `fin_sys_core/coa_admin_driver.py` | ✅ v1 (15 Sep 2026) | Asientos nacen BORRADOR y solo el contador los CONTABILIZA; reportes = asientos en libros (CONTABILIZADO+ANULADO). Rol `contador` + `require_contador`. Un periodo cerrado bloquea TXs y asientos |
| **Módulo 13 (Análisis Inteligente)** | `fin_sys_core/metrics_catalog.py`, `analytics_qa.py`, `insight_engine.py` · `routers/analytics.py` · `frontend/src/analisis/*` | ✅ hitos 1–3 (22 Sep 2026); falta export .xlsx | Catálogo de métricas en lista blanca; la IA traduce la pregunta, jamás calcula |

---

## Reglas Críticas — OBLIGATORIAS

### ZERO-IMPACT POLICY
- **NUNCA** modificar archivos de módulos COMPLETOS para agregar funcionalidad nueva
- Módulos nuevos → nuevas rutas, nuevos archivos, nuevas carpetas
- Endpoints nuevos → crear/editar un router en `routers/*.py` (uno por dominio) y registrarlo en `server.py` con `include_router`. Nunca reescribir endpoints existentes
- Contabilidad: la lógica de formulario/registro vive en `contabilidad-v2/engine/` (providers); UI en `modules/<dominio>/` y `components/`. Nuevas features contables = nuevo module + adapter

### AGREGAR UN MÓDULO NUEVO (flujo correcto)
1. Crear carpeta + componente en `frontend/src/<modulo>/`
2. Agregar **una entrada** al array `modules` en `frontend/src/registry/moduleRegistry.js` (id, label, icon, group, component lazy, `active`)
3. Sidebar, HomeDashboard y main.jsx lo consumen automáticamente — **no editar main.jsx**
4. Si necesita endpoints → router nuevo en `routers/` + `include_router` en `server.py`
5. Feature flags remotos (`/module-flags` en BD) pueden override del campo `active`

### BOT IA (Módulo 09) — reglas propias
- **Regla 6b — "el bot no adivina"** (`docs/reglas_proyecto.md`): cualquier dato que el bot necesite debe existir como campo estructurado en la web; si no existe, se pide a mano. Sin heurísticas, pistas, puntajes ni aprendizaje implícito; los SMS del banco se leen por plantillas (regex por familia) y lo que no se reconoce se conserva, nunca se descarta en silencio.
- **Nada contable sin confirmación humana**: todo entra como borrador (`transaction_drafts`) y solo `Confirmar #N` o el botón ✅ crea la transacción. Registrar un medio de pago de un tercero también es un toque explícito (💾).
- **El token de Telegram es el MISMO en local y en producción** (decisión de Andrés): **no lanzar `fin_sys_core/bot_telegram.py` en local** — chocaría con el poller de producción (409). El bot se prueba con los tests (`bot_driver.handle_message` / `handle_callback`); en el chat real los cambios se ven después del deploy.
- **La BD es compartida con producción**: los tests de integración del bot usan un chat `test-…`, terceros con sufijo único y la cola de SMS `sms_prueba` (nunca `sms`, que atiende el poller real), y borran sus filas en `tearDown`.
- **Trabajar por id**: cuentas y terceros se cruzan por campos estructurados (`last4_cuenta`, `last4_tarjeta`, `phone`, `third_party_accounts`), siempre por igualdad; los nombres son libres.
- **Specs**: cada etapa tiene su spec en `docs/specs/09-bot-ia/` (requisitos `R-`, decisiones `D-`, criterios `CA-`); al cerrar una etapa se actualiza su `Estado`.

### PERMISOS EXPLÍCITOS POR ARCHIVO

| Archivo | Permiso |
|---|---|
| `fin_sys_core/database_driver.py` | 🔴 Solo con aprobación explícita del usuario |
| `fin_sys_core/control_tower_driver.py` | 🔴 Solo con aprobación explícita del usuario |
| `server.py` | 🟡 Solo bootstrap + registrar routers. Endpoints viven en `routers/*.py` |
| `frontend/src/contabilidad-v2/engine/*` | 🟡 Motor del módulo contable (providers + payload). Cambios con tests (`npm test`) |
| `frontend/src/contabilidad-v2/modules/*` | 🟢 ACTIVO — UI por dominio + adapters, libre modificación |
| `.env` | 🔴 NUNCA tocar bajo ninguna circunstancia |
| Tablas de BD existentes | 🔴 NUNCA alterar schema sin aprobación explícita |
| `frontend/src/control-tower/*` | 🟡 No mezclar paleta ámbar con paleta brutalista del módulo principal |
| `fin_sys_core/hr_driver.py` | 🟢 ACTIVO — Solo agregar endpoints/funciones, no modificar existentes |
| `fin_sys_core/hr_documents_driver.py` | 🟢 ACTIVO — Solo agregar endpoints/funciones, no modificar existentes |
| `project-hub/features/members/tabs/` | 🟢 ACTIVO — Libre modificación dentro de la carpeta |
| `frontend/src/shell/shell.css` | 🟢 ACTIVO — Design tokens del shell, libre modificación |
| `frontend/src/shell/Sidebar.jsx` | 🟢 ACTIVO — Lee del registry; no hardcodear items |
| `frontend/src/shell/HomeDashboard.jsx` | 🟢 ACTIVO — Lee del registry; no hardcodear módulos |
| `frontend/src/registry/moduleRegistry.js` | 🟢 ACTIVO — SSOT de módulos, agregar entradas aquí |
| `frontend/src/main.jsx` | 🟡 No editar el switch — consume del registry. Solo tocar si hay bug del shell |
| `frontend/src/contabilidad-v2/components/*` | 🟢 ACTIVO — ContextPanel, tabs, modales, inventario (Cartera + Zero-COA toggle) |
| `fin_sys_core/bot_*.py`, `sms_bancolombia.py`, `terceros_cuentas.py`, `draft_builder.py` | 🟢 ACTIVO — Bot IA; cambios con tests (puros en CI + con BD en local) y respetando la Regla 6b |
| `kernel/*` | 🟢 ACTIVO — Motor contable, event bus, accounting |
| `scripts/seed_puc.py` | 🟢 ACTIVO — Seed PUC + posting rules |

### ⚠️ ENDPOINTS HUÉRFANOS (documentar, NO borrar)
Existen en el código pero **no tienen consumidor activo** en el frontend
(ambos son stubs `NOT_IMPLEMENTED` en `routers/hr.py`):
- `POST /api/hr/storage/sign-upload` — Sustituido por data URL base64 (bucket bloquea MIME)
- `POST /api/hr/salary/calculate` — Cálculo ocurre localmente en `SalaryTab.jsx`

_Eliminados (2026-07-26, ya no existen en el código): `PUT /api/hr/salary/v2/{user_id}`
y `PUT /api/hr/profile/v2/{user_id}`._

> **Regla**: Mantenerlos hasta la sesión de limpieza técnica (DT-21 en `CHECKLIST.md`).

### PROTOCOLO OBLIGATORIO ANTES DE CUALQUIER CAMBIO
1. **Listar** exactamente qué archivos se van a modificar y por qué
2. **Mostrar el plan** → **esperar aprobación** del usuario antes de escribir código
3. **Ejecutar un paso a la vez**, no bundling de cambios
4. **Resumir** qué cambió, qué NO se tocó, y qué riesgos existen

---

## Comandos de Desarrollo

```bash
# ── Backend (desde la raíz del proyecto) ──
python server.py                              # arrancar FastAPI :8000
python scripts/health_check.py                # health check (7 checks)
python tests/test_core.py                     # tests motor matemático (5/5)
python -m kernel.test_kernel                  # tests kernel Zero-COA (6/6)
python tests/test_contadores.py               # módulo Contadores (15/15, BD real)
python -m unittest tests.test_single_module_identity tests.test_tx_atomica   # un solo pool / TX+asiento atómicos
python tests/test_e2e.py                      # tests end-to-end kernel (FINSYS_BASE para otro puerto)

# ── Frontend (desde frontend/) ──
npm run dev                                   # Vite dev server :5173
npm run lint                                  # ESLint
npm test                                      # Vitest (run once, jsdom)
npm run test:watch                            # Vitest watch mode
npm run build                                 # build producción

# ── Si Vite arranca en :5174 (proceso Node zombie) ──
#   Get-Process -Name node | Stop-Process -Force
#   cd frontend && npm run dev

# ── Si puerto 8000 ocupado ──
#   Get-Process python | Stop-Process -Force
```

> **Orden de verificación recomendado**: `lint` → `typecheck` (no configurado actualmente) → `test` → `health_check`.

---

## Identidad Visual

### Módulo Principal (App 01–06) — paleta brutalista
- Fuente: `IBM Plex Mono` (monospaced en todo el texto)
- Bordes: `2px solid #000000`
- Border-radius: `0px` — absolutamente cuadrado
- Sombras: `3px 3px 0 #000` — duras, no difusas
- Paleta: negro, blanco, verde HSL (positivo), `#FFB000` ámbar (warnings)

### Control Tower (Módulo 07) — PALETA DIFERENTE, NO MEZCLAR
- Color de acento: ámbar `#fbbf24` (Tailwind `amber-400`)
- Fondo: `bg-black`
- Sombras duras en ámbar: `shadow-[8px_8px_0px_#fbbf24]`
- Esta paleta NO se usa en el módulo Contabilidad ni viceversa

---

## Arquitectura de Datos (Referencia Rápida — los conteos DERIVAN, verificar con health_check)

- **Portafolios**: 4 (IDs 1–4: Negocio A, Pegasus, Personal, Principal) — health_check alerta si <4
- **Cuentas bancarias**: DINÁMICAS — las crea el usuario con su balance inicial (no hay número fijo). El seed por defecto inserta 5 si la tabla está vacía. health_check solo alerta si hay 0 cuentas
- **Entidades CT**: árbol de 4 niveles (Holding → Empresa → Sub → Proyecto)
- **workspace_users CT**: admin `andres@finsys.os / admin123`
- **Storage Bucket**: `hr-docs` (público, MIME `application/octet-stream` para HTML)
- Conteos de TXs, tablas y endpoints: **leer del output de `health_check.py`**, no hardcodear

---

## Contexto de Memoria

> Leer `CHECKLIST.md` (raíz) para el estado actual, pendientes y archivos prohibidos,
> y `docs/checkpoints.md` para lo que pasó en sesiones anteriores.
> Se actualizan cada sesión — son más frescos que este `AGENTS.md` para conteos y deuda técnica.
> Para diseñar o continuar una etapa: `docs/specs/README.md` (specs por módulo y etapa).
> Cómo se trabaja hoy (push de Andrés, deploy por script, sin HTTPS en producción): nota "Estado real" al inicio de `WORKFLOW.md`.
