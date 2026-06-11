# Plan de Implementacion — Project Hub (Modulo 08)
Dashboard de Colaboracion Multi-Tenant: Tareas + Notas Notion + Calendario + Jerarquia Organizacional
Fecha: 10 Junio 2026 | Estado: PENDIENTE APROBACION

---

## Resumen de Decisiones (Confirmadas)

| Pregunta | Decision |
|---|---|
| Relacion con CT | Completamente independiente — nueva app separada |
| Vista de tareas | Kanban + Lista (alternar con toggle) |
| Editor de notas | Bloques tipo Notion (texto, imagenes, tablas, checklists, codigo) |
| Vista calendario | Mensual + Semanal + Agenda + Linea de tiempo (Gantt) |
| Jerarquia | Flexible — el superusuario define niveles sin limite fijo |
| Multi-org switching | Si — usuarios con permisos ven multiples organizaciones |
| Ubicacion | Pestana nueva: [APP] [TEST COA] [CT] [PROJECT HUB] |

---

## Descripcion de Features

### 1. Task Board
- Kanban: Por Hacer / En Progreso / En Revision / Completado (drag-and-drop con dnd-kit)
- Vista Lista: tabla sorteable y filtrable
- Tarjeta: titulo, asignados (avatares), prioridad (color lateral), deadline urgente
- Metricas: tiempo promedio de completado por usuario
- Biblioteca: dnd-kit (@dnd-kit/core + @dnd-kit/sortable)

### 2. Notes — Editor Tipo Notion
- Bloques: texto, H1-H3, listas, checklists, tablas, codigo, imagenes, embeds
- Subida de imagenes a Supabase Storage (bucket: hub-images)
- Privadas por defecto, opcion de compartir con el equipo
- Biblioteca: @blocknote/react + @blocknote/mantine

### 3. Calendar — Multi-Usuario
- Vista mensual, semanal, agenda y Gantt (tareas + eventos juntos)
- Cada usuario tiene su propio color en el calendario compartido
- Crear eventos y asignarlos a multiples usuarios
- Biblioteca: react-big-calendar

### 4. Multi-Tenant Jerarquico
- Registro de organizacion: nombre, NIT, logo, descripcion
- Registro de usuario: nombres, cedula, foto, rol, descripcion
- Arbol de entidades sin limite de niveles (auto-referencial)
- Workspace Switcher tipo Slack en esquina superior izquierda
- Superusuario: acceso a todos los workspaces

---

## Open Questions (Requieren Respuesta)

1. ROLES: Propongo owner / admin / member / viewer. OK o necesitas roles custom?
2. NOTAS: Propongo privadas + compartidas (wiki de equipo). Correcto?
3. CONEXION CONTABLE: Asumo que las tareas del Hub son INDEPENDIENTES de las transacciones contables. Correcto?

---

## Stack Tecnologico

| Feature | Libreria |
|---|---|
| Drag-Drop Kanban | dnd-kit |
| Editor de Bloques | @blocknote/react + @blocknote/mantine |
| Calendario | react-big-calendar |
| Estado global | zustand |
| Server state | @tanstack/react-query |
| Realtime | Supabase Realtime (Postgres Changes) |
| Imagenes | Supabase Storage (bucket: hub-images) |

Paleta Visual (nueva identidad):
  - Fondo: #0a0a0a
  - Acento: #0EA5E9 (cian — diferente al ambar del CT y al negro/blanco del APP)
  - Bordes: 2px solid brutalista
  - Fuente: IBM Plex Mono

---

## Nuevas Tablas en Supabase (NO alteran las existentes)

Todas con prefijo hub_ para evitar colisiones:

hub_workspaces        — Organizaciones/workspaces
hub_users             — Usuarios con perfil completo (nombre, cedula, foto, descripcion)
hub_workspace_members — Relacion usuario-workspace con rol
hub_entities          — Arbol jerarquico flexible (parent_id auto-referencial)
hub_projects          — Proyectos dentro de una entidad
hub_tasks             — Tareas con estado, prioridad, deadline
hub_task_assignees    — N:N tarea-usuario
hub_notes             — Notas con contenido JSONB (BlockNote)
hub_events            — Eventos de calendario
hub_event_attendees   — N:N evento-usuario

---

## Archivos a Crear (NUEVOS — Zero-Impact)

fin_sys_core/hub_driver.py        — Driver Python CRUD para las 10 tablas hub_*

frontend/src/project-hub/
  ProjectHubApp.jsx               — Raiz del modulo
  hooks/useProjectHub.js          — Estado global del hub
  hooks/useWorkspace.js           — Workspace activo y switcher
  components/HubTopBar.jsx        — Barra superior con workspace switcher
  components/HubLoginRegister.jsx — Login/Registro de hub_users
  components/HubSidebar.jsx       — Arbol de entidades + navegacion
  components/WorkspaceSwitcher.jsx— Selector tipo Slack
  features/tasks/TaskBoard.jsx    — Kanban + Lista con toggle
  features/tasks/KanbanView.jsx   — Columnas drag-and-drop
  features/tasks/ListView.jsx     — Tabla sorteable
  features/tasks/TaskCard.jsx     — Tarjeta con avatares y prioridad
  features/tasks/TaskModal.jsx    — Modal detalle/edicion
  features/notes/NotesApp.jsx     — Lista de notas
  features/notes/NoteEditor.jsx   — BlockNote con image upload
  features/calendar/CalendarApp.jsx — Vistas mensual/semanal/agenda/gantt
  features/calendar/EventModal.jsx  — Crear evento con asistentes
  features/members/MembersList.jsx  — Miembros del workspace
  features/members/MemberProfile.jsx— Perfil y metricas
  features/settings/EntityTree.jsx  — Arbol jerarquico editable

---

## Solo se Modifica (Existentes)

server.py      — Bloque nuevo al FINAL con /api/hub/* (19 endpoints)
main.jsx       — +1 boton [PROJECT HUB] en la barra de navegacion

INTACTOS (Zero-Impact garantizado):
  App.jsx
  control-tower/*
  database_driver.py
  control_tower_driver.py
  Tablas existentes en Supabase

---

## Fases de Implementacion

FASE 1 — Infraestructura Base
  - 10 tablas hub_* en Supabase via MCP
  - hub_driver.py
  - Endpoints /api/hub/workspaces, /api/hub/users/*
  - Shell: login, topbar, sidebar, workspace switcher
  - Boton PROJECT HUB en main.jsx

FASE 2 — Task Board
  - Endpoints de tareas
  - KanbanView (dnd-kit) + ListView
  - TaskCard, TaskModal con multiselect de asignados

FASE 3 — Notes (BlockNote)
  - Instalar @blocknote/react
  - NoteEditor con upload a Supabase Storage
  - NotesApp con privadas/compartidas

FASE 4 — Calendario
  - Instalar react-big-calendar
  - CalendarApp con todas las vistas
  - EventModal con asistentes
  - Vista Gantt/timeline

FASE 5 — Jerarquia + Metricas
  - EntityTree editable
  - Filtrado por entidad/org
  - Metricas de usuario (tiempo completado)
  - MemberProfile con historial

---

## Verificacion tras cada Fase

python scripts/health_check.py   -> 5/5 OK (modulos existentes intactos)
python fin_sys_core/test_core.py -> 5/5 OK
