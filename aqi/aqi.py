"""
Earth Pulse — AQI & Weather Logger
Runs once per hour via cron. Fetches data from Open-Meteo and pushes to Supabase.
Cron entry (run `crontab -e` on Pi 3B+):
    0 * * * * /usr/bin/python3 /home/pi/earth_pulse/aqi/aqi.py >> /home/pi/earth_pulse/aqi/aqi.log 2>&1
"""

import requests
import csv
import os
import sys
import datetime

# ─── CONFIG ─────────────────────────────────────────────
LAT = 18.5526156
LON = 73.7818663

SUPABASE_URL = "https://krmczyqwblsoekceanlj.supabase.co"
SUPABASE_KEY = "sb_publishable_DrHFT5J0vmrkYraUXIlpQQ_gsk1rdq6"

CSV_BACKUP = os.path.join(os.path.dirname(__file__), "earth_pulse_log.csv")
# ───────────────────────────────────────────────────────

AQI_URL = (
    f"https://air-quality-api.open-meteo.com/v1/air-quality"
    f"?latitude={LAT}&longitude={LON}"
    f"&hourly=pm2_5,pm10,european_aqi,nitrogen_dioxide,ozone,"
    f"carbon_monoxide,sulphur_dioxide,ammonia"
    f"&timezone=Asia/Kolkata&forecast_days=1"
)

WEATHER_URL = (
    f"https://api.open-meteo.com/v1/forecast"
    f"?latitude={LAT}&longitude={LON}"
    f"&hourly=temperature_2m,apparent_temperature,relative_humidity_2m,"
    f"surface_pressure,cloudcover,precipitation,visibility,"
    f"wind_speed_10m,wind_direction_10m,"
    f"shortwave_radiation,direct_radiation,diffuse_radiation"
    f"&timezone=Asia/Kolkata&forecast_days=1"
)


def safe_get(data, key, idx):
    try:
        val = data["hourly"][key][idx]
        return None if val is None else val
    except Exception:
        return None


def ensure_csv_header():
    if not os.path.exists(CSV_BACKUP):
        with open(CSV_BACKUP, mode="w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow([
                "recorded_at",
                "pm2_5", "pm10", "aqi",
                "no2", "ozone", "co", "so2", "ammonia",
                "temperature", "feels_like", "humidity", "pressure",
                "cloudcover", "precipitation", "visibility",
                "wind_speed", "wind_direction",
                "solar_radiation", "direct_radiation", "diffuse_radiation"
            ])


def push_to_supabase(row):
    url = f"{SUPABASE_URL}/rest/v1/climate_readings"

    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "resolution=merge-duplicates"
    }

    response = requests.post(url, json=row, headers=headers)

    if response.status_code in [200, 201]:
        print("  ✅ Supabase: saved")
    else:
        print(f"  ⚠️  Supabase push failed: {response.text}")


def main():
    print(f"\n🌍 Earth Pulse AQI Logger — {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}")

    # Fetch data
    try:
        aqi_data = requests.get(AQI_URL, timeout=10).json()
        weather_data = requests.get(WEATHER_URL, timeout=10).json()
    except Exception as e:
        print(f"❌ API fetch failed: {e}")
        sys.exit(1)

    # Current hour
    time_list = aqi_data["hourly"]["time"]
    now = datetime.datetime.now()

    # Convert API times to datetime
    api_times = [datetime.datetime.fromisoformat(t) for t in time_list]

    # Find closest time <= now
    valid_times = [t for t in api_times if t <= now]
    if valid_times:
        closest_time = max(valid_times)
        idx = api_times.index(closest_time)
    else:
        idx = 0
    recorded_at = time_list[idx]

    # Build row
    row = {
        "recorded_at": datetime.datetime.now().astimezone().isoformat(),
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
    }

    print(f"  Time     : {recorded_at}")
    print(f"  AQI      : {row['aqi']} | PM2.5: {row['pm2_5']} | PM10: {row['pm10']}")
    print(f"  Temp     : {row['temperature']}°C (feels {row['feels_like']}°C)")
    print(f"  Humidity : {row['humidity']}% | Pressure: {row['pressure']} hPa")

    # Push to Supabase
    try:
        push_to_supabase(row)
    except Exception as e:
        print(f"  ⚠️  Supabase push failed: {e}")

    # Save CSV backup
    ensure_csv_header()
    with open(CSV_BACKUP, mode="a", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(list(row.values()))

    print("  💾 CSV backup: saved\n")


if __name__ == "__main__":
    main()

