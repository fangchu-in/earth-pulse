"""
Earth Pulse — AQI & Weather Logger
Runs once per hour via cron. Fetches from Open-Meteo AND Google Air Quality.
Pushes to Supabase with upsert (safe to re-run, no duplicates).

Cron entry (run `crontab -e` on Pi 3B+):
    0 * * * * /home/fangchu/earth_pulse/venv/bin/python /home/fangchu/earth_pulse/aqi/aqi.py >> /home/fangchu/earth_pulse/aqi/aqi.log 2>&1
"""

import requests
import csv
import os
import datetime
import time

# ─── CONFIG ───────────────────────────────────────────────────────────────────
LAT          = 18.5526156
LON          = 73.7818663

SUPABASE_URL = "https://krmczyqwblsoekceanlj.supabase.co"
SUPABASE_KEY = "sb_publishable_DrHFT5J0vmrkYraUXIlpQQ_gsk1rdq6"

# Google Air Quality API key — ends in FaCQ
# Restrict this key in GCP console: Air Quality API only + Pi IP 192.168.68.53
# NEVER commit the full key to GitHub — keep this file out of git or use .env
GOOGLE_AQI_KEY = "AIzaSyAIN9_Jcf62hLmoJA7i-7wTQas1PADFaCQ"

CSV_BACKUP = os.path.join(os.path.dirname(__file__), "earth_pulse_log.csv")
# ──────────────────────────────────────────────────────────────────────────────

AQI_URL = (
    f"https://air-quality-api.open-meteo.com/v1/air-quality"
    f"?latitude={LAT}&longitude={LON}"
    f"&hourly=pm2_5,pm10,european_aqi,nitrogen_dioxide,ozone,"
    f"carbon_monoxide,sulphur_dioxide,ammonia"
    f"&timezone=Asia/Kolkata&past_days=2&forecast_days=1"
)

WEATHER_URL = (
    f"https://api.open-meteo.com/v1/forecast"
    f"?latitude={LAT}&longitude={LON}"
    f"&hourly=temperature_2m,apparent_temperature,relative_humidity_2m,"
    f"surface_pressure,cloudcover,precipitation,visibility,"
    f"wind_speed_10m,wind_direction_10m,"
    f"shortwave_radiation,direct_radiation,diffuse_radiation"
    f"&timezone=Asia/Kolkata&past_days=2&forecast_days=1"
)

GOOGLE_URL = f"https://airquality.googleapis.com/v1/currentConditions:lookup?key={GOOGLE_AQI_KEY}"


def fetch_with_retry(url, method="get", json_body=None, retries=3):
    for i in range(retries):
        try:
            if method == "post":
                return requests.post(url, json=json_body, timeout=10)
            return requests.get(url, timeout=10)
        except Exception as e:
            print(f"  ⚠️  Retry {i+1}: {e}")
            time.sleep(2)
    return None


def safe_get(data, key, idx):
    try:
        val = data["hourly"][key][idx]
        return None if val is None else val
    except Exception:
        return None


def fetch_google_aqi():
    """
    Call Google Air Quality API for current conditions.
    Returns (india_aqi_int, dominant_pollutant_str, health_recommendation_str).
    All values are None if API call fails or key is not set.
    """
    if not GOOGLE_AQI_KEY or "YOUR_FULL" in GOOGLE_AQI_KEY:
        return None, None, None

    body = {
        "location": {"latitude": LAT, "longitude": LON},
        "extraComputations": [
            "HEALTH_RECOMMENDATIONS",
            "DOMINANT_POLLUTANT_CONCENTRATION",
            "LOCAL_AQI"
        ],
        "languageCode": "en"
    }

    resp = fetch_with_retry(GOOGLE_URL, method="post", json_body=body)
    if resp is None or resp.status_code != 200:
        print(f"  ⚠️  Google AQI: HTTP {getattr(resp,'status_code','timeout')}")
        return None, None, None

    try:
        data          = resp.json()
        india_aqi     = None
        dominant      = data.get("dominantPollutant")

        # Google returns multiple AQI indexes — find India's (code = "ind")
        for index in data.get("indexes", []):
            if index.get("code") == "ind":
                india_aqi = index.get("aqi")
                break
        # Fallback to universal AQI if India index not returned
        if india_aqi is None:
            for index in data.get("indexes", []):
                if index.get("code") == "uaqi":
                    india_aqi = index.get("aqi")
                    break

        # Health recommendation — use general population advice
        recs       = data.get("healthRecommendations", {})
        health_rec = recs.get("generalPopulation") or recs.get("athletes")

        return india_aqi, dominant, health_rec

    except Exception as e:
        print(f"  ⚠️  Google AQI parse error: {e}")
        return None, None, None


def push_to_supabase(row):
    headers = {
        "apikey":        SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type":  "application/json",
        "Prefer":        "resolution=merge-duplicates"
    }
    response = requests.post(
        f"{SUPABASE_URL}/rest/v1/climate_readings",
        json=row, headers=headers, timeout=10
    )
    if response.status_code in [200, 201]:
        print("  ✅ Supabase: saved")
    else:
        print(f"  ⚠️  Supabase failed ({response.status_code}): {response.text[:200]}")


def ensure_csv_header():
    if not os.path.exists(CSV_BACKUP):
        with open(CSV_BACKUP, mode="w", newline="") as f:
            csv.writer(f).writerow([
                "recorded_at",
                "pm2_5", "pm10", "aqi",
                "no2", "ozone", "co", "so2", "ammonia",
                "temperature", "feels_like", "humidity", "pressure",
                "cloudcover", "precipitation", "visibility",
                "wind_speed", "wind_direction",
                "solar_radiation", "direct_radiation", "diffuse_radiation",
                "google_aqi_india", "dominant_pollutant", "health_recommendation"
            ])

def get_last_recorded_time():
    try:
        headers = {
            "apikey": SUPABASE_KEY,
            "Authorization": f"Bearer {SUPABASE_KEY}"
        }

        res = requests.get(
            f"{SUPABASE_URL}/rest/v1/climate_readings"
            "?select=recorded_at&order=recorded_at.desc&limit=1",
            headers=headers,
            timeout=10
        )

        data = res.json()
        if data:
            return datetime.datetime.fromisoformat(data[0]["recorded_at"])
        return None

    except Exception as e:
        print(f"⚠️ Could not fetch last record: {e}")
        return None

from datetime import timedelta
from zoneinfo import ZoneInfo

def build_row_for_index(idx, aqi_data, weather_data, timestamp, include_google=False):
    """Reuses your exact row-building logic"""

    google_aqi = None
    dominant_pollutant = None
    health_rec = None

    if include_google:
        google_aqi, dominant_pollutant, health_rec = fetch_google_aqi()

    return {
        "recorded_at": timestamp.isoformat(),

        "pm2_5": safe_get(aqi_data, "pm2_5", idx),
        "pm10": safe_get(aqi_data, "pm10", idx),
        "aqi": safe_get(aqi_data, "european_aqi", idx),
        "no2": safe_get(aqi_data, "nitrogen_dioxide", idx),
        "ozone": safe_get(aqi_data, "ozone", idx),
        "co": safe_get(aqi_data, "carbon_monoxide", idx),
        "so2": safe_get(aqi_data, "sulphur_dioxide", idx),
        "ammonia": safe_get(aqi_data, "ammonia", idx),

        "temperature": safe_get(weather_data, "temperature_2m", idx),
        "feels_like": safe_get(weather_data, "apparent_temperature", idx),
        "humidity": safe_get(weather_data, "relative_humidity_2m", idx),
        "pressure": safe_get(weather_data, "surface_pressure", idx),

        "cloudcover": safe_get(weather_data, "cloudcover", idx),
        "precipitation": safe_get(weather_data, "precipitation", idx),
        "visibility": safe_get(weather_data, "visibility", idx),

        "wind_speed": safe_get(weather_data, "wind_speed_10m", idx),
        "wind_direction": safe_get(weather_data, "wind_direction_10m", idx),

        "solar_radiation": safe_get(weather_data, "shortwave_radiation", idx),
        "direct_radiation": safe_get(weather_data, "direct_radiation", idx),
        "diffuse_radiation": safe_get(weather_data, "diffuse_radiation", idx),

        "google_aqi_india": google_aqi,
        "dominant_pollutant": dominant_pollutant,
        "health_recommendation": health_rec,
    }

def main():
    now = datetime.datetime.now(ZoneInfo("Asia/Kolkata"))
    print(f"\n🌍 Earth Pulse AQI Logger — {now.strftime('%Y-%m-%d %H:%M')}")

    # ── Open-Meteo ────────────────────────────────────────────────────────────
    aqi_response     = fetch_with_retry(AQI_URL)
    weather_response = fetch_with_retry(WEATHER_URL)

    if aqi_response is None or weather_response is None:
        print("❌ Open-Meteo failed after retries. Aborting.")
        return

    try:
        aqi_data     = aqi_response.json()
        weather_data = weather_response.json()
    except Exception as e:
        print(f"❌ JSON parsing failed: {e}")
        return

    # ── BACKFILL (NEW) ─────────────────────────────────────────────
    time_list = aqi_data["hourly"]["time"]
    api_times = [
    datetime.datetime.fromisoformat(t).replace(tzinfo=ZoneInfo("Asia/Kolkata"))
    for t in time_list
]

    now_ist = datetime.datetime.now(ZoneInfo("Asia/Kolkata"))
    current_hour = now_ist.replace(minute=0, second=0, microsecond=0)

    last_time = get_last_recorded_time()

    if last_time:
        last_time = last_time.astimezone(ZoneInfo("Asia/Kolkata"))

        # 🔥 CRITICAL FIX
        last_time = last_time.replace(minute=0, second=0, microsecond=0)

        print(f"🔎 Last DB entry: {last_time}")

        missing_hours = []
        t = last + timedelta(hours=1)
        t = t.replace(minute=0, second=0, microsecond=0)

        while t < current_hour:
            missing_hours.append(t)
            t += timedelta(hours=1)

        if missing_hours:
            print(f"🔄 Backfilling {len(missing_hours)} hours...")

            for ts in missing_hours:
                try:
                    idx = api_times.index(ts)
                except ValueError:
                    print(f"  ⚠️ Missing API data for {ts}")
                    continue

                row = build_row_for_index(idx, aqi_data, weather_data, ts)
                push_to_supabase(row)

        else:
            print("✅ No backfill needed")

    # Match current time to nearest API hour
    time_list   = aqi_data["hourly"]["time"]
    api_times = [
    datetime.datetime.fromisoformat(t).replace(tzinfo=ZoneInfo("Asia/Kolkata"))
    for t in time_list
]
    valid_times = [t for t in api_times if t <= now]
    idx         = api_times.index(max(valid_times)) if valid_times else 0
    recorded_at = now.astimezone().isoformat()

    # ── Google Air Quality ────────────────────────────────────────────────────
    print("  Fetching Google Air Quality…")
    google_aqi, dominant_pollutant, health_rec = fetch_google_aqi()
    if google_aqi:
        print(f"  Google AQI @ ({LAT}, {LON}): {google_aqi} | Dominant: {dominant_pollutant}")
    else:
        print("  Google AQI: unavailable — stored as NULL")

    # ── Build row (all existing + 3 new Google columns) ───────────────────────
    row = {
        "recorded_at":           recorded_at,
        "pm2_5":                 safe_get(aqi_data, "pm2_5", idx),
        "pm10":                  safe_get(aqi_data, "pm10", idx),
        "aqi":                   safe_get(aqi_data, "european_aqi", idx),
        "no2":                   safe_get(aqi_data, "nitrogen_dioxide", idx),
        "ozone":                 safe_get(aqi_data, "ozone", idx),
        "co":                    safe_get(aqi_data, "carbon_monoxide", idx),
        "so2":                   safe_get(aqi_data, "sulphur_dioxide", idx),
        "ammonia":               safe_get(aqi_data, "ammonia", idx),
        "temperature":           safe_get(weather_data, "temperature_2m", idx),
        "feels_like":            safe_get(weather_data, "apparent_temperature", idx),
        "humidity":              safe_get(weather_data, "relative_humidity_2m", idx),
        "pressure":              safe_get(weather_data, "surface_pressure", idx),
        "cloudcover":            safe_get(weather_data, "cloudcover", idx),
        "precipitation":         safe_get(weather_data, "precipitation", idx),
        "visibility":            safe_get(weather_data, "visibility", idx),
        "wind_speed":            safe_get(weather_data, "wind_speed_10m", idx),
        "wind_direction":        safe_get(weather_data, "wind_direction_10m", idx),
        "solar_radiation":       safe_get(weather_data, "shortwave_radiation", idx),
        "direct_radiation":      safe_get(weather_data, "direct_radiation", idx),
        "diffuse_radiation":     safe_get(weather_data, "diffuse_radiation", idx),
        # ── NEW: Google AQI columns ──
        "google_aqi_india":      google_aqi,
        "dominant_pollutant":    dominant_pollutant,
        "health_recommendation": health_rec,
    }

    # ── Print ─────────────────────────────────────────────────────────────────
    print(f"  AQI (EU)   : {row['aqi']} | PM2.5: {row['pm2_5']} | PM10: {row['pm10']}")
    print(f"  AQI (India): {google_aqi or '—'} | Dominant pollutant: {dominant_pollutant or '—'}")
    print(f"  Temp       : {row['temperature']}°C (feels {row['feels_like']}°C)")
    print(f"  Humidity   : {row['humidity']}% | Pressure: {row['pressure']} hPa")
    print(f"  Rain       : {row['precipitation']} mm | Cloud: {row['cloudcover']}%")

    # ── Push & backup ─────────────────────────────────────────────────────────
    push_to_supabase(row)
    ensure_csv_header()
    with open(CSV_BACKUP, mode="a", newline="") as f:
        csv.writer(f).writerow(list(row.values()))
    print("  💾 CSV backup: saved\n")


if __name__ == "__main__":
    main()
