# Checklist de Inicio de Sesión — FIN-SYS OS v2.0

> Ejecutar SIEMPRE al iniciar un nuevo objetivo o tras un reinicio del sistema.
> Última actualización: 21 Ago 2026 — 17:05 COT

## Comandos Rápidos

```bash
# Health check completo
python scripts/health_check.py

# Mantenimiento + actualización .md
python scripts/session_maintenance.py

# Solo verificar estado
python scripts/session_maintenance.py --check
```

---

## 0. Verificación de Git (HACER PRIMERO)

Hoy hay trabajo sin cerrar y es fácil pisarlo:

```powershell
git status                          # ¿sigue el WIP del consolidado por entidad?
git log master..HEAD --oneline      # ¿la rama sigue sin merge a master?
```

- [ ] Rama actual: `modulo-09-bot-ia` (worktree principal)
- [ ] **NO descartar el working tree**: `DashboardPanel.jsx` (ya commiteado) llama
      `GET /api/org/consolidated`, endpoint que solo existe sin commitear en `routers/org.py`
- [ ] Recordar: **producción sirve `master`**, que va tres semanas atrás (DT-13)

---

## Arranque Rápido del Sistema

```powershell
# Backend (desde raíz del proyecto)
python -m uvicorn server:app --host 127.0.0.1 --port 8000 --reload

# Frontend (desde carpeta frontend/)
npm run dev -- --port 5173
```

Esperar: `VITE v8.x ready → http://localhost:5173`

---

## Verificaciones Manuales

### 1. Servidores
- [ ] **Frontend (React/Vite)**: `http://localhost:5173` carga la app
- [ ] **Backend (FastAPI)**: `http://127.0.0.1:8000/docs` responde
- [ ] **Producción**: `http://159.223.156.50:8080` responde 200

### 2. Base de Datos
- [ ] **Supabase PostgreSQL**: conectado (proyecto `sciorfjvdqxvcwgvnmbv`, us-east-2)
- [ ] `IS_POSTGRES_ACTIVE` = `True` (no en modo simulación)
- [ ] Ojo: la BD es **compartida entre local y producción** — un borrado local borra en prod

### 3. Motor Matemático y Kernel
- [ ] `python fin_sys_core/test_core.py` → `Ran 5 tests — OK`
- [ ] IVA=19.000 | GMF=400
- [ ] `python -m kernel.test_kernel` → 5/5

### 4. Login (post-remediación de julio)
- [ ] Login único del shell: **`andres@finsys.os` / `admin123`** (rol owner)
- [ ] Las cuentas demo `@finsys.io` **ya no existen**: si un doc las menciona, está obsoleto

### 5. Control Tower (Módulo 07)
- [ ] `GET /api/ct/entities` → árbol de entidades (6 al 21 ago)
- [ ] `GET /api/ct/entities/1/kpis` → responde con KPIs

### 6. Módulo Principal (01–06)
- [ ] `GET /api/portfolios` → 4 portafolios
- [ ] `GET /api/accounts` → 5 cuentas
- [ ] `GET /api/transactions` → ≥13 registros
- [ ] `GET /api/cartera/summary` → incluye `cxc_total`, `cxp_total`, `vencido_total`, `proximo_total`
- [ ] `GET /api/org/consolidated` → responde (si da 404, el WIP no está aplicado)

### 7. Project Hub / RRHH (Módulos 08 y 08c)
- [ ] TaskBoard y COMPENDIO cargan
- [ ] MemberProfile → pestañas Documentos e Historial funcionan
- [ ] Generar comprobante → aparece en Documentos con ícono 🧾

### 8. Módulo 09 — Bot IA (solo en rama)
- [ ] `python -m pytest tests/test_bot_driver.py tests/test_bot_confirmation.py tests/test_bot_resolvers.py`
- [ ] Tablas del bot migradas: `python scripts/migrate_bot_tables.py` (idempotente)
- [ ] Vincular chat↔usuario si hace falta: `python scripts/bot_link_code.py`

---

## Estado Esperado de la BD (verificado 21 Ago 2026 — 16:57 COT)

| Tabla | Registros |
|---|---|
| `portfolios` | 4 |
| `user_accounts` | 5 |
| `transactions` | 13 (2 son `TS-TEST-*`, pendientes de limpieza) |
| `entities` (CT) | 6 — ninguna con `portfolio_id` poblado (DT-14) |
| `hub_workspaces` | 1+ |
| `hub_tasks` | 21 (1 es `TS-TEST-*`) |
| `hr_payment_records` | 13 |
| `hr_documents` | 6 |

---

## Documentos a leer al empezar

1. `memory-bank/activeContext.md` — qué se puede tocar hoy y qué está abierto
2. `docs/checkpoints.md` — checkpoint más reciente (21 ago 2026)
3. `docs/PRD.md` — intención de negocio (fuente de verdad, no técnica)
4. `testsprite_tests/testsprite-mcp-test-report.md` — hallazgos E2E abiertos
