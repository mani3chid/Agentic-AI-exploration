import os
import json
import atexit
from flask import Flask, render_template, request, Response, stream_with_context, jsonify
from dotenv import load_dotenv

from states import STATE_CAPITALS
from weather import get_current_weather, get_todays_forecast
from email_sender import send_weather_email
from scheduler import build_scheduler, scheduler_info, SCHEDULE_STATE

load_dotenv()

SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
EMAIL_SENDER = os.getenv("EMAIL_SENDER", "")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD", "")
EMAIL_RECIPIENT = os.getenv("EMAIL_RECIPIENT", "")

STATE_NAMES = sorted(STATE_CAPITALS.keys())

app = Flask(__name__)


# ── Scheduled job ────────────────────────────────────────────────────────────

def _do_send(state: str, label: str = "[SCHEDULER]"):
    city = STATE_CAPITALS[state]
    print(f"{label} Fetching weather for {state} ({city})…")
    try:
        current = get_current_weather(city)
        print(f"{label} {current['temp']}°C — {current['description']}")
        forecast = get_todays_forecast(city)
        print(f"{label} {len(forecast)} hourly forecast entries.")
        send_weather_email(
            state=state, city=city, current=current, forecast=forecast,
            smtp_host=SMTP_HOST, smtp_port=SMTP_PORT,
            sender=EMAIL_SENDER, password=EMAIL_PASSWORD, recipient=EMAIL_RECIPIENT,
        )
        print(f"{label} Email sent to {EMAIL_RECIPIENT}.")
    except Exception as exc:
        print(f"{label} ERROR — {exc}")


def scheduled_job():
    _do_send(SCHEDULE_STATE)


# Start scheduler only in the main process (avoids double-start with reloader)
sched = build_scheduler(scheduled_job)
if not app.debug or os.environ.get("WERKZEUG_RUN_MAIN") == "true":
    sched.start()
    atexit.register(sched.shutdown)


# ── Routes ────────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    info = scheduler_info(sched)
    return render_template("index.html", states=STATE_NAMES, scheduler=info)


@app.route("/scheduler-status")
def scheduler_status():
    return jsonify(scheduler_info(sched))


@app.route("/send")
def send():
    state = request.args.get("state", "").strip()

    def generate():
        if not state or state not in STATE_CAPITALS:
            yield _event("error", "Invalid state selected.")
            return

        city = STATE_CAPITALS[state]
        missing = [k for k, v in {
            "EMAIL_SENDER": EMAIL_SENDER,
            "EMAIL_PASSWORD": EMAIL_PASSWORD,
            "EMAIL_RECIPIENT": EMAIL_RECIPIENT,
        }.items() if not v]
        if missing:
            yield _event("error", f"Missing in .env: {', '.join(missing)}")
            return

        yield _event("log", f"Geocoding {city}…")
        try:
            current = get_current_weather(city)
        except Exception as exc:
            yield _event("error", f"Weather fetch failed: {exc}")
            return

        yield _event("log", f"Current weather: {current['temp']}°C — {current['description']}")

        try:
            forecast = get_todays_forecast(city)
        except Exception as exc:
            yield _event("error", f"Forecast fetch failed: {exc}")
            return

        yield _event("log", f"Fetched {len(forecast)} hourly forecast slots for today.")
        yield _event("log", f"Connecting to SMTP ({SMTP_HOST})…")

        try:
            send_weather_email(
                state=state, city=city, current=current, forecast=forecast,
                smtp_host=SMTP_HOST, smtp_port=SMTP_PORT,
                sender=EMAIL_SENDER, password=EMAIL_PASSWORD, recipient=EMAIL_RECIPIENT,
            )
        except Exception as exc:
            yield _event("error", f"Email send failed: {exc}")
            return

        yield _event("success", f"Email sent to {EMAIL_RECIPIENT} for {state} ({city}).")

    return Response(
        stream_with_context(generate()),
        mimetype="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


def _event(kind: str, msg: str) -> str:
    print(f"[{kind.upper()}] {msg}")
    return f"data: {json.dumps({'type': kind, 'msg': msg})}\n\n"


if __name__ == "__main__":
    app.run(debug=True, port=5001)
