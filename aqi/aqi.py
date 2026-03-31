"""
Earth Pulse — AQI & Weather Logger
Runs once per hour via cron. Fetches from Open-Meteo AND Google Air Quality.
Automatically backfills any missing hours (e.g. after power outage).
Pushes to Supabase with upsert — safe to re-run, no duplicates.

Cron:
    0 * * * * /home/fangchu/earth_pulse/venv/bin/python /home/fangchu/earth_pulse/aqi/aqi.py >> /home/fangchu/earth_pulse/aqi/aqi.log 2>&1

Google API key lives ONLY in /home/fangchu/earth_pulse/.env:
    GOOGLE_AQI_KEY=AIza...FaCQ
"""

# ── Imports (ALL at the top — never mid-file) ─────────────────────────────────
import requests
import csv
import os
import datetime
import time
from datetime import timedelta
from zoneinfo import ZoneInfo

# ── Load .env (key never hardcoded here) ─────────────────────────────────────
def load_env(path="/home/fangchu/earth_pulse/.env"):
    env = {}
    try:
        with open(path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    env[k.strip()] = v.strip()
    except FileNotFoundError:
        pass
    return env

_env = load_env()

# ── CONFIG ────────────────────────────────────────────────────────────────────
LAT          = 18.5526156
LON          = 73.7818663
IST          = ZoneInfo("Asia/Kolkata")

SUPABASE_URL = "https://krmczyqwblsoekceanlj.supabase.co"
SUPABASE_KEY = "sb_publishable_DrHFT5J0vmrkYraUXIlpQQ_gsk1rdq6"

# Read Google key from .env — never hardcode it here
GOOGLE_AQI_KEY = _env.get("GOOGLE_AQI_KEY", "")

CSV_BACKUP = os.path.join(os.path.dirname(__file__), "earth_pulse_log.csv")
# ─────────────────────────────────────────────────────────────────────────────

# past_days=2 ensures backfill data is available after short power outages
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

GOOGLE_URL = (
    f"https://airquality.googleapis.com/v1/currentConditions"
    f":lookup?key={GOOGLE_AQI_KEY}"
)


# ── Helpers ───────────────────────────────────────────────────────────────────

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


def get_last_recorded_time():
    """
    Returns the most recent recorded_at from Supabase as an IST-aware datetime.
    Returns None if no records exist or on error.
    """
    try:
        headers = {
            "apikey":        SUPABASE_KEY,
            "Authorization": f"Bearer {SUPABASE_KEY}"
        }
        res  = requests.get(
            f"{SUPABASE_URL}/rest/v1/climate_readings"
            f"?select=recorded_at&order=recorded_at.desc&limit=1",
            headers=headers, timeout=10
        )
        data = res.json()
        if data and isinstance(data, list) and len(data) > 0:
            raw = data[0]["recorded_at"]
            dt  = datetime.datetime.fromisoformat(raw)
            # Attach UTC if naive, then convert to IST
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=datetime.timezone.utc)
            return dt.astimezone(IST)
    except Exception as e:
        print(f"  ⚠️  Could not fetch last record: {e}")
    return None


def fetch_google_aqi():
    """
    Returns (india_aqi_int, dominant_pollutant_str, health_recommendation_str).
    All None if key is missing or API fails — script continues without crashing.
    """
    if not GOOGLE_AQI_KEY:
        print("  ℹ️  No Google AQI key in .env — skipping")
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
        print(f"  ⚠️  Google AQI HTTP {getattr(resp, 'status_code', 'timeout')} — stored as NULL")
        return None, None, None

    try:
        data      = resp.json()
        india_aqi = None
        dominant  = data.get("dominantPollutant")

        # Prefer India AQI standard (code="ind"), fall back to universal (code="uaqi")
        for index in data.get("indexes", []):
            if index.get("code") == "ind":
                india_aqi = index.get("aqi")
                break
        if india_aqi is None:
            for index in data.get("indexes", []):
                if index.get("code") == "uaqi":
                    india_aqi = index.get("aqi")
                    break

        recs       = data.get("healthRecommendations", {})
        health_rec = recs.get("generalPopulation") or recs.get("athletes")

        return india_aqi, dominant, health_rec

    except Exception as e:
        print(f"  ⚠️  Google AQI parse error: {e}")
        return None, None, None


def build_row(idx, aqi_data, weather_data, timestamp,
              google_aqi=None, dominant_pollutant=None, health_rec=None):
    """
    Build a complete Supabase row from API data at position idx.
    timestamp must be a timezone-aware datetime (IST).
    """
    return {
        "recorded_at":           timestamp.isoformat(),
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
        "google_aqi_india":      google_aqi,
        "dominant_pollutant":    dominant_pollutant,
        "health_recommendation": health_rec,
    }


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
                "pm2_5", "pm10", "aqi", "no2", "ozone", "co", "so2", "ammonia",
                "temperature", "feels_like", "humidity", "pressure",
                "cloudcover", "precipitation", "visibility",
                "wind_speed", "wind_direction",
                "solar_radiation", "direct_radiation", "diffuse_radiation",
                "google_aqi_india", "dominant_pollutant", "health_recommendation"
            ])


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    now_ist = datetime.datetime.now(IST)
    print(f"\n🌍 Earth Pulse AQI Logger — {now_ist.strftime('%Y-%m-%d %H:%M IST')}")

    # ── Fetch Open-Meteo (past 2 days gives backfill headroom) ───────────────
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

    # Build lookup dict: IST-aware datetime → array index
    time_list = aqi_data["hourly"]["time"]
    api_index = {
        datetime.datetime.fromisoformat(t).replace(tzinfo=IST): i
        for i, t in enumerate(time_list)
    }

    # Current full hour in IST (e.g. 16:00, 17:00)
    current_hour = now_ist.replace(minute=0, second=0, microsecond=0)

    # ── Backfill missing hours ────────────────────────────────────────────────
    last_time = get_last_recorded_time()

    if last_time is not None:
        # Floor to the hour (remove minutes/seconds from the stored timestamp)
        last_hour = last_time.replace(minute=0, second=0, microsecond=0)
        print(f"  Last DB entry: {last_hour.strftime('%Y-%m-%d %H:%M IST')}")

        # Walk forward from last recorded hour to find gaps
        missing = []
        t = last_hour + timedelta(hours=1)   # ← BUG FIX: was `last`, now `last_hour`
        while t < current_hour:
            missing.append(t)
            t += timedelta(hours=1)

        if missing:
            print(f"  🔄 Backfilling {len(missing)} missing hour(s)…")
            for ts in missing:
                if ts not in api_index:
                    print(f"    ⚠️  No API data for {ts.strftime('%Y-%m-%d %H:%M')} — skipping")
                    continue
                idx = api_index[ts]
                row = build_row(idx, aqi_data, weather_data, ts)
                print(f"    ↩️  {ts.strftime('%Y-%m-%d %H:%M')} | AQI {row['aqi']} | "
                      f"Temp {row['temperature']}°C | Rain {row['precipitation']}mm")
                push_to_supabase(row)
                time.sleep(0.3)   # gentle rate limit
        else:
            print("  ✅ No gaps — database is continuous")
    else:
        print("  ℹ️  No existing records — this may be the first run")

    # ── Current hour — also fetch Google AQI ─────────────────────────────────
    print(f"\n  Fetching Google Air Quality…")
    google_aqi, dominant_pollutant, health_rec = fetch_google_aqi()

    if google_aqi:
        print(f"  Google AQI (India): {google_aqi} | Dominant: {dominant_pollutant}")
    else:
        print("  Google AQI: unavailable — stored as NULL")

    if current_hour not in api_index:
        print(f"  ⚠️  No Open-Meteo data for current hour — skipping push")
        return

    idx = api_index[current_hour]
    row = build_row(idx, aqi_data, weather_data, current_hour,
                    google_aqi, dominant_pollutant, health_rec)

    # ── Print summary ─────────────────────────────────────────────────────────
    print(f"  AQI (EU)   : {row['aqi']} | PM2.5: {row['pm2_5']} | PM10: {row['pm10']}")
    print(f"  AQI (India): {google_aqi or '—'} | Dominant: {dominant_pollutant or '—'}")
    print(f"  Temp       : {row['temperature']}°C (feels {row['feels_like']}°C)")
    print(f"  Humidity   : {row['humidity']}% | Pressure: {row['pressure']} hPa")
    print(f"  Rain       : {row['precipitation']} mm | Cloud: {row['cloudcover']}%")

    push_to_supabase(row)

    # ── CSV local backup ──────────────────────────────────────────────────────
    ensure_csv_header()
    with open(CSV_BACKUP, mode="a", newline="") as f:
        csv.writer(f).writerow(list(row.values()))
    print("  💾 CSV backup: saved\n")


if __name__ == "__main__":
    main()
