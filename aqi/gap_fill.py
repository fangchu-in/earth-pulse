"""
Earth Pulse — Gap Fill Script
Recovers missing hourly records after power outages, using:
  - Open-Meteo Archive API  (weather + EU AQI — unlimited history)
  - Google Air Quality History API  (India AQI — up to 30 days back)

Run manually anytime:
    source /home/fangchu/earth_pulse/venv/bin/activate
    python /home/fangchu/earth_pulse/aqi/gap_fill.py

Also runs automatically on every reboot (add to crontab):
    @reboot sleep 30 && /home/fangchu/earth_pulse/venv/bin/python /home/fangchu/earth_pulse/aqi/gap_fill.py >> /home/fangchu/earth_pulse/aqi/gap_fill.log 2>&1
"""

import requests
import datetime
import time
from datetime import timedelta
from zoneinfo import ZoneInfo

# ── Load .env ─────────────────────────────────────────────────────────────────
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
GOOGLE_AQI_KEY = _env.get("GOOGLE_AQI_KEY", "")

# How many days back to look for gaps (Google history API supports up to 30)
LOOKBACK_DAYS = 3
# ─────────────────────────────────────────────────────────────────────────────

SUPABASE_HEADERS = {
    "apikey":        SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type":  "application/json",
    "Prefer":        "resolution=merge-duplicates"
}


# ── Supabase helpers ──────────────────────────────────────────────────────────

def get_all_recorded_hours(since_ist):
    """
    Fetch all recorded_at timestamps from Supabase since a given IST datetime.
    Returns a set of IST-aware datetimes floored to the hour.
    """
    since_utc = since_ist.astimezone(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%S') + 'Z'
    recorded = set()
    try:
        res = requests.get(
            f"{SUPABASE_URL}/rest/v1/climate_readings"
            f"?select=recorded_at&recorded_at=gte.{since_utc}&order=recorded_at.asc&limit=5000",
            headers=SUPABASE_HEADERS, timeout=15
        )
        rows = res.json()
        if isinstance(rows, list):
            for row in rows:
                raw = row["recorded_at"]
                dt  = datetime.datetime.fromisoformat(raw)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=datetime.timezone.utc)
                # Floor to hour in IST
                dt_ist = dt.astimezone(IST).replace(minute=0, second=0, microsecond=0)
                recorded.add(dt_ist)
    except Exception as e:
        print(f"  ⚠️  Could not fetch existing records: {e}")
    return recorded


def push_row(row):
    """Upsert a row to Supabase. Returns True on success."""
    try:
        res = requests.post(
            f"{SUPABASE_URL}/rest/v1/climate_readings",
            json=row, headers=SUPABASE_HEADERS, timeout=10
        )
        return res.status_code in [200, 201]
    except Exception as e:
        print(f"  ⚠️  Push error: {e}")
        return False


# ── Open-Meteo Archive ────────────────────────────────────────────────────────

def fetch_openmeteo_archive(start_date_str, end_date_str):
    """
    Fetch historical hourly AQI and weather from Open-Meteo archive APIs.
    start/end_date_str format: 'YYYY-MM-DD'
    Returns (aqi_data, weather_data) dicts or (None, None) on failure.
    """
    aqi_url = (
        f"https://air-quality-api.open-meteo.com/v1/air-quality"
        f"?latitude={LAT}&longitude={LON}"
        f"&hourly=pm2_5,pm10,european_aqi,nitrogen_dioxide,ozone,"
        f"carbon_monoxide,sulphur_dioxide,ammonia"
        f"&timezone=Asia/Kolkata"
        f"&start_date={start_date_str}&end_date={end_date_str}"
    )
    weather_url = (
        f"https://archive-api.open-meteo.com/v1/archive"
        f"?latitude={LAT}&longitude={LON}"
        f"&hourly=temperature_2m,apparent_temperature,relative_humidity_2m,"
        f"surface_pressure,cloudcover,precipitation,visibility,"
        f"wind_speed_10m,wind_direction_10m,"
        f"shortwave_radiation,direct_radiation,diffuse_radiation"
        f"&timezone=Asia/Kolkata"
        f"&start_date={start_date_str}&end_date={end_date_str}"
    )
    try:
        print(f"  Fetching Open-Meteo archive: {start_date_str} → {end_date_str}…")
        aqi_data     = requests.get(aqi_url,     timeout=30).json()
        weather_data = requests.get(weather_url, timeout=30).json()

        # Check for API errors
        if "error" in aqi_data:
            print(f"  ❌ Open-Meteo AQI error: {aqi_data.get('reason', aqi_data)}")
            return None, None
        if "error" in weather_data:
            print(f"  ❌ Open-Meteo weather error: {weather_data.get('reason', weather_data)}")
            return None, None

        return aqi_data, weather_data
    except Exception as e:
        print(f"  ❌ Open-Meteo fetch failed: {e}")
        return None, None


def safe(data, key, idx):
    try:
        v = data["hourly"][key][idx]
        return None if v is None else v
    except Exception:
        return None


# ── Google Air Quality History ────────────────────────────────────────────────

def fetch_google_aqi_history(start_ist, end_ist):
    """
    Fetch Google Air Quality hourly history for a time range.
    Google history API accepts UTC times and returns up to 720 hours (30 days).
    Returns a dict: {IST-aware datetime floored to hour: (india_aqi, dominant, health_rec)}
    """
    if not GOOGLE_AQI_KEY:
        print("  ℹ️  No Google AQI key — skipping Google history")
        return {}

    # Google wants UTC ISO 8601 with 'Z' suffix
    start_utc = start_ist.astimezone(datetime.timezone.utc)
    end_utc   = end_ist.astimezone(datetime.timezone.utc)

    url  = f"https://airquality.googleapis.com/v1/history:lookup?key={GOOGLE_AQI_KEY}"
    body = {
        "location": {"latitude": LAT, "longitude": LON},
        "period": {
            "startTime": start_utc.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "endTime":   end_utc.strftime("%Y-%m-%dT%H:%M:%SZ"),
        },
        "extraComputations": [
            "HEALTH_RECOMMENDATIONS",
            "DOMINANT_POLLUTANT_CONCENTRATION",
            "LOCAL_AQI"
        ],
        "pageSize": 720,   # max allowed
        "languageCode": "en"
    }

    results = {}
    page_token = None
    page = 0

    while True:
        if page_token:
            body["pageToken"] = page_token
        elif "pageToken" in body:
            del body["pageToken"]

        try:
            resp = requests.post(url, json=body, timeout=30)
        except Exception as e:
            print(f"  ⚠️  Google history request failed: {e}")
            break

        if resp.status_code != 200:
            print(f"  ⚠️  Google history HTTP {resp.status_code}: {resp.text[:200]}")
            break

        data = resp.json()
        hours_data = data.get("hoursInfo", [])
        page += 1
        print(f"  ☁️  Google history page {page}: {len(hours_data)} hours")

        for hour_info in hours_data:
            # Parse the hour's datetime
            dt_str = hour_info.get("dateTime", "")
            if not dt_str:
                continue
            try:
                dt_utc = datetime.datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
                dt_ist = dt_utc.astimezone(IST).replace(minute=0, second=0, microsecond=0)
            except Exception:
                continue

            # Extract India AQI
            india_aqi = None
            dominant  = None
            for index in hour_info.get("indexes", []):
                if index.get("code") == "ind":
                    india_aqi = index.get("aqi")
                    break
            if india_aqi is None:
                for index in hour_info.get("indexes", []):
                    if index.get("code") == "uaqi":
                        india_aqi = index.get("aqi")
                        break

            dominant  = hour_info.get("dominantPollutant")
            recs      = hour_info.get("healthRecommendations", {})
            health    = recs.get("generalPopulation") or recs.get("athletes")

            results[dt_ist] = (india_aqi, dominant, health)

        # Handle pagination
        page_token = data.get("nextPageToken")
        if not page_token:
            break

    print(f"  ☁️  Google history total: {len(results)} hours fetched")
    return results


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    now_ist = datetime.datetime.now(IST)
    print(f"\n🔄 Earth Pulse Gap Fill — {now_ist.strftime('%Y-%m-%d %H:%M IST')}")

    # ── Find the gap window ───────────────────────────────────────────────────
    lookback_start = (now_ist - timedelta(days=LOOKBACK_DAYS)).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    current_hour = now_ist.replace(minute=0, second=0, microsecond=0)

    print(f"  Scanning for gaps: {lookback_start.strftime('%Y-%m-%d')} → now")

    # ── Get all hours we already have in the DB ───────────────────────────────
    recorded_hours = get_all_recorded_hours(lookback_start)
    print(f"  Found {len(recorded_hours)} existing records in this window")

    # ── Build list of ALL expected hours in the window ────────────────────────
    all_expected = set()
    t = lookback_start
    while t < current_hour:
        all_expected.add(t)
        t += timedelta(hours=1)

    # ── Find missing hours ────────────────────────────────────────────────────
    missing_hours = sorted(all_expected - recorded_hours)

    if not missing_hours:
        print("  ✅ No gaps found — database is complete for the last 3 days")
        return

    print(f"\n  ⚠️  Found {len(missing_hours)} missing hours:")
    for h in missing_hours:
        print(f"    • {h.strftime('%Y-%m-%d %H:%M IST')}")

    # ── Fetch Open-Meteo archive for the full window ──────────────────────────
    start_str = lookback_start.strftime("%Y-%m-%d")
    end_str   = now_ist.strftime("%Y-%m-%d")
    aqi_data, weather_data = fetch_openmeteo_archive(start_str, end_str)

    if aqi_data is None:
        print("  ❌ Cannot fill gaps without Open-Meteo data. Try again later.")
        return

    # Build lookup: IST hour → array index
    time_list = aqi_data["hourly"]["time"]
    api_index = {}
    for i, t_str in enumerate(time_list):
        dt = datetime.datetime.fromisoformat(t_str).replace(tzinfo=IST)
        api_index[dt] = i

    # ── Fetch Google AQI history for the gap window ───────────────────────────
    first_missing = missing_hours[0]
    last_missing  = missing_hours[-1] + timedelta(hours=1)
    print(f"\n  Fetching Google AQI history: {first_missing.strftime('%Y-%m-%d %H:%M')} → {last_missing.strftime('%Y-%m-%d %H:%M')}…")
    google_history = fetch_google_aqi_history(first_missing, last_missing)

    # ── Fill each missing hour ────────────────────────────────────────────────
    print(f"\n  Filling {len(missing_hours)} missing hours…")
    filled  = 0
    skipped = 0

    for ts in missing_hours:
        if ts not in api_index:
            print(f"  ⚠️  No Open-Meteo data for {ts.strftime('%Y-%m-%d %H:%M')} — skipping")
            skipped += 1
            continue

        idx = api_index[ts]

        # Get Google AQI for this hour if available
        g_aqi, g_dominant, g_health = google_history.get(ts, (None, None, None))

        row = {
            "recorded_at":           ts.isoformat(),
            "pm2_5":                 safe(aqi_data,     "pm2_5",              idx),
            "pm10":                  safe(aqi_data,     "pm10",               idx),
            "aqi":                   safe(aqi_data,     "european_aqi",       idx),
            "no2":                   safe(aqi_data,     "nitrogen_dioxide",   idx),
            "ozone":                 safe(aqi_data,     "ozone",              idx),
            "co":                    safe(aqi_data,     "carbon_monoxide",    idx),
            "so2":                   safe(aqi_data,     "sulphur_dioxide",    idx),
            "ammonia":               safe(aqi_data,     "ammonia",            idx),
            "temperature":           safe(weather_data, "temperature_2m",     idx),
            "feels_like":            safe(weather_data, "apparent_temperature",idx),
            "humidity":              safe(weather_data, "relative_humidity_2m",idx),
            "pressure":              safe(weather_data, "surface_pressure",   idx),
            "cloudcover":            safe(weather_data, "cloudcover",         idx),
            "precipitation":         safe(weather_data, "precipitation",      idx),
            "visibility":            safe(weather_data, "visibility",         idx),
            "wind_speed":            safe(weather_data, "wind_speed_10m",     idx),
            "wind_direction":        safe(weather_data, "wind_direction_10m", idx),
            "solar_radiation":       safe(weather_data, "shortwave_radiation",idx),
            "direct_radiation":      safe(weather_data, "direct_radiation",   idx),
            "diffuse_radiation":     safe(weather_data, "diffuse_radiation",  idx),
            "google_aqi_india":      g_aqi,
            "dominant_pollutant":    g_dominant,
            "health_recommendation": g_health,
        }

        rain   = row.get("precipitation") or 0
        temp   = row.get("temperature")
        aqi_eu = row.get("aqi")
        g_str  = f" | Google AQI (India): {g_aqi}" if g_aqi else ""

        if push_row(row):
            filled += 1
            rain_icon = " 🌧️" if rain > 0 else ""
            print(f"  ✅ {ts.strftime('%Y-%m-%d %H:%M IST')} | "
                  f"AQI(EU): {aqi_eu} | Temp: {temp}°C | Rain: {rain}mm{rain_icon}{g_str}")
        else:
            print(f"  ❌ Failed to push {ts.strftime('%Y-%m-%d %H:%M IST')}")
            skipped += 1

        time.sleep(0.25)   # gentle Supabase rate limit

    print(f"\n  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print(f"  Gap fill complete.")
    print(f"  ✅ Filled  : {filled} hours")
    print(f"  ⚠️  Skipped : {skipped} hours")
    if google_history:
        print(f"  ☁️  Google  : {len(google_history)} hours of India AQI recovered")
    print(f"  Earth Pulse database is now continuous 🌍\n")


if __name__ == "__main__":
    main()
