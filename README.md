# DMV Notifier

A web app that monitors the California DMV appointment system and sends instant notifications when slots open up near you — filtered by location, time, day, and service type.

## Live Demo

[dmvautomation-production.up.railway.app](https://dmvautomation-production.up.railway.app)

---

## What it does

- Monitors DMV appointment availability in real time
- Filters by zip code and radius
- Filters by service type (Drive Test, Real ID, Knowledge Test, etc.)
- Filters by day of week and time of day
- Sends push notifications via Pushover app
- Sends formatted HTML emails with a one-click booking link
- Deduplication — never sends the same slot twice
- Opt-out support
- User accounts with saved preferences

---

## Tech stack

| Layer | Technology |
|---|---|
| Backend | Python, Flask |
| Scraper | Playwright (headless Chromium) |
| Database | SQLite (local) + Supabase (cloud) |
| Auth | Supabase Auth |
| Push notifications | Pushover |
| Email | Gmail SMTP |
| Frontend | HTML / CSS / JavaScript |
| Hosting | Railway |

---

## How it works

The California DMV does not have a public API. The scraper uses Playwright to walk through the booking flow in a headless browser, intercepts the internal JSON endpoints, and extracts available appointment dates and times. It then filters results against each user's preferences and sends notifications for any new slots found.

---

## Project structure

```
dmv-notifier/
├── app.py              # Flask backend — routes, auth, scheduler
├── scraper.py          # DMV scraper — dates and times
├── geo_filter.py       # Radius filtering by zip code
├── database.py         # SQLite operations
├── notify.py           # Pushover and email notifications
├── config.py           # Service types, constants, defaults
├── main.py             # Local entry point and scheduler
├── frontend/
│   └── index.html      # Single-page web app
├── Procfile            # Railway start command
├── railway.json        # Railway config
├── requirements.txt    # Python dependencies
└── .env.example        # Environment variable template
```

---

## Local setup

### 1. Clone and install

```bash
git clone https://github.com/SathvikVerma/DmvAutomation.git
cd DmvAutomation
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
playwright install chromium
```

### 2. Configure your `.env`

Copy `.env.example` to `.env` and fill in your values:

```
# DMV credentials
DMV_LICENSE=your_license_number
DMV_DOB=MM/DD/YYYY

# Location
DMV_ZIP=your_zip_code
DMV_RADIUS=25

# Gmail — used to send email notifications
GMAIL_ADDRESS=you@gmail.com
GMAIL_APP_PASSWORD=xxxx xxxx xxxx xxxx

# Notification targets
NOTIFY_EMAIL=you@gmail.com

# Pushover — used to send push notifications to your phone
PUSHOVER_USER_KEY=your_pushover_user_key
PUSHOVER_API_TOKEN=your_pushover_api_token

# Supabase
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=your_anon_key
SUPABASE_SERVICE_KEY=your_service_key
```

### 3. Run locally

```bash
python app.py
```

Open `http://127.0.0.1:5000` in your browser.

---

## Gmail app password

Standard Gmail passwords won't work — you need an app-specific password:

1. Go to [myaccount.google.com](https://myaccount.google.com) → Security
2. Enable 2-Step Verification if not already on
3. Search for **App passwords** → create one named `DMV Notifier`
4. Paste the 16-character code as `GMAIL_APP_PASSWORD`

---

## Pushover setup

Pushover sends instant push notifications to your phone — no carrier needed.

1. Download the Pushover app at [pushover.net](https://pushover.net)
2. Create an account and copy your **User Key** from the dashboard
3. Create a new application, name it `DMV Notifier`, copy the **API Token**
4. Add both to your `.env` and to the Notifications section in the web dashboard

---

## Service types

| Value | Description |
|---|---|
| `automobile` | Automobile Drive Test |
| `commercial` | Commercial Drive Test |
| `motorcycle` | Motorcycle Drive Test |
| `realid_cdl` | Real ID & CDL |
| `knowledge` | Knowledge Test Re-evaluation |

---

## Appointment filters

**Time**
- Any time
- Before 12 pm (morning)
- After 12 pm (afternoon)
- Custom range

**Day**
- Any day
- Weekdays only
- Custom days (pick specific days of the week)
- Limit to next N days

**Slots per alert** — choose how many slots to receive per notification (1, 2, 3, 5, 10, or custom)

**Check frequency** — how often to scan for new slots (5 min, 15 min, 30 min, 1 hr, 5 hr, or custom)

**Notify frequency** — how often to actually send alerts (every new slot, once a day, twice a day)

---

## Deploying to Railway

1. Push repo to GitHub
2. Connect to [railway.app](https://railway.app) → New Project → Deploy from GitHub
3. Add all environment variables in the Variables tab
4. Generate a public domain in Settings → Networking

---

## Roadmap

- [ ] Automated DMV login using stored credentials (no manual browser step needed)
- [ ] Support for all California DMV offices statewide
- [ ] Fully multi-user with one always-running server session
- [ ] Mobile-optimized UI