# scraper.py
import hashlib
import re
import time
import json
import urllib.parse
from dataclasses import dataclass
from datetime import datetime, timedelta

import requests
from playwright.sync_api import sync_playwright

from config import BASE, TIMES_URL, SERVICE_TYPES

AVAILABLE_URL = f"{BASE}/wp-json/dmv/v1/appointment/available/"
DATES_URL     = f"{BASE}/wp-json/dmv/v1/appointment/branches/{{publicId}}/dates"
BOOKING_URL   = f"{BASE}/appointments/select-appointment-type/"

SERVICE_ID = "DT!1857a62125c4425a24d85aceac6726cb8df3687d47b03b692e27bd8d17814"

HEADERS = {
    "accept":          "*/*",
    "accept-language": "en-US,en;q=0.9",
    "user-agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/148.0.0.0 Safari/537.36"
    ),
    "sec-fetch-dest": "empty",
    "sec-fetch-mode": "cors",
    "sec-fetch-site": "same-origin",
}

OFFICE_INFO = {
    "516!56b48e272ba45819d81868f440fb30eb6c406b705436cf1d101d2ea2c75c": {"address": "111 W. Alma Ave.",            "zip": "95110", "city": "San Jose"},
    "632!afa980930a4d9da9dea767520801e38ef924a286d22bf6d97782c5d20731": {"address": "3665 Flora Vista Ave.",        "zip": "95051", "city": "Santa Clara"},
    "640!9ffc1fef9b57f8bf1ba6984ffdb4981acbf88d4b101ae27edac9d65a45f4": {"address": "600 North Santa Cruz Ave.",   "zip": "95030", "city": "Los Gatos"},
    "668!425f963ed312b21424c080ab6ad65d91e820502590e03c8c28c2accc263c": {"address": "180 Martinvale Lane",         "zip": "95119", "city": "Santa Teresa"},
    "631!c533ba75524ac439cdf0826fc9eafc888c8242fa3863104a1b383c3bfb05": {"address": "6300 W. Las Positas Blvd",    "zip": "94588", "city": "Pleasanton"},
    "644!03ada32357f5fd32a107fca81b020fd9b4fd0062cbaabf014dcacb6b5516": {"address": "4287 Central Ave.",           "zip": "94536", "city": "Fremont"},
    "623!7d6e807879fe5c298d463eeabed992b7b28b2feb80ad74dbb1a4ce5ebae6": {"address": "6984 Automall Parkway Suite A","zip": "95020", "city": "Gilroy"},
}


@dataclass
class Slot:
    office_id:      str
    office_name:    str
    office_address: str
    distance_mi:    float
    service_type:   str
    slot_date:      str
    slot_time:      str
    booking_url:    str

    @property
    def slot_key(self):
        raw = f"{self.office_id}:{self.slot_date}:{self.slot_time}:{self.service_type}"
        return hashlib.md5(raw.encode()).hexdigest()

    @property
    def display_date(self):
        dt = datetime.strptime(self.slot_date, "%Y-%m-%d")
        return dt.strftime("%A, %b %-d")

    @property
    def display_time(self):
        if not self.slot_time:
            return "Time TBD"
        try:
            t = datetime.strptime(self.slot_time, "%H:%M")
            return t.strftime("%-I:%M %p")
        except:
            return self.slot_time

    @property
    def display_datetime(self):
        return f"{self.display_date} at {self.display_time}"


def get_session_automated(dl_number: str, dob: str, zip_code: str) -> tuple:
    """Fully automated Playwright session. Captures the 'available offices' list
    and the session cookies, then queries the dates endpoint directly for each
    nearby office (no fragile calendar-UI clicking)."""
    global SERVICE_ID
    token             = None
    cookies           = {}
    service_id        = None
    available_offices = []   # list of {publicId, name, addressLine1, addressZip}

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-setuid-sandbox", "--disable-dev-shm-usage",
                  "--disable-gpu", "--single-process"]
        )
        context = browser.new_context(
            viewport={"width": 1280, "height": 800},
            user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = context.new_page()

        def on_response(response):
            nonlocal service_id, available_offices
            url = response.url
            # Capture the service id from the available request URL
            if "appointment/available" in url:
                svc_match = re.search(r'services%5B%5D=([^&]+)', url)
                if not svc_match:
                    svc_match = re.search(r'services\[\]=([^&]+)', url)
                if svc_match:
                    service_id = urllib.parse.unquote(svc_match.group(1))
                # Capture the list of available offices
                try:
                    body = response.json()
                    if isinstance(body, list) and body:
                        available_offices = body
                        print(f"  ✓ Captured {len(body)} available offices")
                except Exception as e:
                    print(f"  [available] parse failed: {e}")

        page.on("response", on_response)

        print("  Loading DMV booking page...")
        page.goto(f"{BASE}/appointments/select-appointment-type/", timeout=30000)
        page.wait_for_load_state("networkidle", timeout=15000)
        page.wait_for_timeout(3000)

        try:
            # Step 1: Click the DT label
            print("  Checking DT checkbox...")
            try:
                page.click("label[for='DT']", timeout=5000)
                print("  ✓ Clicked DT label")
            except:
                try:
                    page.evaluate("document.getElementById('DT').click()")
                    print("  ✓ Checked DT via JavaScript")
                except Exception as e:
                    print(f"  Could not check DT: {e}")

            page.wait_for_timeout(3000)

            # Step 2: Fill license number
            for selector in ["#dlNumber", "input[name='dlNumber']"]:
                try:
                    field = page.locator(selector).first
                    field.wait_for(timeout=5000)
                    field.click()
                    field.type(dl_number, delay=50)
                    page.keyboard.press("Tab")
                    print("  ✓ Entered license number")
                    break
                except:
                    continue

            # Step 3: Fill DOB
            for selector in ["#dob", "input[name='dob']"]:
                try:
                    field = page.locator(selector).first
                    field.wait_for(timeout=5000)
                    field.click()
                    field.type(dob, delay=50)
                    page.keyboard.press("Tab")
                    print("  ✓ Entered DOB")
                    break
                except:
                    continue

            page.wait_for_timeout(2000)

            # Step 4: Click Make an Appointment (this triggers the available/ call)
            clicked_submit = page.evaluate("""
                () => {
                    const candidates = Array.from(document.querySelectorAll('button, a, input[type="submit"]'));
                    const header = document.querySelector('header');
                    const valid = candidates.filter(b => {
                        if (header && header.contains(b)) return false;
                        const txt = (b.textContent || b.value || '').trim().toLowerCase();
                        return txt === 'make an appointment' || txt.includes('make an appointment');
                    });
                    if (valid.length > 0) {
                        valid[0].scrollIntoView();
                        valid[0].click();
                        return true;
                    }
                    return false;
                }
            """)
            if clicked_submit:
                print("  ✓ Clicked Make an Appointment")
            else:
                print("  Could not click Make an Appointment")

            # Wait for the available/ endpoint to return the office list
            for _ in range(15):
                if available_offices:
                    break
                page.wait_for_timeout(1000)

        except Exception as e:
            print(f"  Automation step failed: {e}")

        # Grab cookies for direct API calls
        raw_cookies = context.cookies()
        cookies = {c["name"]: c["value"] for c in raw_cookies}
        browser.close()

    if service_id:
        SERVICE_ID = service_id

    return token, cookies, service_id, available_offices


def get_session_manual() -> tuple:
    """Manual fallback for local testing."""
    global SERVICE_ID
    token             = None
    cookies           = {}
    service_id        = None
    clicked_office_id = None
    dates_data        = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, args=["--start-maximized"])
        context = browser.new_context(no_viewport=True)
        page    = context.new_page()

        def on_response(response):
            nonlocal token, service_id, clicked_office_id, dates_data
            if "branches/" in response.url and "dates" in response.url:
                svc_match = re.search(r'services%5B%5D=([^&]+)', response.url)
                if svc_match:
                    service_id = urllib.parse.unquote(svc_match.group(1))
                office_match = re.search(r'branches/([^/]+)/dates', response.url)
                if office_match:
                    clicked_office_id = urllib.parse.unquote(office_match.group(1))
                token_match = re.search(r'token=([^&]+)', response.url)
                if token_match:
                    token = token_match.group(1)
                try:
                    dates_data = response.json()
                    print(f"\n  ✓ Captured {len(dates_data)} date entries!")
                except:
                    pass

        page.on("response", on_response)

        print("\n" + "="*55)
        print("  ACTION NEEDED — please use the browser that opened")
        print("="*55)
        print("  1. Click SELECT next to Automobile")
        print("  2. Enter your license number and date of birth")
        print("  3. Click 'Make an Appointment'")
        print("  4. Enter your zip code and click the arrow")
        print("  5. Click 'Select Location' on any office")
        print("\n  Script will auto-continue once data is captured.")
        print("="*55)

        page.goto(f"{BASE}/appointments/select-appointment-type/", timeout=30000)

        for i in range(180):
            if dates_data:
                break
            page.wait_for_timeout(1000)
            if i > 0 and i % 20 == 0:
                print(f"  Still waiting... ({i}s)")

        raw_cookies = context.cookies()
        cookies = {c["name"]: c["value"] for c in raw_cookies}
        browser.close()

    return token, cookies, service_id, clicked_office_id, dates_data


def get_times_for_date(public_id: str, date_str: str, session: requests.Session) -> list:
    url = TIMES_URL.format(publicId=public_id)
    params = {"date": date_str, "services[]": SERVICE_ID, "numberOfCustomers": "1"}
    try:
        resp = session.get(url, params=params, headers=HEADERS, timeout=10)
        resp.raise_for_status()
        return resp.json()
    except:
        return []


def get_dates_for_office(public_id: str, session: requests.Session) -> list:
    """Call the dates endpoint directly for one office using session cookies."""
    url = DATES_URL.format(publicId=public_id)
    params = {"services[]": SERVICE_ID, "numberOfCustomers": "1"}
    try:
        resp = session.get(url, params=params, headers=HEADERS, timeout=10)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        return []


def passes_day_filter(date_str: str, prefs: dict) -> bool:
    day_filter  = prefs.get("day_filter", "all")
    within_days = prefs.get("within_days")
    dt = datetime.strptime(date_str, "%Y-%m-%d")
    if within_days:
        if dt > datetime.now() + timedelta(days=int(within_days)):
            return False
    if day_filter == "all":
        return True
    elif day_filter == "weekdays":
        return dt.weekday() < 5
    elif day_filter == "custom":
        return dt.weekday() in (prefs.get("allowed_days") or [0,1,2,3,4])
    return True


def passes_time_filter(time_str: str, prefs: dict) -> bool:
    time_filter = prefs.get("time_filter", "all")
    if time_filter == "all":
        return True
    try:
        t = datetime.strptime(time_str, "%H:%M").time()
    except:
        return True
    if time_filter == "morning":
        return t < datetime.strptime("12:00", "%H:%M").time()
    elif time_filter == "afternoon":
        return t >= datetime.strptime("12:00", "%H:%M").time()
    elif time_filter == "custom":
        t_from = datetime.strptime(prefs.get("time_from", "00:00"), "%H:%M").time()
        t_to   = datetime.strptime(prefs.get("time_to",   "23:59"), "%H:%M").time()
        return t_from <= t <= t_to
    return True


def parse_slots_with_times(dates_response, target_office_id, distance_mi, session, prefs) -> list:
    global SERVICE_ID
    slots   = []
    info    = OFFICE_INFO.get(target_office_id, {})
    address = f"{info.get('address', '')}, {info.get('city', '')}"

    for entry in dates_response:
        raw_date = entry.get("date", "")
        if not raw_date:
            continue
        slot_date  = raw_date.split("T")[0]
        branch_ids = [b["publicId"] for b in entry.get("branches", [])]
        if target_office_id not in branch_ids:
            continue
        if not passes_day_filter(slot_date, prefs):
            continue

        office_name = next(
            (b["name"] for b in entry["branches"] if b["publicId"] == target_office_id),
            info.get("city", target_office_id)
        )
        office_num = target_office_id.split("!")[0]
        base_url   = f"{BOOKING_URL}?officeId={office_num}&date={slot_date}"
        times      = get_times_for_date(target_office_id, slot_date, session)

        if times:
            for t in times:
                if not passes_time_filter(t, prefs):
                    continue
                slots.append(Slot(
                    office_id=target_office_id, office_name=office_name,
                    office_address=address, distance_mi=distance_mi,
                    service_type=SERVICE_ID, slot_date=slot_date, slot_time=t,
                    booking_url=f"{base_url}&time={t}",
                ))
        else:
            slots.append(Slot(
                office_id=target_office_id, office_name=office_name,
                office_address=address, distance_mi=distance_mi,
                service_type=SERVICE_ID, slot_date=slot_date, slot_time="",
                booking_url=base_url,
            ))
        time.sleep(0.5)

    return slots


def run_check(zip_code: str, radius_mi: float, prefs: dict = None) -> list:
    global SERVICE_ID
    from geo_filter import zip_to_coords
    from geopy.distance import geodesic

    if prefs is None:
        from config import DEFAULTS
        prefs = DEFAULTS.copy()

    print(f"\n── DMV check for {zip_code} ──")

    dl_number = prefs.get("dl_number", "")
    dob       = prefs.get("dob", "")

    if dl_number and dob:
        print("  Using automated login...")
        token, cookies, service_id, available_offices = get_session_automated(
            dl_number, dob, zip_code
        )
    else:
        print("  No credentials — using manual login...")
        # Manual mode still returns the old 5-tuple; adapt it
        token, cookies, service_id, clicked_office_id, dates_data = get_session_manual()
        available_offices = []

    if service_id:
        SERVICE_ID = service_id

    if not available_offices:
        print("  ✗ No available offices captured")
        return []

    session = requests.Session()
    session.cookies.update(cookies)

    # Determine user coordinates for distance filtering
    try:
        user_coords = zip_to_coords(zip_code)
    except:
        user_coords = None

    # Filter offices by radius, then query dates for each
    all_slots = []
    nearby = []
    for office in available_offices:
        pub_id = office.get("publicId", "")
        ozip   = office.get("addressZip", "")
        oname  = office.get("name", "").title()
        oaddr  = office.get("addressLine1", "")
        distance = 0.0
        if user_coords and ozip:
            try:
                office_coords = zip_to_coords(ozip)
                distance = round(geodesic(user_coords, office_coords).miles, 1)
            except:
                distance = 9999
        # Keep only offices within the radius
        if distance <= radius_mi:
            nearby.append((pub_id, oname, oaddr, ozip, distance))

    # Sort by distance, closest first
    nearby.sort(key=lambda x: x[4])
    print(f"  {len(nearby)} offices within {radius_mi} miles")

    for pub_id, oname, oaddr, ozip, distance in nearby:
        dates = get_dates_for_office(pub_id, session)
        if not dates:
            continue
        print(f"  {oname}: {len(dates)} date entries ({distance} mi)")
        slots = parse_office_dates(dates, pub_id, oname, oaddr, distance, session, prefs)
        all_slots.extend(slots)
        time.sleep(0.4)

    print(f"Total slots found: {len(all_slots)}")
    return all_slots


def parse_office_dates(dates_response, pub_id, office_name, office_address,
                       distance_mi, session, prefs) -> list:
    """Parse the dates response for a single office and fetch times per date."""
    global SERVICE_ID
    slots = []
    # The dates response may be a list of date strings or objects
    for entry in dates_response:
        if isinstance(entry, dict):
            raw_date = entry.get("date", "")
        else:
            raw_date = str(entry)
        if not raw_date:
            continue
        slot_date = raw_date.split("T")[0]
        if not passes_day_filter(slot_date, prefs):
            continue

        office_num = pub_id.split("!")[0]
        base_url   = f"{BOOKING_URL}?officeId={office_num}&date={slot_date}"
        times      = get_times_for_date(pub_id, slot_date, session)

        if times:
            for t in times:
                tstr = t if isinstance(t, str) else (t.get("time", "") if isinstance(t, dict) else "")
                if not tstr:
                    continue
                if not passes_time_filter(tstr, prefs):
                    continue
                slots.append(Slot(
                    office_id=pub_id, office_name=office_name,
                    office_address=office_address, distance_mi=distance_mi,
                    service_type=SERVICE_ID, slot_date=slot_date, slot_time=tstr,
                    booking_url=f"{base_url}&time={tstr}",
                ))
        else:
            slots.append(Slot(
                office_id=pub_id, office_name=office_name,
                office_address=office_address, distance_mi=distance_mi,
                service_type=SERVICE_ID, slot_date=slot_date, slot_time="",
                booking_url=base_url,
            ))
        time.sleep(0.3)

    return slots


if __name__ == "__main__":
    from config import DEFAULTS
    slots = run_check("95035", radius_mi=25, prefs=DEFAULTS.copy())
    for s in slots[:5]:
        print(f"{s.display_datetime} | {s.office_name} | {s.booking_url}")