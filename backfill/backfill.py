"""
Earth Pulse — Historical Backfill
Pulls 2022-01-01 to yesterday from Open-Meteo archive and pushes to Supabase.
Run ONCE from your laptop or Pi 3B+:
    python3 backfill.py
Takes ~5-10 minutes. Safe to re-run (upsert on recorded_at).
"""

import requests
import time
from datetime import datetime, timedelta
from supabase import create_client

# ─── CONFIG — same as aqi.py ──────────────────────────────────────────────────
LAT           = 18.5526156
LON           = 73.7818663
SUPABASE_URL  = "https://krmczyqwblsoekceanlj.supabase.co"
SUPABASE_KEY  = "sb_publishable_DrHFT5J0vmrkYraUXIlpQQ_gsk1rdq6"
START_DATE    = "2022-01-01"
END_DATE      = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
BATCH_SIZE    = 500   # rows pushed per Supabase call
# ──────────────────────────────────────────────────────────────────────────────


def fetch_chunk(start, end):
    """Fetch one date range chunk from Open-Meteo archive APIs."""
    aqi_url = (
        f"https://air-quality-api.open-meteo.com/v1/air-quality"
        f"?latitude={LAT}&longitude={LON}"
        f"&hourly=pm2_5,pm10,european_aqi,nitrogen_dioxide,ozone,"
        f"carbon_monoxide,sulphur_dioxide,ammonia"
        f"&timezone=Asia/Kolkata"
        f"&start_date={start}&end_date={end}"
    )
    weather_url = (
        f"https://archive-api.open-meteo.com/v1/archive"
        f"?latitude={LAT}&longitude={LON}"
        f"&hourly=temperature_2m,apparent_temperature,relative_humidity_2m,"
        f"surface_pressure,cloudcover,precipitation,visibility,"
        f"wind_speed_10m,wind_direction_10m,"
        f"shortwave_radiation,direct_radiation,diffuse_radiation"
        f"&timezone=Asia/Kolkata"
        f"&start_date={start}&end_date={end}"
    )
    aqi_data     = requests.get(aqi_url, timeout=30).json()
    weather_data = requests.get(weather_url, timeout=30).json()
    return aqi_data, weather_data


def safe(data, key, idx):
    try:
        v = data["hourly"][key][idx]
        return None if v is None else v
    except Exception:
        return None


def build_rows(aqi_data, weather_data):
    rows = []
    times = aqi_data["hourly"]["time"]
    for idx, t in enumerate(times):
        rows.append({
            "recorded_at":       t,
            "pm2_5":             safe(aqi_data, "pm2_5", idx),
            "pm10":              safe(aqi_data, "pm10", idx),
            "aqi":               safe(aqi_data, "european_aqi", idx),
            "no2":               safe(aqi_data, "nitrogen_dioxide", idx),
            "ozone":             safe(aqi_data, "ozone", idx),
            "co":                safe(aqi_data, "carbon_monoxide", idx),
            "so2":               safe(aqi_data, "sulphur_dioxide", idx),
            "ammonia":           safe(aqi_data, "ammonia", idx),
            "temperature":       safe(weather_data, "temperature_2m", idx),
            "feels_like":        safe(weather_data, "apparent_temperature", idx),
            "humidity":          safe(weather_data, "relative_humidity_2m", idx),
            "pressure":          safe(weather_data, "surface_pressure", idx),
            "cloudcover":        safe(weather_data, "cloudcover", idx),
            "precipitation":     safe(weather_data, "precipitation", idx),
            "visibility":        safe(weather_data, "visibility", idx),
            "wind_speed":        safe(weather_data, "wind_speed_10m", idx),
            "wind_direction":    safe(weather_data, "wind_direction_10m", idx),
            "solar_radiation":   safe(weather_data, "shortwave_radiation", idx),
            "direct_radiation":  safe(weather_data, "direct_radiation", idx),
            "diffuse_radiation": safe(weather_data, "diffuse_radiation", idx),
            "is_holiday":        False,
            "holiday_name":      None,
        })
    return rows


def push_batch(supabase, rows):
    for i in range(0, len(rows), BATCH_SIZE):
        batch = rows[i:i + BATCH_SIZE]
        supabase.table("climate_readings").upsert(
            batch, on_conflict="recorded_at"
        ).execute()
        print(f"    ✅ Pushed {i + len(batch)} / {len(rows)} rows")
        time.sleep(0.5)  # be gentle with API rate limits


def main():
    print(f"\n🌍 Earth Pulse — Historical Backfill")
    print(f"   Period : {START_DATE} → {END_DATE}")
    print(f"   Coords : {LAT}, {LON}\n")

    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

    # Split into 3-month chunks to avoid API response size limits
    start = datetime.strptime(START_DATE, "%Y-%m-%d")
    end   = datetime.strptime(END_DATE, "%Y-%m-%d")

    chunk_start = start
    while chunk_start < end:
        chunk_end = min(chunk_start + timedelta(days=90), end)
        s = chunk_start.strftime("%Y-%m-%d")
        e = chunk_end.strftime("%Y-%m-%d")

        print(f"📦 Fetching {s} → {e} ...")
        try:
            aqi_data, weather_data = fetch_chunk(s, e)
            rows = build_rows(aqi_data, weather_data)
            print(f"   {len(rows)} hourly records fetched")
            push_batch(supabase, rows)
        except Exception as ex:
            print(f"   ❌ Error on chunk {s}→{e}: {ex}")

        chunk_start = chunk_end + timedelta(days=1)
        time.sleep(1)

    print("\n🎉 Backfill complete! Check your Supabase table.")
    print(f"   Total period covered: {START_DATE} → {END_DATE}")


if __name__ == "__main__":
    main()
