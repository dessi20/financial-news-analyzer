import json
import os
import sqlite3
from typing import Any


def _db_path() -> str:
    return os.environ.get("FNA_DB_PATH", "analyses.db")


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(_db_path())
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with _connect() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS analyses (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at  TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%S', 'now')),
                source      TEXT    NOT NULL,
                headline    TEXT    NOT NULL,
                key_takeaways TEXT  NOT NULL,
                market_impact TEXT  NOT NULL,
                tickers     TEXT    NOT NULL,
                sentiment   TEXT    NOT NULL,
                raw_input   TEXT    NOT NULL
            )
        """)


def save_analysis(
    source: str,
    headline: str,
    key_takeaways: list[str],
    market_impact: str,
    tickers: list[str],
    sentiment: str,
    raw_input: str,
) -> int:
    with _connect() as conn:
        cursor = conn.execute(
            """
            INSERT INTO analyses
                (source, headline, key_takeaways, market_impact, tickers, sentiment, raw_input)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                source,
                headline,
                json.dumps(key_takeaways),
                market_impact,
                json.dumps(tickers),
                sentiment,
                raw_input,
            ),
        )
        row_id = cursor.lastrowid
        if row_id is None:
            raise RuntimeError("INSERT did not produce a row ID")
        return row_id


def _deserialize(row: sqlite3.Row) -> dict[str, Any]:
    d = dict(row)
    d["key_takeaways"] = json.loads(d["key_takeaways"])
    d["tickers"] = json.loads(d["tickers"])
    return d


def get_history(limit: int = 10) -> list[dict[str, Any]]:
    with _connect() as conn:
        rows = conn.execute(
            "SELECT * FROM analyses ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
    return [_deserialize(r) for r in rows]


def search_analyses(keyword: str) -> list[dict[str, Any]]:
    keyword_escaped = keyword.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    pattern = f"%{keyword_escaped}%"
    with _connect() as conn:
        rows = conn.execute(
            """
            SELECT * FROM analyses
            WHERE headline LIKE ? ESCAPE '\\'
               OR tickers   LIKE ? ESCAPE '\\'
               OR market_impact LIKE ? ESCAPE '\\'
            ORDER BY id DESC
            """,
            (pattern, pattern, pattern),
        ).fetchall()
    return [_deserialize(r) for r in rows]


def get_by_id(row_id: int) -> dict[str, Any] | None:
    with _connect() as conn:
        row = conn.execute(
            "SELECT * FROM analyses WHERE id = ?", (row_id,)
        ).fetchone()
    return _deserialize(row) if row else None
