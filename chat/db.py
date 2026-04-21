"""chat/db.py — CRUD projets, conversations, messages via pool centralisé."""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any
from uuid import UUID

from pool import get_conn


# ─── Projets ───────────────────────────────────────────────

def list_projects() -> list[dict]:
    """Liste tous les projets, triés par updated_at DESC, avec nombre de conversations."""
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT p.id, p.name, p.description, p.created_at, p.updated_at,
                       COUNT(c.id) AS conversation_count
                FROM chat_projects p
                LEFT JOIN chat_conversations c ON c.project_id = p.id
                GROUP BY p.id
                ORDER BY p.updated_at DESC
            """)
            cols = [d[0] for d in cur.description]
            return [dict(zip(cols, row)) for row in cur.fetchall()]


def create_project(name: str, description: str | None = None) -> dict:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO chat_projects (name, description) VALUES (%s, %s) RETURNING id, name, description, created_at, updated_at",
                (name, description),
            )
            cols = [d[0] for d in cur.description]
            return dict(zip(cols, cur.fetchone()))


def update_project(project_id: str, name: str | None = None, description: str | None = None) -> dict | None:
    sets, vals = [], []
    if name is not None:
        sets.append("name = %s")
        vals.append(name)
    if description is not None:
        sets.append("description = %s")
        vals.append(description)
    if not sets:
        return get_project(project_id)
    sets.append("updated_at = NOW()")
    vals.append(project_id)
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                f"UPDATE chat_projects SET {', '.join(sets)} WHERE id = %s RETURNING id, name, description, created_at, updated_at",
                vals,
            )
            row = cur.fetchone()
            if not row:
                return None
            cols = [d[0] for d in cur.description]
            return dict(zip(cols, row))


def get_project(project_id: str) -> dict | None:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id, name, description, created_at, updated_at FROM chat_projects WHERE id = %s", (project_id,))
            row = cur.fetchone()
            if not row:
                return None
            cols = [d[0] for d in cur.description]
            return dict(zip(cols, row))


def delete_project(project_id: str) -> bool:
    """Supprime un projet. Les conversations deviennent orphelines (SET NULL)."""
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM chat_projects WHERE id = %s", (project_id,))
            return cur.rowcount > 0


# ─── Conversations ─────────────────────────────────────────

def list_conversations(project_id: str | None = None, orphans_only: bool = False, limit: int = 50) -> list[dict]:
    """Liste les conversations. project_id=None + orphans_only=True = conversations libres."""
    with get_conn() as conn:
        with conn.cursor() as cur:
            if orphans_only:
                cur.execute("""
                    SELECT c.id, c.project_id, c.title, c.created_at, c.updated_at,
                           (SELECT COUNT(*) FROM chat_messages m WHERE m.conversation_id = c.id) AS message_count
                    FROM chat_conversations c
                    WHERE c.project_id IS NULL
                    ORDER BY c.updated_at DESC LIMIT %s
                """, (limit,))
            elif project_id:
                cur.execute("""
                    SELECT c.id, c.project_id, c.title, c.created_at, c.updated_at,
                           (SELECT COUNT(*) FROM chat_messages m WHERE m.conversation_id = c.id) AS message_count
                    FROM chat_conversations c
                    WHERE c.project_id = %s
                    ORDER BY c.updated_at DESC LIMIT %s
                """, (project_id, limit))
            else:
                cur.execute("""
                    SELECT c.id, c.project_id, c.title, c.created_at, c.updated_at,
                           (SELECT COUNT(*) FROM chat_messages m WHERE m.conversation_id = c.id) AS message_count
                    FROM chat_conversations c
                    ORDER BY c.updated_at DESC LIMIT %s
                """, (limit,))
            cols = [d[0] for d in cur.description]
            return [dict(zip(cols, row)) for row in cur.fetchall()]


def create_conversation(title: str = "Nouvelle conversation", project_id: str | None = None) -> dict:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO chat_conversations (title, project_id) VALUES (%s, %s) RETURNING id, project_id, title, created_at, updated_at",
                (title, project_id),
            )
            cols = [d[0] for d in cur.description]
            return dict(zip(cols, cur.fetchone()))


def update_conversation(conv_id: str, title: str | None = None, project_id: str | None = "UNSET") -> dict | None:
    sets, vals = [], []
    if title is not None:
        sets.append("title = %s")
        vals.append(title)
    if project_id != "UNSET":
        sets.append("project_id = %s")
        vals.append(project_id)
    if not sets:
        return get_conversation(conv_id)
    sets.append("updated_at = NOW()")
    vals.append(conv_id)
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                f"UPDATE chat_conversations SET {', '.join(sets)} WHERE id = %s RETURNING id, project_id, title, created_at, updated_at",
                vals,
            )
            row = cur.fetchone()
            if not row:
                return None
            cols = [d[0] for d in cur.description]
            return dict(zip(cols, row))


def get_conversation(conv_id: str) -> dict | None:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id, project_id, title, created_at, updated_at FROM chat_conversations WHERE id = %s", (conv_id,))
            row = cur.fetchone()
            if not row:
                return None
            cols = [d[0] for d in cur.description]
            return dict(zip(cols, row))


def delete_conversation(conv_id: str) -> bool:
    """Supprime une conversation et tous ses messages (CASCADE)."""
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM chat_conversations WHERE id = %s", (conv_id,))
            return cur.rowcount > 0


# ─── Messages ──────────────────────────────────────────────

def list_messages(conversation_id: str, limit: int = 200, offset: int = 0) -> list[dict]:
    """Messages d'une conversation, triés chronologiquement."""
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id, conversation_id, role, content, metadata, created_at
                FROM chat_messages
                WHERE conversation_id = %s
                ORDER BY created_at ASC
                LIMIT %s OFFSET %s
            """, (conversation_id, limit, offset))
            cols = [d[0] for d in cur.description]
            return [dict(zip(cols, row)) for row in cur.fetchall()]


def add_message(conversation_id: str, role: str, content: str, metadata: dict | None = None) -> dict:
    """Ajoute un message et met a jour updated_at de la conversation."""
    meta_json = json.dumps(metadata or {})
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO chat_messages (conversation_id, role, content, metadata) VALUES (%s, %s, %s, %s) RETURNING id, conversation_id, role, content, metadata, created_at",
                (conversation_id, role, content, meta_json),
            )
            cols = [d[0] for d in cur.description]
            msg = dict(zip(cols, cur.fetchone()))
            # Touch conversation updated_at
            cur.execute("UPDATE chat_conversations SET updated_at = NOW() WHERE id = %s", (conversation_id,))
            return msg


def auto_title(conversation_id: str) -> str | None:
    """Genere un titre a partir du premier message user (50 premiers chars)."""
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT content FROM chat_messages
                WHERE conversation_id = %s AND role = 'user'
                ORDER BY created_at ASC LIMIT 1
            """, (conversation_id,))
            row = cur.fetchone()
            if not row:
                return None
            title = row[0][:50].strip()
            if len(row[0]) > 50:
                title += "..."
            cur.execute(
                "UPDATE chat_conversations SET title = %s, updated_at = NOW() WHERE id = %s",
                (title, conversation_id),
            )
            return title
