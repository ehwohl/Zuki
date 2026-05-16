"""
indexer.py — SQLite index for Google Drive files
──────────────────────────────────────────────────
DB location: memory/office_index.db  (gitignored)

Schema:
  files(id, name, mime_type, client, category, summary, web_link, modified_at, indexed_at)

Categories: Rechnung, Vertrag, Bericht, Angebot, Sonstiges

Log marker: [INDEX]
"""

import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from core.logger import get_logger

log = get_logger("office.indexer")

_ROOT    = Path(__file__).resolve().parent.parent.parent
_DB_PATH = _ROOT / "memory" / "office_index.db"

_DDL = """
CREATE TABLE IF NOT EXISTS files (
    id          TEXT PRIMARY KEY,
    name        TEXT NOT NULL,
    mime_type   TEXT,
    client      TEXT,
    category    TEXT,
    summary     TEXT,
    web_link    TEXT,
    modified_at TEXT,
    indexed_at  TEXT
);
CREATE INDEX IF NOT EXISTS idx_client   ON files(client);
CREATE INDEX IF NOT EXISTS idx_category ON files(category);
"""


def _conn() -> sqlite3.Connection:
    _DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(str(_DB_PATH))
    con.row_factory = sqlite3.Row
    return con


def init_db() -> None:
    with _conn() as con:
        con.executescript(_DDL)
    log.debug("[INDEX] Datenbank bereit: %s", _DB_PATH)


def upsert(file: dict) -> None:
    """Insert or update a single file record."""
    with _conn() as con:
        con.execute(
            """
            INSERT INTO files
                (id, name, mime_type, client, category, summary, web_link, modified_at, indexed_at)
            VALUES
                (:id, :name, :mime_type, :client, :category, :summary, :web_link, :modified_at, :indexed_at)
            ON CONFLICT(id) DO UPDATE SET
                name        = excluded.name,
                mime_type   = excluded.mime_type,
                client      = excluded.client,
                category    = excluded.category,
                summary     = excluded.summary,
                web_link    = excluded.web_link,
                modified_at = excluded.modified_at,
                indexed_at  = excluded.indexed_at
            """,
            {
                "id":          file["id"],
                "name":        file["name"],
                "mime_type":   file.get("mime_type", ""),
                "client":      file.get("client", ""),
                "category":    file.get("category", "Sonstiges"),
                "summary":     file.get("summary", ""),
                "web_link":    file.get("web_link", ""),
                "modified_at": file.get("modified_at", ""),
                "indexed_at":  datetime.now(timezone.utc).isoformat(),
            },
        )


def search(query: str, limit: int = 10) -> list[dict]:
    """Full-text search across name, client, category, summary."""
    like = f"%{query}%"
    with _conn() as con:
        rows = con.execute(
            """
            SELECT * FROM files
            WHERE name LIKE ? OR client LIKE ? OR category LIKE ? OR summary LIKE ?
            ORDER BY modified_at DESC
            LIMIT ?
            """,
            (like, like, like, like, limit),
        ).fetchall()
    return [dict(r) for r in rows]


def get_by_client(client: str, limit: int = 30) -> list[dict]:
    """Return files for a client (partial name match), newest first."""
    with _conn() as con:
        rows = con.execute(
            "SELECT * FROM files WHERE client LIKE ? ORDER BY modified_at DESC LIMIT ?",
            (f"%{client}%", limit),
        ).fetchall()
    return [dict(r) for r in rows]


def file_count() -> int:
    with _conn() as con:
        row = con.execute("SELECT COUNT(*) FROM files").fetchone()
        return row[0] if row else 0


def category_counts() -> dict[str, int]:
    with _conn() as con:
        rows = con.execute(
            "SELECT category, COUNT(*) as n FROM files GROUP BY category ORDER BY n DESC"
        ).fetchall()
    return {r["category"]: r["n"] for r in rows}


def clear() -> None:
    with _conn() as con:
        con.execute("DELETE FROM files")
    log.info("[INDEX] Datenbank geleert")
