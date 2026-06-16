import requests
import openmeteo_requests
import requests_cache
import pandas as pd
from retry_requests import retry
from datetime import datetime, date

GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"

# WMO weather interpretation codes → human-readable description
WMO_CODES = {
    0: "Clear Sky",
    1: "Mainly Clear", 2: "Partly Cloudy", 3: "Overcast",
    45: "Foggy", 48: "Icy Fog",
    51: "Light Drizzle", 53: "Moderate Drizzle", 55: "Dense Drizzle",
    61: "Slight Rain", 63: "Moderate Rain", 65: "Heavy Rain",
    71: "Slight Snowfall", 73: "Moderate Snowfall", 75: "Heavy Snowfall",
    77: "Snow Grains",
    80: "Slight Rain Showers", 81: "Moderate Rain Showers", 82: "Violent Rain Showers",
    85: "Slight Snow Showers", 86: "Heavy Snow Showers",
    95: "Thunderstorm", 96: "Thunderstorm with Hail", 99: "Thunderstorm with Heavy Hail",
}


def _make_client():
    cache_session = requests_cache.CachedSession(".cache", expire_after=1800)
    retry_session = retry(cache_session, retries=3, backoff_factor=0.3)
    return openmeteo_requests.Client(session=retry_session)


def _geocode(city: str) -> tuple[float, float]:
    resp = requests.get(
        GEOCODING_URL,
        params={"name": city, "count": 1, "language": "en", "format": "json"},
        timeout=10,
    )
    resp.raise_for_status()
    results = resp.json().get("results")
    if not results:
        raise ValueError(f"City not found: {city}")
    r = results[0]
    return r["latitude"], r["longitude"]


def get_current_weather(city: str) -> dict:
    lat, lon = _geocode(city)
    client = _make_client()

    responses = client.weather_api(FORECAST_URL, params={
        "latitude": lat,
        "longitude": lon,
        "current": [
            "temperature_2m",
            "apparent_temperature",
            "relative_humidity_2m",
            "wind_speed_10m",
            "weather_code",
        ],
        "timezone": "Asia/Kolkata",
        "forecast_days": 1,
    })

    current = responses[0].Current()
    code = int(current.Variables(4).Value())

    return {
        "city": city,
        "temp": round(current.Variables(0).Value(), 1),
        "feels_like": round(current.Variables(1).Value(), 1),
        "humidity": int(current.Variables(2).Value()),
        "wind_speed": round(current.Variables(3).Value(), 1),
        "description": WMO_CODES.get(code, f"Code {code}"),
    }


def get_todays_forecast(city: str) -> list[dict]:
    lat, lon = _geocode(city)
    client = _make_client()

    responses = client.weather_api(FORECAST_URL, params={
        "latitude": lat,
        "longitude": lon,
        "hourly": [
            "temperature_2m",
            "apparent_temperature",
            "relative_humidity_2m",
            "weather_code",
        ],
        "timezone": "Asia/Kolkata",
        "forecast_days": 1,
    })

    hourly = responses[0].Hourly()
    times = pd.date_range(
        start=pd.Timestamp(hourly.Time(), unit="s", tz="Asia/Kolkata"),
        end=pd.Timestamp(hourly.TimeEnd(), unit="s", tz="Asia/Kolkata"),
        freq=pd.Timedelta(seconds=hourly.Interval()),
        inclusive="left",
    )

    temps = hourly.Variables(0).ValuesAsNumpy()
    feels = hourly.Variables(1).ValuesAsNumpy()
    humidity = hourly.Variables(2).ValuesAsNumpy()
    codes = hourly.Variables(3).ValuesAsNumpy()

    today = date.today()
    forecast = []
    for i, ts in enumerate(times):
        if ts.date() == today:
            code = int(codes[i])
            forecast.append({
                "time": ts.strftime("%I:%M %p"),
                "temp": round(float(temps[i]), 1),
                "feels_like": round(float(feels[i]), 1),
                "humidity": int(humidity[i]),
                "description": WMO_CODES.get(code, f"Code {code}"),
            })

    return forecast
