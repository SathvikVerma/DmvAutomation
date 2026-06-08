# db.py
import sqlite3
import os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), "slots.db")


def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Create tables if they don't exist yet."""
    conn = get_conn()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS seen_slots (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            slot_key       TEXT    UNIQUE NOT NULL,
            office_id      TEXT    NOT NULL,
            office_name    TEXT    NOT NULL,
            office_address TEXT    NOT NULL,
            distance_mi    REAL,
            service_type   TEXT    NOT NULL,
            slot_date      TEXT    NOT NULL,
            booking_url    TEXT    NOT NULL,
            status         TEXT    DEFAULT 'new',
            found_at       TEXT    DEFAULT (datetime('now')),
            notified_at    TEXT
        );

        CREATE TABLE IF NOT EXISTS subscribers (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            phone       TEXT    UNIQUE,
            email       TEXT    UNIQUE,
            zip_code    TEXT    NOT NULL,
            radius_mi   REAL    NOT NULL,
            opted_out   INTEGER DEFAULT 0,
            created_at  TEXT    DEFAULT (datetime('now'))
        );
    """)
    conn.commit()
    conn.close()
    print("  Database initialized.")


def is_new_slot(slot_key: str) -> bool:
    """Returns True if this slot has never been seen before."""
    conn = get_conn()
    row = conn.execute(
        "SELECT id FROM seen_slots WHERE slot_key = ?", (slot_key,)
    ).fetchone()
    conn.close()
    return row is None


def save_slot(slot) -> bool:
    """
    Insert a new slot. Returns True if it was new, False if already existed.
    `slot` is a Slot dataclass from scraper.py.
    """
    conn = get_conn()
    try:
        conn.execute("""
            INSERT INTO seen_slots
              (slot_key, office_id, office_name, office_address,
               distance_mi, service_type, slot_date, booking_url)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            slot.slot_key,
            slot.office_id,
            slot.office_name,
            slot.office_address,
            slot.distance_mi,
            slot.service_type,
            slot.slot_date,
            slot.booking_url,
        ))
        conn.commit()
        return True   # new slot
    except sqlite3.IntegrityError:
        return False  # already seen
    finally:
        conn.close()


def mark_notified(slot_key: str):
    """Mark a slot as notified so we don't alert twice."""
    conn = get_conn()
    conn.execute("""
        UPDATE seen_slots
        SET status = 'sent', notified_at = ?
        WHERE slot_key = ?
    """, (datetime.now().isoformat(), slot_key))
    conn.commit()
    conn.close()


def get_recent_slots(limit: int = 50) -> list:
    """Fetch recent slots for the dashboard."""
    conn = get_conn()
    rows = conn.execute("""
        SELECT * FROM seen_slots
        ORDER BY found_at DESC
        LIMIT ?
    """, (limit,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def is_opted_out(phone: str) -> bool:
    """Check if a phone number has opted out of notifications."""
    conn = get_conn()
    row = conn.execute(
        "SELECT opted_out FROM subscribers WHERE phone = ?", (phone,)
    ).fetchone()
    conn.close()
    return bool(row and row["opted_out"])


def set_opt_out(phone: str, opted_out: bool = True):
    """Set opted_out flag for a phone number."""
    conn = get_conn()
    conn.execute("""
        UPDATE subscribers SET opted_out = ?
        WHERE phone = ?
    """, (1 if opted_out else 0, phone))
    conn.commit()
    conn.close()
    status = "opted OUT" if opted_out else "opted back IN"
    print(f"  {phone} has {status}")


def clear_seen_slots():
    """Wipe the seen slots cache — useful for testing."""
    conn = get_conn()
    conn.execute("DELETE FROM seen_slots")
    conn.commit()
    conn.close()
    print("  Seen slots cache cleared.")


if __name__ == "__main__":
    init_db()
    print("  Tables created successfully.")
    print(f"  Database file: {DB_PATH}")