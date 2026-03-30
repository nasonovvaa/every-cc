"""SQLite storage for tracking sent tenders (deduplication)."""

import logging
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)

DB_PATH = Path(__file__).parent / "sent_tenders.db"


def _get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH))
    conn.execute("""
        CREATE TABLE IF NOT EXISTS sent_tenders (
            id TEXT PRIMARY KEY,
            source TEXT NOT NULL,
            title TEXT NOT NULL,
            sent_at TEXT NOT NULL
        )
    """)
    conn.commit()
    return conn


def is_already_sent(source: str, tender_id: str) -> bool:
    """Check if a tender was already sent to Telegram."""
    key = f"{source}:{tender_id}"
    conn = _get_connection()
    try:
        row = conn.execute(
            "SELECT 1 FROM sent_tenders WHERE id = ?", (key,)
        ).fetchone()
        return row is not None
    finally:
        conn.close()


def mark_as_sent(source: str, tender_id: str, title: str) -> None:
    """Mark a tender as sent."""
    key = f"{source}:{tender_id}"
    conn = _get_connection()
    try:
        conn.execute(
            "INSERT OR IGNORE INTO sent_tenders (id, source, title, sent_at) VALUES (?, ?, ?, ?)",
            (key, source, title, datetime.now(timezone.utc).isoformat()),
        )
        conn.commit()
    finally:
        conn.close()


def filter_new_tenders(tenders: list) -> list:
    """Filter out tenders that have already been sent."""
    conn = _get_connection()
    try:
        new = []
        for t in tenders:
            key = f"{t.source}:{t.tender_id}"
            row = conn.execute(
                "SELECT 1 FROM sent_tenders WHERE id = ?", (key,)
            ).fetchone()
            if row is None:
                new.append(t)
        return new
    finally:
        conn.close()


def mark_batch_as_sent(tenders: list) -> None:
    """Mark a batch of tenders as sent."""
    conn = _get_connection()
    try:
        for t in tenders:
            key = f"{t.source}:{t.tender_id}"
            conn.execute(
                "INSERT OR IGNORE INTO sent_tenders (id, source, title, sent_at) VALUES (?, ?, ?, ?)",
                (key, t.source, t.title, datetime.now(timezone.utc).isoformat()),
            )
        conn.commit()
    finally:
        conn.close()


def get_sent_count() -> int:
    """Get the total number of sent tenders."""
    conn = _get_connection()
    try:
        row = conn.execute("SELECT COUNT(*) FROM sent_tenders").fetchone()
        return row[0] if row else 0
    finally:
        conn.close()
