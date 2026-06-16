# India Weather Email Automation Tool — Specification

## Overview

A Python Flask web application that lets the user select an Indian state from a dropdown, fetches the current weather and today's forecast for that state's capital city via Open-Meteo (no API key required), and sends a formatted HTML weather email to a configured recipient. The app also supports scheduled email sending for a fixed state over a configurable time window.

---

## Features

### 1. State Selection UI (Web)
- Flask-served HTML page with a dropdown listing all 28 Indian states + 8 Union Territories.
- "Send Weather Email" button triggers a fetch-and-send flow.
- Real-time log panel streams status updates to the browser via Server-Sent Events (SSE).
- Same log lines are echoed to the terminal.

### 2. Weather Data
- **Provider:** Open-Meteo API (free, no API key required).
- **Geocoding:** Open-Meteo Geocoding API resolves city name → lat/lon.
- **Data fetched per state capital:**
  - Current weather: temperature (°C), feels-like (°C), humidity (%), wind speed (km/h), WMO weather description.
  - Today's forecast: hourly temperature, feels-like, humidity, and description for all remaining hours of the day.
- **Libraries:** `openmeteo-requests`, `requests-cache` (30-min cache), `retry-requests`, `numpy`, `pandas`

### 3. Email Composition
- **Library:** `smtplib` + `email.mime` (stdlib).
- Email format: HTML with subject line — `"Weather Report: <State> — <Date>"`.
- Body includes:
  - State name and capital city
  - Current conditions (temp, feels-like, humidity, wind, description)
  - Today's hourly forecast table (time | temp | feels-like | humidity | condition)
- Sender credentials read from `.env` (never hardcoded).

### 4. Scheduled Email Sending *(v2 — added 2026-06-16)*
- A background APScheduler job that sends the Tamil Nadu (Chennai) weather email automatically on a fixed interval within a defined time window.
- **Default schedule:** every **5 minutes** between **12:15 PM and 12:45 PM IST on 2026-06-16 only**. The job does not repeat on subsequent days.
- Scheduler starts automatically when the Flask app starts.
- Each scheduled send is fully logged to the terminal (same log format as manual sends).
- Scheduler stops gracefully when the app shuts down.
- **UI indicator:** the web page shows a "Scheduler active" badge and the next scheduled fire time.
- No email is sent outside the configured time window even if the process is running.

### 5. Configuration (`.env` file)
```
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
EMAIL_SENDER=you@gmail.com
EMAIL_PASSWORD=<16-char Gmail App Password>
EMAIL_RECIPIENT=recipient@example.com

# Scheduler (optional — defaults shown)
SCHEDULE_STATE=Tamil Nadu
SCHEDULE_INTERVAL_MINS=5
SCHEDULE_DATE=2026-06-16         # one-time date only
SCHEDULE_START_TIME=12:15        # 24-hour IST
SCHEDULE_END_TIME=12:45          # 24-hour IST
```

---

## Tech Stack

| Concern | Library |
|---|---|
| Web server | `flask` |
| Real-time log streaming | Server-Sent Events (SSE) via `flask` |
| HTTP requests | `requests` |
| Weather API | `openmeteo-requests`, `requests-cache`, `retry-requests` |
| Data processing | `numpy`, `pandas` |
| Email sending | `smtplib`, `email.mime` (stdlib) |
| Scheduling | `APScheduler` |
| Timezone handling | `pytz` |
| Env config | `python-dotenv` |
| Date/time | `datetime` (stdlib) |

---

## File Structure

```
Agentic-AI-exploration/
├── spec.md                      ← this file
├── weather_email/
│   ├── app.py                   ← Flask app; SSE endpoint; scheduler init
│   ├── weather.py               ← Open-Meteo API calls
│   ├── email_sender.py          ← HTML email composition + SMTP send
│   ├── scheduler.py             ← APScheduler setup and job definition
│   ├── states.py                ← dict mapping state → capital city
│   ├── templates/
│   │   └── index.html           ← web UI with dropdown + live log panel
│   └── .env                     ← secrets (git-ignored)
├── requirements.txt
└── .gitignore
```

---

## Data Flow — Manual Send

```
User selects state in browser
      ↓
GET /send?state=<state>  (SSE stream)
      ↓
weather.py → Open-Meteo geocoding → lat/lon
      ↓
weather.py → Open-Meteo forecast API → current + hourly data
      ↓
email_sender.py → compose HTML → SMTP send
      ↓
SSE events stream log lines to browser log panel
```

## Data Flow — Scheduled Send

```
App starts → scheduler.py initialises APScheduler
      ↓
Every SCHEDULE_INTERVAL_MINS, APScheduler fires job
      ↓
Job checks: is current IST time within [START_TIME, END_TIME]?
  ├─ Yes → fetch weather for SCHEDULE_STATE → send email → log to terminal
  └─ No  → skip silently
```

---

## State → Capital City Mapping (sample)

| State | Capital |
|---|---|
| Andhra Pradesh | Amaravati |
| Assam | Dispur |
| Bihar | Patna |
| Delhi | New Delhi |
| Goa | Panaji |
| Gujarat | Gandhinagar |
| Karnataka | Bengaluru |
| Kerala | Thiruvananthapuram |
| Maharashtra | Mumbai |
| Rajasthan | Jaipur |
| Tamil Nadu | Chennai |
| Uttar Pradesh | Lucknow |
| West Bengal | Kolkata |
| … | … |

Full list in `states.py`.

---

## Error Handling

- Network failure → log error, skip that send cycle (scheduler continues).
- SMTP auth failure → log error in terminal and browser log panel.
- Scheduled job outside time window → silent skip, no log noise.
- Missing `.env` keys → show clear message in browser status log on startup.

---

## Security Notes

- `.env` is listed in `.gitignore`; never committed.
- Gmail requires an **App Password** (2FA must be enabled on the Google account).
- No weather data or email content is logged to disk.

---

## Out of Scope (v2)

- Multiple recipients
- Weather maps or charts
- Mobile/web interface beyond the current Flask UI
- Persistent schedule storage (schedules are in-memory only; restart resets them)
