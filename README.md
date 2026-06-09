# DMV Appointment Notifier

Automatically monitors the California DMV appointment system and sends SMS + email notifications when slots open up near you.

## Features

- Monitors all DMV service types (Drive Test, Real ID, Knowledge Test, etc.)
- Filters by zip code and radius
- Filter appointments by day of week (e.g. only Mon/Wed/Fri)
- Filter appointments by time of day (morning, afternoon, or custom range)
- Limit to appointments within the next N days
- Sends SMS via carrier email gateway (no paid SMS service needed)
- Sends formatted HTML email with one-click booking link
- Deduplication — never sends the same slot twice
- Opt-out support — reply STOP to unsubscribe
- Configurable notification frequency (realtime, once/day, twice/day)
- Configurable check interval (5 min, 30 min, 1 hr, 5 hr)

## Setup

### 1. Clone and install

```bash
git clone https://github.com/yourusername/dmv-notifier.git
cd dmv-notifier
python -m venv venv
source venv/bin/activate
pip install requests playwright geopy python-dotenv certifi
playwright install chromium
```

### 2. Configure your `.env`

```env
# DMV preferences
DMV_LICENSE=A1234567
DMV_DOB=01/15/1990
DMV_ZIP=95035
DMV_RADIUS=25
DMV_SERVICE_TYPE=automobile

# Notification contacts
NOTIFY_PHONE_DIGITS=4085551234
NOTIFY_EMAIL=you@gmail.com
CARRIER=tmomail.net

# Gmail SMTP (for sending SMS + email)
GMAIL_ADDRESS=you@gmail.com
GMAIL_APP_PASSWORD=xxxx xxxx xxxx xxxx

# Scheduling
CHECK_INTERVAL_MINUTES=5
MAX_SLOTS=3
NOTIFY_FREQUENCY=realtime

# Filters (optional)
TIME_FILTER=all
TIME_FROM=00:00
TIME_TO=23:59
DAY_FILTER=all
ALLOWED_DAYS=[0,1,2,3,4]
# WITHIN_DAYS=14
```

### 3. Gmail app password

1. Go to myaccount.google.com → Security
2. Enable 2-Step Verification if not already on
3. Search for "App passwords" → create one named "DMV Notifier"
4. Paste the 16-character code as `GMAIL_APP_PASSWORD`

### 4. Carrier gateway

Set `CARRIER` to your phone carrier's SMS gateway:

| Carrier   | Gateway              |
|-----------|----------------------|
| T-Mobile  | tmomail.net          |
| AT&T      | txt.att.net          |
| Verizon   | vtext.com            |
| Cricket   | sms.cricketwireless.net |
| Mint      | tmomail.net          |

## Service types

Set `DMV_SERVICE_TYPE` to one of:

| Value       | Description                    |
|-------------|--------------------------------|
| automobile  | Automobile Drive Test          |
| commercial  | Commercial Drive Test          |
| motorcycle  | Motorcycle Drive Test          |
| realid_cdl  | Real ID & CDL                  |
| knowledge   | Knowledge Test Re-evaluation   |

## Filter options

### Time filter (`TIME_FILTER`)
- `all` — any time
- `morning` — before 12:00 PM
- `afternoon` — 12:00 PM and later
- `custom` — set `TIME_FROM` and `TIME_TO` (24hr format, e.g. `13:00`)

### Day filter (`DAY_FILTER`)
- `all` — any day
- `weekdays` — Monday through Friday only
- `custom` — set `ALLOWED_DAYS` as JSON array of weekday numbers (0=Mon, 6=Sun)

### Within days (`WITHIN_DAYS`)
Set to a number to only notify about appointments within the next N days.
Leave unset for no limit.

## Running

```bash
python main.py
```

A browser window will open. Click through the DMV booking flow:
1. Select your service type
2. Enter license number and date of birth
3. Click Make an Appointment
4. Enter your zip code
5. Click Select Location on any office

The scraper captures the session data automatically and takes over from there.

## Project structure

```
dmv-notifier/
├── main.py         # entry point and scheduler
├── scraper.py      # DMV scraping (dates + times)
├── geo_filter.py   # radius filtering by zip code
├── database.py     # SQLite operations
├── notify.py       # SMS and email notifications
├── config.py       # service types, constants, defaults
├── .env            # your credentials (never commit this)
└── slots.db        # auto-created SQLite database
```

## Roadmap

- [ ] Web UI for managing preferences without editing .env
- [ ] Multi-user support
- [ ] Support for all California DMV offices (currently Bay Area only)
- [ ] Automatic session renewal without manual browser interaction