# app.py
import os
import json
import threading
import time as time_module
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
CORS(app)

SUPABASE_URL         = os.getenv("SUPABASE_URL")
SUPABASE_ANON_KEY    = os.getenv("SUPABASE_ANON_KEY")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

# Scheduler state
_scheduler_thread  = None
_scheduler_running = False


# ── Frontend ──────────────────────────────────────────────────
@app.route("/")
def serve_frontend():
    return send_from_directory("frontend", "index.html")


# ── Auth ──────────────────────────────────────────────────────
@app.route("/api/signup", methods=["POST"])
def signup():
    data = request.json
    email, password = data.get("email"), data.get("password")
    if not email or not password:
        return jsonify({"error": "Email and password required"}), 400
    try:
        res = supabase.auth.sign_up({"email": email, "password": password})
        return jsonify({"message": "Signup successful", "user_id": res.user.id})
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@app.route("/api/login", methods=["POST"])
def login():
    data = request.json
    try:
        res = supabase.auth.sign_in_with_password({"email": data.get("email"), "password": data.get("password")})
        return jsonify({"access_token": res.session.access_token, "user_id": res.user.id})
    except Exception as e:
        return jsonify({"error": str(e)}), 401


def get_user_id(auth_header):
    """Helper to verify token and return user_id."""
    if not auth_header:
        return None
    token = auth_header.replace("Bearer ", "")
    try:
        user = supabase.auth.get_user(token)
        return user.user.id
    except:
        return None


# ── Preferences ───────────────────────────────────────────────
@app.route("/api/preferences", methods=["GET", "POST"])
def preferences():
    user_id = get_user_id(request.headers.get("Authorization"))
    if not user_id:
        return jsonify({"error": "Not authenticated"}), 401

    if request.method == "POST":
        data  = request.json
        prefs = {
            "user_id":            user_id,
            "phone_digits":       data.get("phone_digits"),
            "zip_code":           data.get("zip_code", "95035"),
            "radius_mi":          float(data.get("radius_mi", 25)),
            "service_type":       data.get("service_type", "automobile"),
            "max_slots":          int(data.get("max_slots", 3)),
            "check_interval_min": int(data.get("check_interval_min", 5)),
            "notify_frequency":   data.get("notify_frequency", "realtime"),
            "time_filter":        data.get("time_filter", "all"),
            "time_from":          data.get("time_from", "00:00"),
            "time_to":            data.get("time_to", "23:59"),
            "day_filter":         data.get("day_filter", "all"),
            "allowed_days":       json.dumps(data.get("allowed_days", [0,1,2,3,4])),
            "within_days":        data.get("within_days"),
            "carrier":            data.get("carrier", "tmomail.net"),
        }
        try:
            existing = supabase.table("user_profiles").select("id").eq("user_id", user_id).execute()
            if existing.data:
                supabase.table("user_profiles").update(prefs).eq("user_id", user_id).execute()
            else:
                supabase.table("user_profiles").insert(prefs).execute()
            
            return jsonify({"message": "Preferences saved"})
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    else:
        try:
            res = supabase.table("user_profiles") \
                .select("*") \
                .eq("user_id", user_id) \
                .execute()
            # Return first row if exists, otherwise empty object
            data = res.data
            if data and len(data) > 0:
                return jsonify(data[0])
            else:
                return jsonify({})
        except Exception as e:
            return jsonify({"error": str(e)}), 500


# ── Opt out ───────────────────────────────────────────────────
@app.route("/api/optout", methods=["POST"])
def optout():
    phone_digits = request.json.get("phone_digits")
    if not phone_digits:
        return jsonify({"error": "Phone number required"}), 400
    try:
        supabase.table("user_profiles").update({"opted_out": True}).eq("phone_digits", phone_digits).execute()
        return jsonify({"message": f"{phone_digits} opted out"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ── Slots history ─────────────────────────────────────────────
@app.route("/api/slots", methods=["GET"])
def get_slots():
    user_id = get_user_id(request.headers.get("Authorization"))
    if not user_id:
        return jsonify({"error": "Not authenticated"}), 401
    try:
        res = supabase.table("seen_slots") \
            .select("*") \
            .eq("user_id", user_id) \
            .order("found_at", desc=True) \
            .limit(50) \
            .execute()
        return jsonify(res.data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ── Health ────────────────────────────────────────────────────
@app.route("/api/health")
def health():
    return jsonify({"status": "ok"})


# ── Scheduler ─────────────────────────────────────────────────
def run_scheduler():
    global _scheduler_running
    from scraper import run_check
    from notify  import notify_new_slots
    from database import init_db

    init_db()
    _scheduler_running = True

    def run_scheduler():
        global _scheduler_running
    from scraper import run_check
    from notify  import notify_new_slots
    from database import init_db

    init_db()
    _scheduler_running = True

    while _scheduler_running:
        try:
            res   = supabase.table("user_profiles").select("*").eq("opted_out", False).execute()
            users = res.data or []
            print(f"\n[Scheduler] Checking {len(users)} active users...")

            for user in users:
                try:
                    prefs = {
                        "zip_code":           user["zip_code"],
                        "radius_mi":          user["radius_mi"],
                        "service_type":       user["service_type"],
                        "max_slots":          user["max_slots"],
                        "check_interval_min": user["check_interval_min"],
                        "notify_frequency":   user["notify_frequency"],
                        "time_filter":        user["time_filter"],
                        "time_from":          user["time_from"],
                        "time_to":            user["time_to"],
                        "day_filter":         user["day_filter"],
                        "allowed_days":       json.loads(user["allowed_days"]),
                        "within_days":        user["within_days"],
                        "phone_digits":       user["phone_digits"],
                        "carrier":            user["carrier"],
                    }
                    slots = run_check(user["zip_code"], user["radius_mi"], prefs=prefs)
                    if slots:
                        notify_new_slots(slots, prefs=prefs)
                except Exception as e:
                    print(f"  Error for user {user.get('user_id')}: {e}")

        except Exception as e:
            print(f"[Scheduler] Error: {e}")

        # Only run once per manual trigger
        print("\n[Scheduler] Check complete. Toggle off and on to run again.")
        break


@app.route("/api/scheduler/start", methods=["POST"])
def start_scheduler():
    global _scheduler_thread, _scheduler_running
    if _scheduler_thread and _scheduler_thread.is_alive():
        return jsonify({"message": "Scheduler already running"})
    _scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
    _scheduler_thread.start()
    return jsonify({"message": "Scheduler started"})


@app.route("/api/scheduler/stop", methods=["POST"])
def stop_scheduler():
    global _scheduler_running
    _scheduler_running = False
    return jsonify({"message": "Scheduler stopping"})


@app.route("/api/scheduler/status")
def scheduler_status():
    running = _scheduler_thread is not None and _scheduler_thread.is_alive()
    return jsonify({"running": running})


if __name__ == "__main__":
    app.run(debug=True, port=5000)