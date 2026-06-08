# database.py
import sqlite3
import os
import json
from datetime import datetime, timedelta

DB_PATH = os.path.join(os.path.dirname(__file__), "slots.db")


def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
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
            slot_time      TEXT,
            booking_url    TEXT    NOT NULL,
            status         TEXT    DEFAULT 'new',
            found_at       TEXT    DEFAULT (datetime('now')),
            notified_at    TEXT
        );

        CREATE TABLE IF NOT EXISTS subscribers (
            id                  INTEGER PRIMARY KEY AUTOINCREMENT,
            phone_digits        TEXT,
            email               TEXT,
            zip_code            TEXT    NOT NULL,
            radius_mi           REAL    NOT NULL DEFAULT 25,
            service_type        TEXT    NOT NULL DEFAULT 'automobile',
            max_slots           INTEGER NOT NULL DEFAULT 3,
            check_interval_min  INTEGER NOT NULL DEFAULT 5,
            notify_frequency    TEXT    NOT NULL DEFAULT 'realtime',
            time_filter         TEXT    NOT NULL DEFAULT 'all',
            time_from           TEXT    NOT NULL DEFAULT '00:00',
            time_to             TEXT    NOT NULL DEFAULT '23:59',
            day_filter          TEXT    NOT NULL DEFAULT 'all',
            allowed_days        TEXT    NOT NULL DEFAULT '[0,1,2,3,4]',
            within_days         INTEGER,
            opted_out           INTEGER NOT NULL DEFAULT 0,
            last_notified_at    TEXT,
            created_at          TEXT    DEFAULT (datetime('now'))
        );
    """)
    conn.commit()
    conn.close()


# ── Slot operations ───────────────────────────────────────────────────────────

def is_new_slot(slot_key: str) -> bool:
    conn = get_conn()
    row = conn.execute(
        "SELECT id FROM seen_slots WHERE slot_key = ?", (slot_key,)
    ).fetchone()
    conn.close()
    return row is None


def save_slot(slot) -> bool:
    conn = get_conn()
    try:
        conn.execute("""
            INSERT INTO seen_slots
              (slot_key, office_id, office_name, office_address,
               distance_mi, service_type, slot_date, slot_time, booking_url)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            slot.slot_key,
            slot.office_id,
            slot.office_name,
            slot.office_address,
            slot.distance_mi,
            slot.service_type,
            slot.slot_date,
            slot.slot_time,
            slot.booking_url,
        ))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()


def mark_notified(slot_key: str):
    conn = get_conn()
    conn.execute("""
        UPDATE seen_slots
        SET status = 'sent', notified_at = ?
        WHERE slot_key = ?
    """, (datetime.now().isoformat(), slot_key))
    conn.commit()
    conn.close()


def get_recent_slots(limit: int = 50) -> list:
    conn = get_conn()
    rows = conn.execute("""
        SELECT * FROM seen_slots
        ORDER BY found_at DESC LIMIT ?
    """, (limit,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def clear_seen_slots():
    conn = get_conn()
    conn.execute("DELETE FROM seen_slots")
    conn.commit()
    conn.close()
    print("  Seen slots cache cleared.")


# ── Subscriber operations ─────────────────────────────────────────────────────

def get_subscriber(phone_digits: str = None, email: str = None) -> dict | None:
    conn = get_conn()
    if phone_digits:
        row = conn.execute(
            "SELECT * FROM subscribers WHERE phone_digits = ?", (phone_digits,)
        ).fetchone()
    elif email:
        row = conn.execute(
            "SELECT * FROM subscribers WHERE email = ?", (email,)
        ).fetchone()
    else:
        row = None
    conn.close()
    return dict(row) if row else None


def upsert_subscriber(prefs: dict):
    """Insert or update a subscriber's preferences."""
    conn = get_conn()
    existing = None
    if prefs.get("phone_digits"):
        existing = conn.execute(
            "SELECT id FROM subscribers WHERE phone_digits = ?",
            (prefs["phone_digits"],)
        ).fetchone()

    if existing:
        conn.execute("""
            UPDATE subscribers SET
                email               = ?,
                zip_code            = ?,
                radius_mi           = ?,
                service_type        = ?,
                max_slots           = ?,
                check_interval_min  = ?,
                notify_frequency    = ?,
                time_filter         = ?,
                time_from           = ?,
                time_to             = ?,
                day_filter          = ?,
                allowed_days        = ?,
                within_days         = ?,
                opted_out           = 0
            WHERE phone_digits = ?
        """, (
            prefs.get("email"),
            prefs["zip_code"],
            prefs.get("radius_mi", 25),
            prefs.get("service_type", "automobile"),
            prefs.get("max_slots", 3),
            prefs.get("check_interval_min", 5),
            prefs.get("notify_frequency", "realtime"),
            prefs.get("time_filter", "all"),
            prefs.get("time_from", "00:00"),
            prefs.get("time_to", "23:59"),
            prefs.get("day_filter", "all"),
            json.dumps(prefs.get("allowed_days", [0,1,2,3,4])),
            prefs.get("within_days"),
            prefs["phone_digits"],
        ))
    else:
        conn.execute("""
            INSERT INTO subscribers
              (phone_digits, email, zip_code, radius_mi, service_type,
               max_slots, check_interval_min, notify_frequency,
               time_filter, time_from, time_to,
               day_filter, allowed_days, within_days)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, (
            prefs.get("phone_digits"),
            prefs.get("email"),
            prefs["zip_code"],
            prefs.get("radius_mi", 25),
            prefs.get("service_type", "automobile"),
            prefs.get("max_slots", 3),
            prefs.get("check_interval_min", 5),
            prefs.get("notify_frequency", "realtime"),
            prefs.get("time_filter", "all"),
            prefs.get("time_from", "00:00"),
            prefs.get("time_to", "23:59"),
            prefs.get("day_filter", "all"),
            json.dumps(prefs.get("allowed_days", [0,1,2,3,4])),
            prefs.get("within_days"),
        ))
    conn.commit()
    conn.close()


def update_last_notified(phone_digits: str):
    conn = get_conn()
    conn.execute("""
        UPDATE subscribers SET last_notified_at = ?
        WHERE phone_digits = ?
    """, (datetime.now().isoformat(), phone_digits))
    conn.commit()
    conn.close()


def is_opted_out(phone_digits: str) -> bool:
    conn = get_conn()
    row = conn.execute(
        "SELECT opted_out FROM subscribers WHERE phone_digits = ?",
        (phone_digits,)
    ).fetchone()
    conn.close()
    return bool(row and row["opted_out"])


def set_opt_out(phone_digits: str, opted_out: bool = True):
    conn = get_conn()
    conn.execute(
        "UPDATE subscribers SET opted_out = ? WHERE phone_digits = ?",
        (1 if opted_out else 0, phone_digits)
    )
    conn.commit()
    conn.close()
    print(f"  {phone_digits} opted {'out' if opted_out else 'back in'}")


def can_notify_now(phone_digits: str, notify_frequency: str) -> bool:
    """Check if enough time has passed to send another notification."""
    if notify_frequency == "realtime":
        return True

    conn = get_conn()
    row = conn.execute(
        "SELECT last_notified_at FROM subscribers WHERE phone_digits = ?",
        (phone_digits,)
    ).fetchone()
    conn.close()

    if not row or not row["last_notified_at"]:
        return True

    last = datetime.fromisoformat(row["last_notified_at"])
    now  = datetime.now()

    if notify_frequency == "once_day":
        return (now - last) >= timedelta(hours=24)
    elif notify_frequency == "twice_day":
        return (now - last) >= timedelta(hours=12)

    return True


if __name__ == "__main__":
    init_db()
    print("  Database initialized.")
    print(f"  Database file: {DB_PATH}")