"""
hub_driver.py — Driver para el Project Hub (Módulo 08)
Maneja operaciones CRUD para las 10 tablas hub_*
Zero-Impact: No modifica database_driver.py ni control_tower_driver.py
"""
import os
import hashlib
import uuid
from datetime import datetime, timezone
import psycopg2
import psycopg2.extras

# ─── Conexión (reutiliza las mismas variables de entorno que el proyecto) ──────
def _get_conn():
    return psycopg2.connect(
        host=os.environ.get("DB_HOST"),
        port=int(os.environ.get("DB_PORT", 5432)),
        dbname=os.environ.get("DB_NAME"),
        user=os.environ.get("DB_USER"),
        password=os.environ.get("DB_PASSWORD"),
        sslmode="require",
        cursor_factory=psycopg2.extras.RealDictCursor
    )

def _hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


# ══════════════════════════════════════════════════════════════════════════════
# WORKSPACES
# ══════════════════════════════════════════════════════════════════════════════

def create_workspace(name: str, nit: str = None, logo_url: str = None) -> dict:
    """Crea una nueva organización/workspace."""
    slug = name.lower().replace(" ", "-").replace("/", "-")[:50]
    # Asegurar slug único
    slug = f"{slug}-{str(uuid.uuid4())[:8]}"
    conn = _get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO hub_workspaces (slug, name, nit, logo_url)
                VALUES (%s, %s, %s, %s)
                RETURNING *
            """, (slug, name, nit, logo_url))
            row = cur.fetchone()
            conn.commit()
            return dict(row)
    finally:
        conn.close()


def get_workspaces_for_user(user_id: str) -> list:
    """Devuelve todos los workspaces a los que pertenece un usuario."""
    conn = _get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT w.*,
                       wm.role AS member_role
                FROM hub_workspaces w
                JOIN hub_workspace_members wm ON wm.workspace_id = w.id
                WHERE wm.user_id = %s
                ORDER BY w.created_at ASC
            """, (user_id,))
            return [dict(r) for r in cur.fetchall()]
    finally:
        conn.close()


def get_all_workspaces() -> list:
    """Solo para superusuarios — devuelve todos los workspaces."""
    conn = _get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM hub_workspaces ORDER BY created_at ASC")
            return [dict(r) for r in cur.fetchall()]
    finally:
        conn.close()


# ══════════════════════════════════════════════════════════════════════════════
# USERS
# ══════════════════════════════════════════════════════════════════════════════

# Paleta de colores para avatares de usuarios
AVATAR_COLORS = [
    "#0EA5E9", "#8B5CF6", "#10B981", "#F59E0B",
    "#EF4444", "#EC4899", "#6366F1", "#14B8A6"
]

def register_user(email: str, password: str, name: str, cedula: str = None,
                  description: str = None, workspace_id: str = None,
                  role: str = "member") -> dict:
    """Registra un nuevo usuario y opcionalmente lo une a un workspace."""
    conn = _get_conn()
    try:
        with conn.cursor() as cur:
            # Verificar email único
            cur.execute("SELECT id FROM hub_users WHERE email = %s", (email,))
            if cur.fetchone():
                raise ValueError("El email ya está registrado")

            # Asignar color de avatar automáticamente
            cur.execute("SELECT COUNT(*) as cnt FROM hub_users")
            count = cur.fetchone()["cnt"]
            color = AVATAR_COLORS[count % len(AVATAR_COLORS)]

            cur.execute("""
                INSERT INTO hub_users
                  (email, password_hash, name, cedula, description, color, role)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                RETURNING id, email, name, cedula, color, role, description,
                          is_superuser, avatar_url, created_at
            """, (email, _hash_password(password), name, cedula, description, color, role))
            user = dict(cur.fetchone())

            # Unir al workspace si se proporcionó
            if workspace_id:
                cur.execute("""
                    INSERT INTO hub_workspace_members (workspace_id, user_id, role)
                    VALUES (%s, %s, %s)
                    ON CONFLICT DO NOTHING
                """, (workspace_id, user["id"], role))

            conn.commit()
            return user
    finally:
        conn.close()


def login_user(email: str, password: str) -> dict | None:
    """Autentica un usuario. Devuelve los datos del usuario o None."""
    conn = _get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id, email, name, cedula, color, role, description,
                       is_superuser, avatar_url, created_at
                FROM hub_users
                WHERE email = %s AND password_hash = %s
            """, (email, _hash_password(password)))
            row = cur.fetchone()
            return dict(row) if row else None
    finally:
        conn.close()


def get_workspace_members(workspace_id: str) -> list:
    """Devuelve los miembros de un workspace con sus roles."""
    conn = _get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT u.id, u.name, u.email, u.cedula, u.color,
                       u.avatar_url, u.description, wm.role, wm.joined_at
                FROM hub_users u
                JOIN hub_workspace_members wm ON wm.user_id = u.id
                WHERE wm.workspace_id = %s
                ORDER BY wm.joined_at ASC
            """, (workspace_id,))
            return [dict(r) for r in cur.fetchall()]
    finally:
        conn.close()


def add_member_to_workspace(workspace_id: str, user_id: str, role: str = "member") -> dict:
    """Agrega un usuario a un workspace."""
    conn = _get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO hub_workspace_members (workspace_id, user_id, role)
                VALUES (%s, %s, %s)
                ON CONFLICT (workspace_id, user_id) DO UPDATE SET role = EXCLUDED.role
                RETURNING *
            """, (workspace_id, user_id, role))
            conn.commit()
            return dict(cur.fetchone())
    finally:
        conn.close()


# ══════════════════════════════════════════════════════════════════════════════
# ENTITIES (árbol jerárquico flexible)
# ══════════════════════════════════════════════════════════════════════════════

def get_entity_tree(workspace_id: str) -> list:
    """Devuelve el árbol de entidades con CTE recursivo."""
    conn = _get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                WITH RECURSIVE tree AS (
                    SELECT *, 0 AS depth, ARRAY[id] AS path
                    FROM hub_entities
                    WHERE workspace_id = %s AND parent_id IS NULL
                    UNION ALL
                    SELECT e.*, t.depth + 1, t.path || e.id
                    FROM hub_entities e
                    JOIN tree t ON e.parent_id = t.id
                    WHERE e.workspace_id = %s
                )
                SELECT * FROM tree ORDER BY path, position
            """, (workspace_id, workspace_id))
            return [dict(r) for r in cur.fetchall()]
    finally:
        conn.close()


def create_entity(workspace_id: str, name: str, entity_type: str = "CUSTOM",
                  parent_id: str = None, description: str = None,
                  color: str = "#0EA5E9") -> dict:
    conn = _get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO hub_entities (workspace_id, parent_id, name, type, description, color)
                VALUES (%s, %s, %s, %s, %s, %s)
                RETURNING *
            """, (workspace_id, parent_id, name, entity_type, description, color))
            conn.commit()
            return dict(cur.fetchone())
    finally:
        conn.close()


def delete_entity(entity_id: str) -> bool:
    conn = _get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM hub_entities WHERE id = %s", (entity_id,))
            conn.commit()
            return cur.rowcount > 0
    finally:
        conn.close()


# ══════════════════════════════════════════════════════════════════════════════
# PROJECTS
# ══════════════════════════════════════════════════════════════════════════════

def create_project(workspace_id: str, name: str, entity_id: str = None,
                   description: str = None, color: str = "#0EA5E9",
                   created_by: str = None) -> dict:
    conn = _get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO hub_projects (workspace_id, entity_id, name, description, color, created_by)
                VALUES (%s, %s, %s, %s, %s, %s)
                RETURNING *
            """, (workspace_id, entity_id, name, description, color, created_by))
            conn.commit()
            return dict(cur.fetchone())
    finally:
        conn.close()


def get_projects(workspace_id: str, entity_id: str = None) -> list:
    conn = _get_conn()
    try:
        with conn.cursor() as cur:
            if entity_id:
                cur.execute("""
                    SELECT p.*, u.name AS creator_name
                    FROM hub_projects p
                    LEFT JOIN hub_users u ON u.id = p.created_by
                    WHERE p.workspace_id = %s AND p.entity_id = %s
                    ORDER BY p.created_at ASC
                """, (workspace_id, entity_id))
            else:
                cur.execute("""
                    SELECT p.*, u.name AS creator_name
                    FROM hub_projects p
                    LEFT JOIN hub_users u ON u.id = p.created_by
                    WHERE p.workspace_id = %s
                    ORDER BY p.created_at ASC
                """, (workspace_id,))
            return [dict(r) for r in cur.fetchall()]
    finally:
        conn.close()


# ══════════════════════════════════════════════════════════════════════════════
# TASKS
# ══════════════════════════════════════════════════════════════════════════════

def get_tasks(project_id: str, status: str = None) -> list:
    """Devuelve tareas de un proyecto con sus asignados."""
    conn = _get_conn()
    try:
        with conn.cursor() as cur:
            query = """
                SELECT t.*,
                       COALESCE(
                         json_agg(
                           json_build_object(
                             'id', u.id, 'name', u.name,
                             'color', u.color, 'avatar_url', u.avatar_url
                           )
                         ) FILTER (WHERE u.id IS NOT NULL),
                         '[]'
                       ) AS assignees
                FROM hub_tasks t
                LEFT JOIN hub_task_assignees ta ON ta.task_id = t.id
                LEFT JOIN hub_users u ON u.id = ta.user_id
                WHERE t.project_id = %s
            """
            params = [project_id]
            if status:
                query += " AND t.status = %s"
                params.append(status)
            query += " GROUP BY t.id ORDER BY t.position ASC, t.created_at ASC"
            cur.execute(query, params)
            rows = cur.fetchall()
            result = []
            for r in rows:
                d = dict(r)
                if isinstance(d.get("assignees"), str):
                    import json
                    d["assignees"] = json.loads(d["assignees"])
                result.append(d)
            return result
    finally:
        conn.close()


def create_task(workspace_id: str, project_id: str, title: str,
                description: str = None, priority: str = "medium",
                due_date: str = None, created_by: str = None,
                assignee_ids: list = None) -> dict:
    conn = _get_conn()
    try:
        with conn.cursor() as cur:
            # Obtener la siguiente posición
            cur.execute(
                "SELECT COALESCE(MAX(position), -1) + 1 AS pos FROM hub_tasks WHERE project_id = %s",
                (project_id,)
            )
            position = cur.fetchone()["pos"]

            cur.execute("""
                INSERT INTO hub_tasks
                  (workspace_id, project_id, title, description, priority,
                   due_date, created_by, position)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING *
            """, (workspace_id, project_id, title, description, priority,
                  due_date, created_by, position))
            task = dict(cur.fetchone())

            # Asignar usuarios
            if assignee_ids:
                for uid in assignee_ids:
                    cur.execute("""
                        INSERT INTO hub_task_assignees (task_id, user_id)
                        VALUES (%s, %s) ON CONFLICT DO NOTHING
                    """, (task["id"], uid))

            conn.commit()
            task["assignees"] = assignee_ids or []
            return task
    finally:
        conn.close()


def update_task(task_id: str, **kwargs) -> dict:
    """Actualiza campos de una tarea (status, position, title, priority, etc.)."""
    conn = _get_conn()
    allowed = {"title", "description", "status", "priority", "due_date",
               "position", "started_at", "completed_at"}
    fields = {k: v for k, v in kwargs.items() if k in allowed}

    # Auto-set timestamps cuando cambia el status
    if fields.get("status") == "in_progress" and "started_at" not in fields:
        fields["started_at"] = datetime.now(timezone.utc).isoformat()
    if fields.get("status") == "done" and "completed_at" not in fields:
        fields["completed_at"] = datetime.now(timezone.utc).isoformat()

    try:
        with conn.cursor() as cur:
            if not fields:
                cur.execute("SELECT * FROM hub_tasks WHERE id = %s", (task_id,))
                return dict(cur.fetchone())

            set_clause = ", ".join(f"{k} = %s" for k in fields)
            values = list(fields.values()) + [task_id]
            cur.execute(f"""
                UPDATE hub_tasks SET {set_clause}
                WHERE id = %s RETURNING *
            """, values)

            # Actualizar asignados si se proporcionaron
            if "assignee_ids" in kwargs:
                cur.execute("DELETE FROM hub_task_assignees WHERE task_id = %s", (task_id,))
                for uid in kwargs["assignee_ids"]:
                    cur.execute("""
                        INSERT INTO hub_task_assignees (task_id, user_id)
                        VALUES (%s, %s) ON CONFLICT DO NOTHING
                    """, (task_id, uid))

            conn.commit()
            return dict(cur.fetchone()) if cur.rowcount else {}
    finally:
        conn.close()


def delete_task(task_id: str) -> bool:
    conn = _get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM hub_tasks WHERE id = %s", (task_id,))
            conn.commit()
            return cur.rowcount > 0
    finally:
        conn.close()


# ══════════════════════════════════════════════════════════════════════════════
# NOTES
# ══════════════════════════════════════════════════════════════════════════════

def get_notes(workspace_id: str, user_id: str) -> list:
    """Devuelve notas propias del usuario más las notas compartidas del workspace."""
    conn = _get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT n.*, u.name AS author_name, u.color AS author_color
                FROM hub_notes n
                JOIN hub_users u ON u.id = n.user_id
                WHERE n.workspace_id = %s
                  AND (n.user_id = %s OR n.is_private = false)
                ORDER BY n.updated_at DESC
            """, (workspace_id, user_id))
            return [dict(r) for r in cur.fetchall()]
    finally:
        conn.close()


def create_note(workspace_id: str, user_id: str, title: str = "Sin título",
                project_id: str = None) -> dict:
    conn = _get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO hub_notes (workspace_id, user_id, title, project_id)
                VALUES (%s, %s, %s, %s)
                RETURNING *
            """, (workspace_id, user_id, title, project_id))
            conn.commit()
            return dict(cur.fetchone())
    finally:
        conn.close()


def update_note(note_id: str, title: str = None, content=None,
                is_private: bool = None) -> dict:
    conn = _get_conn()
    try:
        with conn.cursor() as cur:
            import json as _json
            fields = {}
            if title is not None:
                fields["title"] = title
            if content is not None:
                fields["content"] = _json.dumps(content) if not isinstance(content, str) else content
            if is_private is not None:
                fields["is_private"] = is_private
            fields["updated_at"] = datetime.now(timezone.utc).isoformat()

            set_clause = ", ".join(f"{k} = %s" for k in fields)
            values = list(fields.values()) + [note_id]
            cur.execute(f"""
                UPDATE hub_notes SET {set_clause}
                WHERE id = %s RETURNING *
            """, values)
            conn.commit()
            return dict(cur.fetchone()) if cur.rowcount else {}
    finally:
        conn.close()


# ══════════════════════════════════════════════════════════════════════════════
# EVENTS / CALENDAR
# ══════════════════════════════════════════════════════════════════════════════

def get_events(workspace_id: str) -> list:
    """Devuelve todos los eventos del workspace con sus asistentes."""
    conn = _get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT e.*,
                       COALESCE(
                         json_agg(
                           json_build_object(
                             'id', u.id, 'name', u.name, 'color', u.color
                           )
                         ) FILTER (WHERE u.id IS NOT NULL),
                         '[]'
                       ) AS attendees
                FROM hub_events e
                LEFT JOIN hub_event_attendees ea ON ea.event_id = e.id
                LEFT JOIN hub_users u ON u.id = ea.user_id
                WHERE e.workspace_id = %s
                GROUP BY e.id
                ORDER BY e.start_time ASC
            """, (workspace_id,))
            rows = cur.fetchall()
            result = []
            for r in rows:
                d = dict(r)
                if isinstance(d.get("attendees"), str):
                    import json
                    d["attendees"] = json.loads(d["attendees"])
                result.append(d)
            return result
    finally:
        conn.close()


def create_event(workspace_id: str, title: str, start_time: str, end_time: str,
                 description: str = None, all_day: bool = False,
                 color: str = None, created_by: str = None,
                 project_id: str = None, attendee_ids: list = None) -> dict:
    conn = _get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO hub_events
                  (workspace_id, project_id, title, description,
                   start_time, end_time, all_day, color, created_by)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING *
            """, (workspace_id, project_id, title, description,
                  start_time, end_time, all_day, color, created_by))
            event = dict(cur.fetchone())

            if attendee_ids:
                for uid in attendee_ids:
                    cur.execute("""
                        INSERT INTO hub_event_attendees (event_id, user_id)
                        VALUES (%s, %s) ON CONFLICT DO NOTHING
                    """, (event["id"], uid))

            conn.commit()
            event["attendees"] = attendee_ids or []
            return event
    finally:
        conn.close()


def update_event(event_id: str, **kwargs) -> dict:
    conn = _get_conn()
    allowed = {"title", "description", "start_time", "end_time", "all_day", "color"}
    fields = {k: v for k, v in kwargs.items() if k in allowed}
    try:
        with conn.cursor() as cur:
            if fields:
                set_clause = ", ".join(f"{k} = %s" for k in fields)
                values = list(fields.values()) + [event_id]
                cur.execute(f"UPDATE hub_events SET {set_clause} WHERE id = %s RETURNING *", values)

            if "attendee_ids" in kwargs:
                cur.execute("DELETE FROM hub_event_attendees WHERE event_id = %s", (event_id,))
                for uid in kwargs["attendee_ids"]:
                    cur.execute("""
                        INSERT INTO hub_event_attendees (event_id, user_id)
                        VALUES (%s, %s) ON CONFLICT DO NOTHING
                    """, (event_id, uid))

            conn.commit()
            cur.execute("SELECT * FROM hub_events WHERE id = %s", (event_id,))
            return dict(cur.fetchone()) if cur.rowcount else {}
    finally:
        conn.close()


# ══════════════════════════════════════════════════════════════════════════════
# MÉTRICAS
# ══════════════════════════════════════════════════════════════════════════════

def get_user_metrics(workspace_id: str) -> list:
    """Métricas de rendimiento por usuario: tareas completadas, tiempo promedio, etc."""
    conn = _get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT
                    u.id, u.name, u.color, u.avatar_url,
                    COUNT(t.id) FILTER (WHERE t.status = 'done')         AS tasks_done,
                    COUNT(t.id) FILTER (WHERE t.status != 'done')        AS tasks_pending,
                    COUNT(t.id) FILTER (WHERE t.due_date < NOW()::DATE
                                         AND t.status != 'done')        AS tasks_overdue,
                    AVG(
                      EXTRACT(EPOCH FROM (t.completed_at - t.started_at)) / 3600
                    ) FILTER (WHERE t.completed_at IS NOT NULL
                              AND t.started_at IS NOT NULL)              AS avg_hours_to_complete
                FROM hub_users u
                JOIN hub_workspace_members wm ON wm.user_id = u.id
                LEFT JOIN hub_task_assignees ta ON ta.user_id = u.id
                LEFT JOIN hub_tasks t ON t.id = ta.task_id
                                     AND t.workspace_id = %s
                WHERE wm.workspace_id = %s
                GROUP BY u.id, u.name, u.color, u.avatar_url
                ORDER BY tasks_done DESC
            """, (workspace_id, workspace_id))
            return [dict(r) for r in cur.fetchall()]
    finally:
        conn.close()
