# Módulo 08: Project Hub — Documentación Técnica
*FIN-SYS OS v2.0 · Última actualización: 2026-06-11*

---

## Descripción

El **Project Hub** es un dashboard colaborativo multi-tenant, completamente independiente de los módulos contables existentes (Zero-Impact Policy). Permite a equipos gestionar proyectos, tareas, notas, calendarios y jerarquías organizacionales.

**Acceso**: En `http://localhost:5173` → botón `⬡ PROJECT HUB` (azul cian)

---

## Stack Técnico

| Capa | Tecnología | Archivos |
|---|---|---|
| Shell React | Vite + React | `frontend/src/project-hub/` |
| Estado global | Custom Hook | `hooks/useProjectHub.js` |
| Task Board | @dnd-kit/core + sortable | `features/tasks/` |
| Editor notas | @blocknote/react | `features/notes/` |
| Calendario | react-big-calendar + moment | `features/calendar/` |
| Backend CRUD | FastAPI + Python | `server.py` (final), `fin_sys_core/hub_driver.py` |
| Base de datos | PostgreSQL (Supabase) | 10 tablas `hub_*` |

---

## Arquitectura de Componentes

```
ProjectHubApp.jsx              ← Root: login → workspace → vistas
├── HubTopBar.jsx              ← Breadcrumb, usuario, logout/exit
├── HubSidebar.jsx             ← Nav, proyectos, workspace switcher
│   └── WorkspaceSwitcher.jsx  ← Selector multi-workspace
├── HubLoginRegister.jsx       ← Auth + registro con workspace
└── Vista activa (switch):
    ├── TaskBoard.jsx          ← Kanban | Lista (toggle)
    │   ├── KanbanView.jsx     ← DnD drag-drop
    │   ├── ListView.jsx       ← Tabla sorteable
    │   └── TaskModal.jsx      ← Crear/editar tarea
    ├── NotesApp.jsx           ← Lista + editor BlockNote
    │   └── NoteEditor.jsx     ← Editor rich text
    ├── CalendarApp.jsx        ← react-big-calendar multi-vista
    │   ├── EventModal.jsx     ← Crear/editar evento
    │   └── calendar-overrides.css
    ├── MembersList.jsx        ← Grid equipo + KPIs
    │   └── MemberProfile.jsx  ← Perfil individual detallado
    └── WorkspaceSettings.jsx  ← Info + árbol org.
        └── EntityTree.jsx     ← Árbol recursivo editable
```

---

## API Endpoints Hub (22 endpoints)

```
GET/POST  /api/hub/workspaces
POST      /api/hub/users/register
POST      /api/hub/users/login
GET       /api/hub/users
POST      /api/hub/users/add-member
GET/POST/DELETE  /api/hub/entities[/{id}]
GET/POST  /api/hub/projects
GET/POST  /api/hub/tasks
PUT/DELETE /api/hub/tasks/{id}
GET/POST  /api/hub/notes
PUT       /api/hub/notes/{id}
GET/POST  /api/hub/events
PUT       /api/hub/events/{id}
GET       /api/hub/metrics
```

---

## Tablas de Base de Datos

| Tabla | Descripción |
|---|---|
| `hub_workspaces` | Organizaciones multi-tenant |
| `hub_users` | Usuarios del hub (independientes) |
| `hub_workspace_members` | Roles por workspace (owner/admin/member/viewer) |
| `hub_entities` | Árbol jerárquico flexible (sin límite de niveles) |
| `hub_projects` | Proyectos dentro de un workspace |
| `hub_tasks` | Tareas con status, prioridad, deadline |
| `hub_task_assignees` | Asignados por tarea (N:M) |
| `hub_notes` | Notas con contenido BlockNote JSON |
| `hub_events` | Eventos de calendario |
| `hub_event_attendees` | Asistentes por evento (N:M) |

---

## Datos de Prueba (Seed)

### Workspace principal
**Inversiones FIN-SYS** · NIT: 900.123.456-7

### Credenciales de acceso
| Rol | Email | Contraseña | Nombre |
|---|---|---|---|
| OWNER | `andres@finsys.io` | `admin123` | Andrés Ramírez |
| ADMIN | `sofia@finsys.io` | `sofia123` | Sofía Martínez |
| MEMBER | `camilo@finsys.io` | `camilo123` | Camilo Torres |
| MEMBER | `valentina@finsys.io` | `vale123` | Valentina Gómez |
| VIEWER | `daniel@finsys.io` | `daniel123` | Daniel Ospina |

### Proyectos (3) y Tareas (20)

**FIN-SYS OS — Plataforma Principal** (8 tareas)
- DONE: Migrar CT a Router, Caché Redis, Actualizar AGENTS.md
- IN_PROGRESS: Notificaciones RT, Supabase Realtime en TaskBoard
- REVIEW: Tests unitarios hub_driver.py
- TODO: Pruebas carga, Audit seguridad SHA-256→bcrypt

**Módulo 08 — Trading NASDAQ** (6 tareas)
- DONE: Esquema tablas trading_*
- IN_PROGRESS: Integración Alpaca Markets API
- TODO: Velas, PnL, Portfolio heatmap, Alertas stop-loss

**Operaciones Q2 2026** (6 tareas)
- DONE: Revisar estados financieros Mayo
- REVIEW: Informe KPIs junta directiva
- IN_PROGRESS: Renovar contratos SaaS
- TODO: Capacitación Hub, Auditoría permisos BD, Migración Dokploy

### Árbol Organizacional (9 entidades, 3 niveles)
```
Inversiones FIN-SYS Holding [HOLDING, rojo]
├── FIN-SYS Tech [EMPRESA, cian]
│   ├── Equipo Backend [EQUIPO]
│   ├── Equipo Frontend [EQUIPO]
│   └── Módulo Trading [PROYECTO]
├── FIN-SYS Capital [EMPRESA, ámbar]
│   ├── Portafolio Pegasus [PROYECTO]
│   └── Portafolio Negocio A [PROYECTO]
└── FIN-SYS Consulting [EMPRESA, verde]
```

### Notas (5)
1. 🏗️ Arquitectura del Sistema (Andrés, pública)
2. 📊 KPIs Financieros Q2 Borrador (Valentina, **privada**)
3. 🛠️ Guía Técnica Módulo Trading (Camilo, pública)
4. 🎨 Design System Hub (Daniel, pública)
5. 📋 Agenda Semanal 9-13 Jun (Sofía, pública)

### Eventos Calendario (8)
- Sprint Review FIN-SYS OS (mañana, todos)
- Presentación KPIs Junta (pasado mañana, Andrés+Valentina)
- Sprint Planning Trading (3 días, Andrés+Camilo)
- Capacitación Project Hub (4 días, equipo completo)
- Auditoría Seguridad BD (1 semana)
- Renovación Contratos SaaS (10 días)
- **ALL DAY**: Deadline Informe Q2 Final (2 semanas)
- **ALL DAY**: Go-Live Producción Dokploy (45 días)


---

## Bug Fixes — Sesión 11 Jun 2026

### Overlay transparente bloqueante
- **Causa**: `CTTopBar.jsx` dejaba un `div fixed inset-0 z-40` al navegar de CT → APP
- **Fix**: `useEffect` cleanup en CTTopBar + eliminado `StrictMode` en `main.jsx`
- **Fix**: `ProjectHubApp` usa `position: relative` en vez de `fixed`
- **Fix**: `HubLoginRegister` usa `position: absolute` (contenida en su div padre)

### Workspace vacío en BD
- Detectado y eliminado workspace `"united bklu holdin"` sin datos
- `scripts/cleanup_empty_workspace.py` creado para este tipo de limpieza

### Race condition en notas
- `useProjectHub.js` ahora valida `user.id` antes de almacenar en localStorage
- Endpoint `/api/hub/notes` retorna HTTP 400 si `user_id` llega vacío

---

## Tipografía — Sesión 11 Jun 2026

Se creó `hub-typography.css` — sistema centralizado:
- Fuente base del hub: 13px (antes 11px)
- Labels mínimo: 12px (antes 10px)
- Badges/meta: 11px (antes 9–10px)
- Scrollbars personalizados para dark theme

**Importado en** `ProjectHubApp.jsx` vía `import './hub-typography.css'`
**Clase raíz**: `className="hub-root"` en el div principal

---

## Scripts de Mantenimiento

```bash
# Poblar BD con todos los datos sintéticos (desde cero)
python scripts/seed_hub.py

# Solo actualizar statuses de tareas existentes
python scripts/patch_task_statuses.py

# Eliminar workspaces vacíos de prueba
python scripts/cleanup_empty_workspace.py

# Health check del sistema completo
python scripts/health_check.py
```

---

## Reglas Zero-Impact — OBLIGATORIAS

| Archivo | Regla |
|---|---|
| `App.jsx` | ❌ NO modificar |
| `control-tower/*` | ❌ NO modificar |
| `database_driver.py` | ❌ NO modificar |
| `control_tower_driver.py` | ❌ NO modificar |
| `server.py` | ✅ Solo agregar al FINAL |
| `hub_driver.py` | ✅ Libre modificación (módulo 08) |
| `frontend/src/project-hub/` | ✅ Libre modificación |

---

## Identidad Visual

```css
/* Paleta Hub — NO usar en App.jsx o Control Tower */
--hub-bg:     #0a0a0a;
--hub-panel:  #111111;
--hub-accent: #0EA5E9;   /* cian sky */
--hub-green:  #10B981;
--hub-amber:  #F59E0B;
--hub-red:    #EF4444;
--hub-dim:    #64748b;
font-family: 'IBM Plex Mono', monospace;
font-size-base: 13px;    /* mínimo de legibilidad */
border: 2px solid;
border-radius: 0px;
```

---

## Estado del Módulo

| Fase | Componentes | Estado |
|---|---|---|
| FASE 1 — BD + Auth + Shell | 10 tablas, driver, login, workspace switcher | ✅ |
| FASE 2 — Task Board | Kanban drag-drop, Lista, TaskModal | ✅ |
| FASE 3 — Notes | NotesApp, NoteEditor BlockNote | ✅ |
| FASE 4 — Calendario | CalendarApp, EventModal, CSS override | ✅ |
| FASE 5 — Org + Métricas | EntityTree recursivo, MembersList, MemberProfile | ✅ |
| Datos sintéticos | 5 usuarios, 3 proyectos, 20 tareas, 5 notas, 8 eventos | ✅ |
| Bug fixes overlay | CTTopBar, StrictMode, positions | ✅ |
| Tipografía accesible | hub-typography.css, HubSidebar, HubTopBar escalados | ✅ |
| Build producción | 1314 módulos, 0 errores, 2.75s | ✅ |
| Health check | 5/5 ✅ | ✅ |
