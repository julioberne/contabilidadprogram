# Checklist de Inicio de Sesión — FIN-SYS OS v2.0 Health Check

> Ejecutar SIEMPRE al iniciar un nuevo objetivo o tras un reinicio del sistema.

## Comando Rápido
```bash
python scripts/health_check.py
```

---

## Verificaciones Manuales

### 1. Servidores
- [ ] **Frontend (React/Vite)**: `npm run dev` en `./frontend/` → `http://localhost:5173`
- [ ] **Backend (FastAPI)**: `python server.py` en raíz → `http://127.0.0.1:8000`

### 2. Base de Datos
- [ ] **Supabase PostgreSQL**: Conectado (proyecto `sciorfjvdqxvcwgvnmbv`, us-east-2)
- [ ] No caer en Modo Simulación inadvertidamente (`IS_POSTGRES_ACTIVE` debe ser `True`)

### 3. Motor Matemático
- [ ] `tax_motor.py`: IVA 19% y GMF 4x1000 calculados correctamente
- [ ] `test_core.py`: `Ran 5 tests — OK`

### 4. Control Tower
- [ ] `GET /api/ct/entities` responde con árbol de 7 entidades
- [ ] `GET /api/ct/entities/1/kpis` muestra balance_neto ~$42.222.500
- [ ] Login demo: `andres@finsys.os / admin123` funciona

### 5. Módulo Principal
- [ ] `GET /api/portfolios` retorna los 4 portafolios
- [ ] `GET /api/accounts` retorna las 7 cuentas
- [ ] `GET /api/transactions` retorna el libro diario (≥18 registros)

---

## Comandos de Reinicio Rápido

```powershell
# Backend (desde raíz del proyecto)
python server.py

# Frontend (desde carpeta frontend/)
npm run dev
```

---

## Estado Esperado de la BD (Referencia)

| Tabla | Registros esperados |
|---|---|
| `portfolios` | 4 |
| `user_accounts` | 7 |
| `transactions` | ≥18 |
| `third_parties` | ≥5 |
| `entities` (CT) | 7 |
| `workspace_users` (CT) | 5 |
| `resource_ids` (CT) | 14 |
| `approvals_queue` (CT) | 7 |
| `entity_members` (CT) | 6 |
