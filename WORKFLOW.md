# 🧭 WORKFLOW.md — Metodología de Trabajo para Agentes IA
## FIN-SYS OS v2.0 · Última actualización: 30 Sep 2026 (nota "Estado real"; el resto del documento es de julio)

> **Este archivo es de lectura obligatoria para cualquier agente IA al inicio de cada sesión.**
> Describe el flujo completo: desarrollo local → git → producción vía Dokploy.
> Complementa a `AGENTS.md` (reglas del proyecto) con el **cómo trabajamos**.

---

## ⚠️ Estado real al 30 Sep 2026 (manda sobre lo que diga más abajo)

Varias secciones de este documento describen el plan original de julio. Hoy se trabaja así:

| Tema | Lo que dice el documento | Lo que pasa hoy |
|---|---|---|
| **Deploy** | "auto-deploy" por webhook al hacer push | **No hay webhook.** Tras cada push a `master` el agente corre `.venv\Scripts\python.exe scratch\deploy_prod.py` (API de Dokploy) y verifica con una sonda (una ruta nueva que pase de 404 a 401, `/api/health`, hash del bundle). |
| **Push** | lo ejecuta el usuario o el agente con aprobación | Lo hace **Andrés** en su terminal: `git push origin master`. El agente commitea en `master` y espera el push. |
| **Producción** | Traefik con SSL en 443 | **`https://finsys-andres.duckdns.org`** desde el 30-sep-2026 17:15: dominio gratis de DuckDNS (cuenta de Andrés) + certificado Let's Encrypt emitido por el Traefik de Dokploy (dominio del compose `finsys-app` → servicio `frontend`, puerto 80; HTTP redirige 301 a HTTPS). `http://159.223.156.50:8080` sigue respondiendo. El teléfono ya envía los SMS directo a producción; el túnel `cloudflared` al PC quedó solo como plan de contingencia. |
| **Backend local** | `uvicorn --reload` lanzado por el usuario | Preview `finsys-backend` (`.claude/launch.json`) en `:8000`, que sirve el build congelado `frontend/dist`. Tras cambios de frontend: `npm run build` (o `scripts\sync_local.py`). Vite `:5173` es opcional. |
| **Python** | `python …` | Siempre `.venv\Scripts\python.exe` (el Python global no tiene las dependencias). |
| **Base de datos** | — | **Una sola BD (Supabase) para local y producción**: un borrado o un dato de prueba en local existe en producción. Los tests de integración limpian sus filas. |
| **Bot de Telegram** | bots distintos para dev y prod | **Mismo token en local y producción**: no lanzar el poller local. Reglas del bot en `AGENTS.md` → "BOT IA — reglas propias". |
| **Ramas** | ramas de feature para módulos nuevos | Todo se integra directo a `master`, sin PRs: desde el checkout principal, o desde el worktree de una sesión (`git push origin <rama>:master`). Commits pequeños y verificados. |
| **Cierre de sesión** | checkpoint + CHECKLIST | Además: spec de la etapa (`docs/specs/`), `database_schema.md` / `api_spec.md` si hubo tablas o endpoints, y `AGENTS.md` si cambió el estado de un módulo (Regla 10 de `docs/reglas_proyecto.md`). |
| **Mantenimiento** | `session_maintenance.py` | Solo con `--check`. Sin argumentos ejecuta borrados en la BD compartida. |

---

## 📐 Principio Central

```
Todo cambio sigue este ciclo sin excepciones:
  LOCAL → VERIFICAR → COMMIT → PUSH → DOKPLOY (auto-deploy)
```

Un agente IA **nunca salta pasos**. Nunca modifica y commitea sin verificar.
Nunca pushea sin que el humano haya aprobado el commit.

---

## 🗺️ Mapa del Entorno

```
┌─────────────────────────────────────────────────────────┐
│  LOCAL (Windows · OneDrive)                             │
│  C:\Users\andre\...\contabilidadprogram\                │
│  ├── Frontend : Vite/React  → http://localhost:5173     │
│  └── Backend  : FastAPI     → http://localhost:8000     │
└──────────────────┬──────────────────────────────────────┘
                   │  git push origin master
                   ▼
┌─────────────────────────────────────────────────────────┐
│  GITHUB                                                 │
│  https://github.com/julioberne/contabilidadprogram      │
│  Rama única de verdad: master                           │
└──────────────────┬──────────────────────────────────────┘
                   │  webhook automático (Dokploy detecta push)
                   ▼
┌─────────────────────────────────────────────────────────┐
│  PRODUCCIÓN (VPS · Dokploy)                             │
│  ├── finsys-backend  : FastAPI/Gunicorn  → :8000        │
│  ├── finsys-frontend : Vite build/Nginx  → :8080        │
│  └── Traefik (proxy SSL, puerto 443 → 8080)             │
└─────────────────────────────────────────────────────────┘
```

---

## ⚙️ Arranque del Entorno Local

El agente NUNCA arranca los servidores por sí solo (son procesos del usuario).
Solo puede verificar que están corriendo.

### Backend (FastAPI)
```powershell
# Desde la raíz del proyecto
python -m uvicorn server:app --host 127.0.0.1 --port 8000 --reload
```

### Frontend (Vite)
```powershell
# Desde frontend/
npm run dev -- --port 5173
```

### Verificación de salud
```powershell
python scripts/health_check.py
# Resultado esperado:
# ✅ Frontend  → :5173 OK
# ✅ Backend   → :8000 OK
# ✅ PostgreSQL → tablas | entidades CT
# ✅ Motor     → IVA=19.000 | GMF=400
```

---

## 🌿 Estrategia de Git

### Modelo: Trunk-Based en master

Este proyecto usa un flujo **trunk-based**:
- **Una sola rama de verdad**: `master`
- **No existe** una rama `develop` permanente
- Los features grandes se trabajan en ramas temporales que se mergean a `master`

### Cuándo usar ramas de feature

| Situación | ¿Rama? | Nombre sugerido |
|---|---|---|
| Fix rápido (< 1 archivo) | ❌ Directo a master | — |
| Feature nuevo (módulo 09, 10...) | ✅ Sí | `modulo-09-bot-ia` |
| Refactor de riesgo medio | ✅ Sí | `refactor-kernel-emits` |
| Limpieza técnica / deuda | ✅ Sí | `fix-dt04-bcrypt` |
| Actualizar documentación | ❌ Directo a master | — |

### Ciclo de vida de una rama de feature

```bash
# 1. Crear rama SOLO cuando empiezas a trabajar en ella
git checkout -b modulo-09-bot-ia

# 2. Desarrollar y commitear en la rama
git add <archivos específicos>
git commit -m "feat(bot): webhook FastAPI + bot_driver esqueleto"

# 3. Mantener al día con master (si la sesión dura varios días)
git merge master

# 4. Al terminar el módulo: mergear a master
git checkout master
git merge modulo-09-bot-ia --no-ff -m "feat: Módulo 09 Bot IA completo"
git push origin master

# 5. Borrar la rama (ya no se necesita)
git branch -d modulo-09-bot-ia
```

### ⚠️ Reglas de ramas para el agente IA

```
NUNCA crear una rama y dejarla vacía (sin commits propios)
NUNCA pushear una rama de feature a origin sin aprobación del usuario
NUNCA mergear a master sin que el humano haya revisado los cambios
```

---

## 📝 Convenciones de Commit

Usar **Conventional Commits** siempre. El agente propone el mensaje, el humano aprueba antes de ejecutar.

### Formato
```
<tipo>(<scope>): <descripción corta en español>

[cuerpo opcional: qué cambió y por qué]
```

### Tipos permitidos

| Tipo | Cuándo usarlo |
|---|---|
| `feat` | Nueva funcionalidad visible para el usuario |
| `fix` | Corrección de bug |
| `chore` | Mantenimiento: limpieza, dependencias, gitignore |
| `docs` | Solo documentación (AGENTS.md, CHECKLIST.md, docs/, WORKFLOW.md) |
| `perf` | Mejora de performance sin cambio de funcionalidad |
| `refactor` | Reorganización de código sin cambio de comportamiento |
| `test` | Agregar o corregir tests |

### Ejemplos reales del proyecto

```bash
feat(hub): FASE 3-5 - Notes + Calendar + EntityTree + Metrics completas
fix: import Optional faltante en ledger_math (rompía /api/dashboard-data en prod)
chore: limpieza git + perf hub notes lazy load
docs: actualizar memory-bank con estado verificado E2E 22 Jun 2026
perf(hub): NotesApp convertido a lazy() + Suspense (code splitting)
```

### Reglas del mensaje

```
✅ Máximo 72 caracteres en la primera línea
✅ Mencionar el archivo o módulo afectado en el scope
✅ En español (este proyecto es en español)
✅ Si el commit cierra deuda técnica, mencionar el ID: "fix(DT-01): ..."
❌ NUNCA: "update", "changes", "fix stuff", "wip"
❌ NUNCA commitear .env, node_modules, __pycache__, uploads/
```

---

## 🔄 Protocolo Paso a Paso para el Agente IA

### FASE 0 — Inicio de sesión (SIEMPRE)
```
1. Leer AGENTS.md completo
2. Leer CHECKLIST.md (estado, pendientes) + último checkpoint de docs/checkpoints.md
3. Correr: python scripts/health_check.py
4. Revisar: git status (¿hay cambios pendientes sin commitear?)
5. Confirmar con el usuario qué módulo o tarea se trabajará hoy
```

### FASE 1 — Planificación (ANTES de escribir código)
```
1. Listar EXACTAMENTE qué archivos se van a modificar
2. Listar qué archivos NO se van a tocar
3. Describir qué hace cada cambio y por qué
4. ESPERAR aprobación explícita del usuario antes de continuar
```

**Template de plan:**
```
📋 Plan de cambios — [Nombre del feature]

Archivos a MODIFICAR:
  - routers/bot.py [NUEVO] → webhook endpoint
  - fin_sys_core/bot_driver.py [NUEVO] → lógica de sesiones bot
  - frontend/src/registry/moduleRegistry.js → registrar módulo bot

Archivos que NO se tocan:
  - App.jsx, database_driver.py, control_tower_driver.py, .env

Cambio en BD: [ninguno / nueva tabla bot_sessions]

¿Apruebas este plan?
```

### FASE 2 — Ejecución (UN archivo a la vez)
```
1. Modificar solo los archivos aprobados
2. Después de cada archivo, mostrar diff o resumen del cambio
3. No pasar al siguiente archivo sin confirmar que el anterior es correcto
4. Si aparece un error inesperado → PARAR y consultar antes de improvisar
```

### FASE 3 — Verificación (ANTES del commit)
```
1. python tests/test_core.py          → 5/5 tests deben pasar
2. python scripts/health_check.py     → todos los checks deben ser ✅
3. Si toca frontend: verificar que Vite compila sin errores (npm run build)
4. Probar manualmente el flujo afectado
```

### FASE 4 — Commit y Push
```
1. El agente propone el mensaje de commit (Conventional Commits)
2. El agente propone el git add con archivos específicos (NUNCA git add .)
3. EL USUARIO ejecuta los comandos (o aprueba que el agente los ejecute)
4. Confirmar que push llegó a GitHub: git log --oneline -3
```

### FASE 5 — Cierre de sesión
```
1. Agregar checkpoint a docs/checkpoints.md (qué se hizo, cómo se verificó)
2. Actualizar CHECKLIST.md: tabla de estado, pendientes cerrados/nuevos
3. Nada más — no hay otros .md de estado (los históricos viven en docs/archive/)
```

---

## 🚀 Pipeline de Producción (Dokploy)

### Cómo funciona el deploy automático

```
git push origin master
        │
        ▼
GitHub webhook → Dokploy detecta el push
        │
        ▼
Dokploy hace docker build (Dockerfile)
        │
        ├─► finsys-backend: python:3.12-slim + gunicorn + FastAPI
        └─► finsys-frontend: node build + Nginx en :8080
        │
        ▼
Traefik enruta el tráfico HTTPS → contenedores
        │
        ▼
/api/* → finsys-backend:8000
/*     → finsys-frontend:8080
```

### Variables de entorno en producción

Las variables **NUNCA van en el código**. Están en el panel "Environment" de Dokploy:
```
DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD
GROQ_API_KEY, GEMINI_API_KEY
CORS_ORIGINS (dominio real en producción)
SENTRY_DSN
```

### Cuándo NO hace auto-deploy

Solo si el commit:
- Solo modifica archivos en `.gitignore` (no llegan al repo)
- Solo modifica `docs/` o los .md de la raíz (el Dockerfile no los copia)

### Verificar deploy en producción
```bash
# Health check del backend en producción
curl https://[dominio]/api/health
# Esperado: {"status": "ok", "db": "connected", "version": "2.0"}
```

---

## 🚨 Situaciones de Emergencia

### "Se rompió producción después de un push"
```bash
# 1. Identificar el commit problemático
git log --oneline -5

# 2. Revertir el último commit manteniendo historial
git revert HEAD --no-edit
git push origin master
# Dokploy hace re-deploy automático con el revert
```

### "Algo se rompió en local"
```bash
# Volver al último commit limpio (descarta cambios locales)
git checkout -- <archivo>

# O resetear completamente al último commit
git reset --hard HEAD
```

### "El agente modificó un archivo que no debía"
```bash
# Ver qué cambió
git diff <archivo>

# Revertir ese archivo específico
git checkout -- <archivo>
```

### "Conflicto al mergear rama de feature con master"
```bash
# En la rama de feature
git merge master
# Resolver conflictos manualmente, luego:
git add <archivos resueltos>
git commit -m "merge: resolver conflictos con master"
```

---

## 📋 Checklist Pre-Commit para el Agente

Antes de proponer cualquier commit, verificar:

```
[ ] ¿El cambio fue aprobado por el usuario?
[ ] ¿Solo se tocaron los archivos del plan aprobado?
[ ] ¿python tests/test_core.py pasa 5/5?
[ ] ¿python scripts/health_check.py es todo ✅?
[ ] ¿El .env NO está incluido en git add?
[ ] ¿node_modules, __pycache__, uploads/ NO están incluidos?
[ ] ¿El mensaje de commit sigue Conventional Commits?
[ ] ¿CHECKLIST.md y docs/checkpoints.md están actualizados?
```

---

## 📁 Archivos que el Agente NUNCA debe incluir en un commit

```gitignore
.env                    # ← CRÍTICO: credenciales de producción
.env.local
frontend/.env.*
node_modules/
__pycache__/
frontend/dist/          # build de producción (lo hace Dokploy)
uploads/                # archivos subidos por usuarios
scratch/                # scripts temporales de sesión
*.pyc
mock_db.json
```

---

## 🔗 Archivos de Referencia

| Archivo | Propósito | Frecuencia de lectura |
|---|---|---|
| `AGENTS.md` | Reglas del proyecto, permisos, stack | Cada sesión |
| `WORKFLOW.md` (este) | Metodología de trabajo, git, deploy | Cada sesión |
| `CHECKLIST.md` | Estado actual, pendientes (DT-*), arranque y accesos | Cada sesión |
| `docs/checkpoints.md` | Historial de sesiones (bitácora) | Al buscar qué se hizo antes |
| `docs/PRD.md` | Intención de negocio (fuente de verdad) | Al planificar |
| `docs/system_patterns.md` | Decisiones de arquitectura | Al tocar diseño |
| `docs/specs/README.md` | Specs internos por módulo y etapa (requisitos, decisiones, criterios de aceptación) | Al diseñar o implementar una etapa |

---

> **Regla de oro**: Si hay duda sobre si algo se puede hacer, la respuesta es **NO** hasta que el usuario lo apruebe explícitamente.
> Un agente que pide permiso siempre es mejor que uno que asume.
