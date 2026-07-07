# Checklist de Inicio de Sesión — FIN-SYS OS v2.0

> Ejecutar SIEMPRE al iniciar un nuevo objetivo o tras un reinicio del sistema.
> Última actualización: 05 Jul 2026 — 19:09 COT

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

### 2. Base de Datos
- [ ] **Supabase PostgreSQL**: Conectado (proyecto `sciorfjvdqxvcwgvnmbv`, us-east-2)
- [ ] `IS_POSTGRES_ACTIVE` = `True` (no en modo simulación)

### 3. Motor Matemático
- [ ] `python fin_sys_core/test_core.py` → `Ran 5 tests — OK`
- [ ] IVA=19.000 | GMF=400

### 4. Control Tower (Módulo 07)
- [ ] `GET /api/ct/entities` → árbol de 7 entidades
- [ ] `GET /api/ct/entities/1/kpis` → balance_neto ~$42,222,500
- [ ] Login: `andres@finsys.os / admin123`

### 5. Módulo Principal (01–06)
- [ ] `GET /api/portfolios` → 4 portafolios
- [ ] `GET /api/accounts` → 7 cuentas
- [ ] `GET /api/transactions` → ≥13 registros

### 6. Project Hub (Módulo 08)
- [ ] Login Hub: `andres@finsys.io / admin123`
- [ ] TaskBoard carga con 21 tareas y 6 usuarios
- [ ] La app principal NO queda bloqueada al navegar entre vistas

### 7. RRHH / Empresas (Módulo 08c)
- [ ] Menú lateral muestra "EMPRESAS" (no RRHH)
- [ ] CompanyMapTab muestra árbol jerárquico
- [ ] MemberProfile → pestaña Documentos funciona
- [ ] MemberProfile → pestaña Historial muestra pagos
- [ ] Generar comprobante → aparece en Documentos con ícono 🧾
- [ ] Preview de comprobante abre modal con HTML renderizado

---

## Estado Esperado de la BD (Verificado 05 Jul 2026 — 19:09 COT)

| Tabla | Registros |
|---|---|
| `portfolios` | 4 |
| `user_accounts` | 7 |
| `transactions` | ≥13 |
| `entities` (CT) | 7 |
| `workspace_users` (CT) | 5 |
| `hub_workspaces` | 1 |
| `hub_users` | 6 |
| `hub_tasks` | 21 |
| `hr_members` | N/A |
| `hr_payment_records` | 13 |
