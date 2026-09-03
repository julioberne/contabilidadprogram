# CHECKLIST — FIN-SYS OS v2.0

> **Único archivo de estado vivo.** Aquí: qué hay, qué falta, cómo arrancar.
> Lo que ya pasó (con verificación) va a `docs/checkpoints.md` — un checkpoint por sesión.
> Última actualización: **03 Sep 2026**.

---

## 1. Estado actual

| Dónde | Estado |
|---|---|
| `master` local | al día con origin (03 sep: bandeja bot, consolidado CUENTAS, cartera plan de pagos + UX) |
| `origin/master` = producción :8080 | desplegado y verificado 03 sep. Deploy estándar: `scratch/deploy_prod.py` (el agente tiene permiso); push lo corre Andrés (credencial del agente expira) |
| BD Supabase | compartida local↔prod · **reiniciada con `feat(reset)`: 0 TXs** · 6 entidades CT (2 vinculadas) · 5 cuentas · 4 portafolios · patrimonio $1.000.000 (verificado 26 ago) |

### Módulos

| # | Módulo | Estado | Ruta |
|---|---|---|---|
| 01–06 | Contabilidad (unificado) | ✅ COMPLETO | `frontend/src/contabilidad-v2/` |
| 07 | Control Tower | ✅ COMPLETO | `frontend/src/control-tower/` |
| 08 / 08c | Project Hub · RRHH/Empresas | ✅ EN USO | `frontend/src/project-hub/` |
| — | Zero-COA Kernel | ✅ Fase 1+2 | `kernel/` |
| 09 | Bot IA (Telegram + Groq) | ✅ MVP en producción · faltan etapas C, B.5, D–F | `fin_sys_core/bot_*.py`, `routers/bot.py` |
| 10 | Trading NASDAQ | 🔵 PLANIFICADO | — |
| 11 | Reportes PDF/Excel · Facturación B2B | 🔵 PLANIFICADO | — |

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
| ~~DT-22~~ | **CERRADA 02 sep** — pooler en transaction mode `6543` en local Y en Dokploy (verificado por API) + redeploy hecho. NUNCA volver a 5432 | ✅ |
| DT-21 | Endpoints huérfanos (stubs `NOT_IMPLEMENTED` en `routers/hr.py`): `POST /api/hr/storage/sign-upload`, `POST /api/hr/salary/calculate` — remover o activar con DT-09 | Baja |

### Funcional / calidad

- [ ] **TC022** — Libro Diario sin buscador (brecha de spec TestSprite; decidir si se agrega)
- [ ] **TestSprite**: re-correr sobre el build actual y avanzar TC031–TC050 (última corrida 29 jul: 25/30 ✅)
- [ ] **Bot IA**: ✅ funcionando en producción (gpt-oss-120b) y **Etapa C COMPLETA** — bandeja web en uso real (4 borradores confirmados por Andrés). Quedan B.5 (RAG) y D–F
- [ ] **Cartera Fase 2**: recordatorios personalizables por Telegram (tick en el poller, `cartera_reminders`, resumen periódico) — el diseño está en el checkpoint 03-sep
- [ ] **Pipeline de etiquetas**: los tags NO llegan a la transacción en ningún flujo (falta campo en TransactionInput + persistencia) — hoy solo viven en el borrador del bot
- [ ] **Portafolios**: la columna de vínculos se retiró del consolidado (02 sep) — reubicar con mejor funcionamiento y dar presupuesto a "Finanzas Personales Julian"
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

### Verificación mínima antes de dar algo por bueno

```powershell
python -m kernel.test_kernel                                                   # 5/5 partida doble
python tests/test_core.py                                                      # 5/5 motor matemático
python -m unittest tests.test_bot_driver tests.test_bot_confirmation tests.test_bot_resolvers
python tests/test_e2e.py                                                       # ⚠️ crea una TX REAL en la BD compartida — solo a propósito, con backend arriba
cd frontend; npx vitest run; npm run build                                     # 45 tests y build de producción
```

- `GET http://127.0.0.1:8000/docs` responde · `GET /api/org/consolidated` → 200 (si 404, backend viejo)
- Ojo: la BD es **compartida con producción** — un borrado local borra en prod.

---

## 4. Referencia (accesos y deploy)

- **Login shell y Control Tower**: `andres@finsys.os` / `admin123` (las cuentas `@finsys.io` no existen; doc que las mencione está obsoleto). Otras: `and123@gmail.com`, `testuser@finsys.os` (member).
- **Supabase**: proyecto `sciorfjvdqxvcwgvnmbv` (us-east-2) · bucket `hr-docs` (público).
- **Producción**: http://159.223.156.50:8080 · Panel Dokploy :3000 · compose único `finsys-app`.
- **Deploy** = `git push origin master` (lo corre Andrés) → webhook Dokploy. Si no dispara (DT-10): `POST /api/compose.deploy` con la key de `scratch/dokploy.env`, o panel :3000 → Deploy.
- **Workspace Hub**: Inversiones FIN-SYS (`37888f92-8bef-4528-b187-2064c6f0049c`).

### Zero-Impact Policy (regla de oro)

Funcionalidad nueva = archivos nuevos. **Prohibido sin aprobación explícita**:
`fin_sys_core/database_driver.py` · `fin_sys_core/control_tower_driver.py` ·
`frontend/src/control-tower/*` · `.env` · alterar schema de tablas existentes.

### Cierre de sesión (obligatorio)

1. Agregar checkpoint a `docs/checkpoints.md` (qué se hizo, cómo se verificó).
2. Actualizar **este archivo**: tabla de estado, pendientes cerrados/nuevos.
3. Nada más — los demás .md no se tocan por rutina (los históricos viven en `docs/archive/`).
