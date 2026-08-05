"""Lakebase data-access layer using a secret-backed PostgreSQL URL."""

from __future__ import annotations

import os
from contextlib import contextmanager
from typing import Any, Iterator

import psycopg
from psycopg import sql
from psycopg.conninfo import conninfo_to_dict
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

SCHEMA_NAME = os.getenv("SUPPORT_SCHEMA", "support_app")
ALLOWED_STATUSES = ("open", "in_progress", "resolved")
ALLOWED_PRIORITIES = ("low", "medium", "high")

_pool: ConnectionPool | None = None


def _lakebase_url() -> str:
    """Return the Lakebase URL injected from a Databricks secret resource."""
    value = os.getenv("LAKEBASE_URL", "").strip()
    if not value:
        raise RuntimeError(
            "LAKEBASE_URL is missing. Add the Databricks secret containing the "
            "Lakebase PostgreSQL URL as an App resource with key "
            "'lakebase_url_secret', then redeploy."
        )

    if not value.startswith(("postgresql://", "postgres://")):
        raise RuntimeError(
            "LAKEBASE_URL must be a PostgreSQL connection URL beginning with "
            "postgresql:// or postgres://."
        )

    try:
        parsed = conninfo_to_dict(value)
    except Exception as exc:
        raise RuntimeError("LAKEBASE_URL is not a valid PostgreSQL connection URL.") from exc

    required = ("host", "dbname", "user", "password")
    missing = [name for name in required if not parsed.get(name)]
    if missing:
        raise RuntimeError(
            "LAKEBASE_URL is missing required component(s): " + ", ".join(missing)
        )

    return value


def get_pool() -> ConnectionPool:
    """Return a process-wide pool connected with the secret Lakebase URL."""
    global _pool

    if _pool is None:
        _pool = ConnectionPool(
            conninfo=_lakebase_url(),
            min_size=1,
            max_size=8,
            max_idle=300,
            timeout=30,
            open=False,
        )
        _pool.open(wait=True, timeout=30)

    return _pool


@contextmanager
def _cursor(*, dictionaries: bool = False) -> Iterator[psycopg.Cursor]:
    """Yield a cursor with this application's schema first in search_path."""
    pool = get_pool()
    with pool.connection() as conn:
        factory = dict_row if dictionaries else None
        with conn.cursor(row_factory=factory) as cur:
            cur.execute(
                sql.SQL("SET search_path TO {}, public").format(
                    sql.Identifier(SCHEMA_NAME)
                )
            )
            yield cur


def initialize_database() -> None:
    """Create schema/tables and insert sample data exactly once."""
    pool = get_pool()
    with pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                sql.SQL("CREATE SCHEMA IF NOT EXISTS {}").format(
                    sql.Identifier(SCHEMA_NAME)
                )
            )
            cur.execute(
                sql.SQL("SET search_path TO {}, public").format(
                    sql.Identifier(SCHEMA_NAME)
                )
            )

            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS app_metadata (
                    metadata_key TEXT PRIMARY KEY,
                    metadata_value TEXT NOT NULL,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )

            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS tickets (
                    ticket_id BIGSERIAL PRIMARY KEY,
                    title VARCHAR(200) NOT NULL,
                    description TEXT,
                    status VARCHAR(20) NOT NULL DEFAULT 'open'
                        CHECK (status IN ('open', 'in_progress', 'resolved')),
                    priority VARCHAR(10) NOT NULL DEFAULT 'medium'
                        CHECK (priority IN ('low', 'medium', 'high')),
                    category VARCHAR(50) NOT NULL DEFAULT 'general',
                    created_by VARCHAR(100) NOT NULL,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )

            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS ticket_messages (
                    message_id BIGSERIAL PRIMARY KEY,
                    ticket_id BIGINT NOT NULL,
                    message_text TEXT NOT NULL,
                    author VARCHAR(100) NOT NULL,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    CONSTRAINT fk_ticket_messages_ticket
                        FOREIGN KEY (ticket_id)
                        REFERENCES tickets(ticket_id)
                        ON DELETE CASCADE
                )
                """
            )

            cur.execute(
                "CREATE INDEX IF NOT EXISTS idx_tickets_status ON tickets(status)"
            )
            cur.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_ticket_messages_ticket_id
                ON ticket_messages(ticket_id, created_at)
                """
            )

            cur.execute(
                """
                INSERT INTO app_metadata (metadata_key, metadata_value)
                VALUES ('sample_data_seeded', 'true')
                ON CONFLICT (metadata_key) DO NOTHING
                RETURNING metadata_key
                """
            )
            should_seed = cur.fetchone() is not None

            if should_seed:
                sample_tickets = [
                    (
                        "Unable to reset account password",
                        "The password reset link expires before it can be used.",
                        "open",
                        "high",
                        "account",
                        "Avery Chen",
                    ),
                    (
                        "VPN connection drops repeatedly",
                        "The corporate VPN disconnects several times each hour.",
                        "in_progress",
                        "medium",
                        "network",
                        "Jordan Lee",
                    ),
                    (
                        "Request access to finance dashboard",
                        "Read-only access is needed for monthly reporting.",
                        "resolved",
                        "low",
                        "access",
                        "Morgan Patel",
                    ),
                ]

                ticket_ids: list[int] = []
                for record in sample_tickets:
                    cur.execute(
                        """
                        INSERT INTO tickets
                            (title, description, status, priority, category, created_by)
                        VALUES (%s, %s, %s, %s, %s, %s)
                        RETURNING ticket_id
                        """,
                        record,
                    )
                    ticket_ids.append(cur.fetchone()[0])

                sample_messages = [
                    (
                        ticket_ids[0],
                        "I tried two reset links, but both showed an expired-link message.",
                        "Avery Chen",
                    ),
                    (
                        ticket_ids[0],
                        "Support is reviewing the identity-provider logs.",
                        "Casey Support",
                    ),
                    (
                        ticket_ids[1],
                        "The issue happens on both Wi-Fi and a wired connection.",
                        "Jordan Lee",
                    ),
                    (
                        ticket_ids[1],
                        "Network diagnostics were collected and assigned to the VPN team.",
                        "Riley Support",
                    ),
                    (
                        ticket_ids[2],
                        "Manager approval was attached to the access request.",
                        "Morgan Patel",
                    ),
                    (
                        ticket_ids[2],
                        "Read-only dashboard access was granted and verified.",
                        "Taylor Support",
                    ),
                ]
                cur.executemany(
                    """
                    INSERT INTO ticket_messages (ticket_id, message_text, author)
                    VALUES (%s, %s, %s)
                    """,
                    sample_messages,
                )


def list_tickets(statuses: list[str] | None = None) -> list[dict[str, Any]]:
    query = """
        SELECT
            t.ticket_id,
            t.title,
            t.description,
            t.status,
            t.priority,
            t.category,
            t.created_by,
            t.created_at,
            t.updated_at,
            COUNT(m.message_id)::INT AS message_count
        FROM tickets t
        LEFT JOIN ticket_messages m ON m.ticket_id = t.ticket_id
    """
    params: list[Any] = []

    if statuses:
        invalid = set(statuses) - set(ALLOWED_STATUSES)
        if invalid:
            raise ValueError(f"Invalid status filter: {sorted(invalid)}")
        query += " WHERE t.status = ANY(%s)"
        params.append(statuses)

    query += """
        GROUP BY t.ticket_id
        ORDER BY
            CASE t.priority WHEN 'high' THEN 1 WHEN 'medium' THEN 2 ELSE 3 END,
            t.updated_at DESC,
            t.ticket_id DESC
    """

    with _cursor(dictionaries=True) as cur:
        cur.execute(query, params)
        return list(cur.fetchall())


def get_ticket(ticket_id: int) -> dict[str, Any] | None:
    with _cursor(dictionaries=True) as cur:
        cur.execute(
            """
            SELECT ticket_id, title, description, status, priority, category,
                   created_by, created_at, updated_at
            FROM tickets
            WHERE ticket_id = %s
            """,
            (ticket_id,),
        )
        return cur.fetchone()


def get_messages(ticket_id: int) -> list[dict[str, Any]]:
    with _cursor(dictionaries=True) as cur:
        cur.execute(
            """
            SELECT message_id, ticket_id, message_text, author, created_at
            FROM ticket_messages
            WHERE ticket_id = %s
            ORDER BY created_at, message_id
            """,
            (ticket_id,),
        )
        return list(cur.fetchall())


def create_ticket(
    *,
    title: str,
    created_by: str,
    description: str = "",
    priority: str = "medium",
    category: str = "general",
) -> int:
    title = title.strip()
    created_by = created_by.strip()
    description = description.strip()
    category = category.strip().lower() or "general"

    if not title:
        raise ValueError("Title is required.")
    if len(title) > 200:
        raise ValueError("Title must be 200 characters or fewer.")
    if not created_by:
        raise ValueError("Created by is required.")
    if len(created_by) > 100:
        raise ValueError("Created by must be 100 characters or fewer.")
    if priority not in ALLOWED_PRIORITIES:
        raise ValueError("Priority must be low, medium, or high.")
    if len(category) > 50:
        raise ValueError("Category must be 50 characters or fewer.")

    with _cursor() as cur:
        cur.execute(
            """
            INSERT INTO tickets
                (title, description, status, priority, category, created_by)
            VALUES (%s, %s, 'open', %s, %s, %s)
            RETURNING ticket_id
            """,
            (title, description or None, priority, category, created_by),
        )
        return int(cur.fetchone()[0])


def add_message(*, ticket_id: int, message_text: str, author: str) -> int:
    message_text = message_text.strip()
    author = author.strip()

    if not message_text:
        raise ValueError("Message text is required.")
    if len(message_text) > 5000:
        raise ValueError("Message must be 5,000 characters or fewer.")
    if not author:
        raise ValueError("Author is required.")
    if len(author) > 100:
        raise ValueError("Author must be 100 characters or fewer.")

    with _cursor() as cur:
        cur.execute("SELECT 1 FROM tickets WHERE ticket_id = %s", (ticket_id,))
        if cur.fetchone() is None:
            raise ValueError("The selected ticket no longer exists.")

        cur.execute(
            """
            INSERT INTO ticket_messages (ticket_id, message_text, author)
            VALUES (%s, %s, %s)
            RETURNING message_id
            """,
            (ticket_id, message_text, author),
        )
        message_id = int(cur.fetchone()[0])
        cur.execute(
            "UPDATE tickets SET updated_at = CURRENT_TIMESTAMP WHERE ticket_id = %s",
            (ticket_id,),
        )
        return message_id


def update_ticket_status(*, ticket_id: int, status: str) -> None:
    if status not in ALLOWED_STATUSES:
        raise ValueError("Status must be open, in_progress, or resolved.")

    with _cursor() as cur:
        cur.execute(
            """
            UPDATE tickets
            SET status = %s, updated_at = CURRENT_TIMESTAMP
            WHERE ticket_id = %s
            """,
            (status, ticket_id),
        )
        if cur.rowcount != 1:
            raise ValueError("The selected ticket no longer exists.")


def delete_ticket(ticket_id: int) -> None:
    with _cursor() as cur:
        cur.execute("DELETE FROM tickets WHERE ticket_id = %s", (ticket_id,))
        if cur.rowcount != 1:
            raise ValueError("The selected ticket no longer exists.")


def ticket_statistics() -> dict[str, int]:
    with _cursor(dictionaries=True) as cur:
        cur.execute(
            """
            SELECT
                COUNT(*)::INT AS total,
                COUNT(*) FILTER (WHERE status = 'open')::INT AS open,
                COUNT(*) FILTER (WHERE status = 'in_progress')::INT AS in_progress,
                COUNT(*) FILTER (WHERE status = 'resolved')::INT AS resolved,
                COUNT(*) FILTER (WHERE priority = 'high')::INT AS high_priority
            FROM tickets
            """
        )
        row = cur.fetchone()
        return dict(row) if row else {
            "total": 0,
            "open": 0,
            "in_progress": 0,
            "resolved": 0,
            "high_priority": 0,
        }
