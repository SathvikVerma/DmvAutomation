# config.py
# ── Service types available on the DMV site ───────────────────────────────────
# The prefix (e.g. "DT") comes from the URL captured in DevTools.
# The full serviceId is captured live from the browser session each run.
# These labels match exactly what the DMV website shows.

SERVICE_TYPES = {
    "automobile":   {"label": "Automobile (Drive Test)",         "prefix": "DT"},
    "commercial":   {"label": "Commercial (Drive Test)",         "prefix": "DT"},
    "motorcycle":   {"label": "Motorcycle (Drive Test)",         "prefix": "DT"},
    "realid_cdl":   {"label": "Real ID & CDL",                   "prefix": "AKTE"},
    "knowledge":    {"label": "Knowledge Test Re-evaluation",    "prefix": "LT"},
}

# ── Day name → weekday number (Monday=0, Sunday=6) ────────────────────────────
DAY_MAP = {
    "monday":    0,
    "tuesday":   1,
    "wednesday": 2,
    "thursday":  3,
    "friday":    4,
    "saturday":  5,
    "sunday":    6,
}

# ── Notification frequency options ────────────────────────────────────────────
NOTIFY_FREQUENCY = {
    "realtime":   "Every time a new slot opens",
    "once_day":   "Once per day",
    "twice_day":  "Twice per day",
}

# ── Check interval options (minutes) ─────────────────────────────────────────
CHECK_INTERVALS = {
    5:   "Every 5 minutes",
    30:  "Every 30 minutes",
    60:  "Every hour",
    300: "Every 5 hours",
}

# ── Default user preferences ──────────────────────────────────────────────────
DEFAULTS = {
    "max_slots":          3,
    "check_interval_min": 5,
    "notify_frequency":   "realtime",
    "time_filter":        "all",        # all | morning | afternoon | custom
    "time_from":          "00:00",
    "time_to":            "23:59",
    "day_filter":         "all",        # all | weekdays | custom
    "allowed_days":       [0,1,2,3,4],  # mon-fri
    "within_days":        None,         # e.g. 12 means only next 12 days
}

# ── Times endpoint ────────────────────────────────────────────────────────────
BASE      = "https://www.dmv.ca.gov/portal"
TIMES_URL = f"{BASE}/wp-json/dmv/v1/appointment/branches/{{publicId}}/times"