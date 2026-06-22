"""
hr_documents_driver.py — CRUD para documentos y carpetas RRHH (Fase 2)
=======================================================================
Gestiona:
  - hr_folders    → árbol de carpetas por workspace
  - hr_documents  → metadatos de archivos (la URL viene de Supabase Storage)

El archivo real se sube directamente desde el frontend usando la
Supabase JS client (URL firmada). Este driver solo maneja metadatos.
"""

import os
import psycopg2
import psycopg2.extras


def _get_conn():
    return psycopg2.connect(
        host=os.getenv("DB_HOST"),
        database=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        port=os.getenv("DB_PORT", "5432"),
        cursor_factory=psycopg2.extras.RealDictCursor,
    )


# ─── CARPETAS ─────────────────────────────────────────────────────────────────

def get_folders(workspace_id: str) -> list:
    """Lista todas las carpetas del workspace en árbol plano."""
    with _get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """SELECT id, name, parent_id, color, created_by,
                          created_at::text
                   FROM hr_folders
                   WHERE workspace_id = %s
                   ORDER BY name""",
                (workspace_id,)
            )
            return [dict(r) for r in cur.fetchall()]


def create_folder(workspace_id: str, name: str,
                  parent_id: str = None, color: str = '#64748b',
                  created_by: str = None) -> dict:
    with _get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """INSERT INTO hr_folders (workspace_id, name, parent_id, color, created_by)
                   VALUES (%s, %s, %s, %s, %s) RETURNING *""",
                (workspace_id, name, parent_id, color, created_by)
            )
            conn.commit()
            return dict(cur.fetchone())


def delete_folder(folder_id: str, workspace_id: str) -> bool:
    """Borra la carpeta (y en cascada sus subcarpetas por FK)."""
    with _get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "DELETE FROM hr_folders WHERE id = %s AND workspace_id = %s",
                (folder_id, workspace_id)
            )
            conn.commit()
            return cur.rowcount > 0


def rename_folder(folder_id: str, name: str, color: str = None) -> dict:
    with _get_conn() as conn:
        with conn.cursor() as cur:
            if color:
                cur.execute(
                    "UPDATE hr_folders SET name = %s, color = %s WHERE id = %s RETURNING *",
                    (name, color, folder_id)
                )
            else:
                cur.execute(
                    "UPDATE hr_folders SET name = %s WHERE id = %s RETURNING *",
                    (name, folder_id)
                )
            conn.commit()
            row = cur.fetchone()
            return dict(row) if row else {}


# ─── DOCUMENTOS ────────────────────────────────────────────────────────────────

def get_documents(user_id: str, workspace_id: str,
                  folder_id: str = None, category: str = None) -> list:
    """Lista documentos del trabajador, opcionalmente filtrados."""
    conditions = ["user_id = %s", "workspace_id = %s"]
    params = [user_id, workspace_id]

    if folder_id:
        conditions.append("folder_id = %s")
        params.append(folder_id)
    if category:
        conditions.append("category = %s")
        params.append(category)

    where = " AND ".join(conditions)
    with _get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                f"""SELECT id, file_name, file_url, file_size, mime_type,
                           category, folder_id, description,
                           created_at::text, uploaded_by
                    FROM hr_documents WHERE {where}
                    ORDER BY created_at DESC""",
                params
            )
            return [dict(r) for r in cur.fetchall()]


def save_document_metadata(user_id: str, workspace_id: str,
                           file_name: str, file_url: str,
                           file_size: int = 0, mime_type: str = None,
                           category: str = 'general', folder_id: str = None,
                           description: str = None,
                           uploaded_by: str = None) -> dict:
    """Guarda el registro de metadatos después de subir el archivo al storage."""
    with _get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """INSERT INTO hr_documents
                   (user_id, workspace_id, folder_id, file_name, file_url,
                    file_size, mime_type, category, description, uploaded_by)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                   RETURNING *""",
                (user_id, workspace_id, folder_id, file_name, file_url,
                 file_size, mime_type, category, description, uploaded_by)
            )
            conn.commit()
            return dict(cur.fetchone())


def delete_document(doc_id: str, user_id: str) -> bool:
    """Borra el metadato (el archivo en storage debe borrarse desde el frontend)."""
    with _get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "DELETE FROM hr_documents WHERE id = %s AND user_id = %s",
                (doc_id, user_id)
            )
            conn.commit()
            return cur.rowcount > 0


def update_document(doc_id: str, data: dict) -> dict:
    """Actualiza categoría, descripción o carpeta de un documento."""
    allowed = {"category", "description", "folder_id", "file_name"}
    fields = {k: v for k, v in data.items() if k in allowed}
    if not fields:
        return {}
    set_clause = ", ".join(f"{k} = %s" for k in fields)
    with _get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                f"UPDATE hr_documents SET {set_clause} WHERE id = %s RETURNING *",
                list(fields.values()) + [doc_id]
            )
            conn.commit()
            row = cur.fetchone()
            return dict(row) if row else {}
