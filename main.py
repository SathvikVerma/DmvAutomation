# main.py
import os
import time
import json
from dotenv import load_dotenv

load_dotenv()

# ── Load user prefs from .env ─────────────────────────────────────────────────
ZIP_CODE      = os.getenv("DMV_ZIP", "95035")
RADIUS_MI     = float(os.getenv("DMV_RADIUS", "25"))
INTERVAL_MIN  = int(os.getenv("CHECK_INTERVAL_MINUTES", "5"))
SERVICE_TYPE  = os.getenv("DMV_SERVICE_TYPE", "automobile")

PREFS = {
    "zip_code":           ZIP_CODE,
    "radius_mi":          RADIUS_MI,
    "service_type":       SERVICE_TYPE,
    "phone_digits":       os.getenv("NOTIFY_PHONE_DIGITS"),
    "email":              os.getenv("NOTIFY_EMAIL"),

    # Notification settings
    "max_slots":          int(os.getenv("MAX_SLOTS", "3")),
    "notify_frequency":   os.getenv("NOTIFY_FREQUENCY", "realtime"),

    # Time filter: all | morning | afternoon | custom
    "time_filter":        os.getenv("TIME_FILTER", "all"),
    "time_from":          os.getenv("TIME_FROM", "00:00"),
    "time_to":            os.getenv("TIME_TO", "23:59"),

    # Day filter: all | weekdays | custom
    "day_filter":         os.getenv("DAY_FILTER", "all"),
    "allowed_days":       json.loads(os.getenv("ALLOWED_DAYS", "[0,1,2,3,4]")),

    # Only notify for appointments within next N days (None = no limit)
    "within_days":        int(os.getenv("WITHIN_DAYS")) if os.getenv("WITHIN_DAYS") else None,
}


def run_cycle():
    from scraper import run_check
    from notify  import notify_new_slots
    from database import init_db

    init_db()

    print(f"\n{'='*52}")
    print(f"  DMV check — {PREFS['zip_code']} | {PREFS['radius_mi']} mi radius")
    print(f"  Service: {PREFS['service_type']} | Interval: {INTERVAL_MIN} min")
    print(f"  Time filter: {PREFS['time_filter']} | Day filter: {PREFS['day_filter']}")
    print(f"{'='*52}")

    try:
        slots = run_check(ZIP_CODE, RADIUS_MI, prefs=PREFS)
        if slots:
            sent = notify_new_slots(slots, prefs=PREFS)
            print(f"\n  Notifications sent: {sent}")
        else:
            print("  No slots found this cycle.")
    except Exception as e:
        print(f"  ✗ Cycle error: {e}")


def main():
    print("\n" + "="*52)
    print("  DMV Notifier — starting up")
    print(f"  Zip: {ZIP_CODE} | Radius: {RADIUS_MI} mi")
    print(f"  Checking every {INTERVAL_MIN} minutes")
    print(f"  Max slots per alert: {PREFS['max_slots']}")
    print(f"  Notify frequency: {PREFS['notify_frequency']}")
    print("  Press Ctrl+C to stop")
    print("="*52)

    while True:
        run_cycle()
        print(f"\n  Sleeping {INTERVAL_MIN} min until next check...")
        time.sleep(INTERVAL_MIN * 60)


if __name__ == "__main__":
    main()