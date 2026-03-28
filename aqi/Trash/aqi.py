import requests
import time
import csv
import os
from datetime import datetime

# Location (Pune)
lat = 18.5526156
lon = 73.7818663

# AQI API
aqi_url = f"https://air-quality-api.open-meteo.com/v1/air-quality?latitude={lat}&longitude={lon}&hourly=pm2_5,pm10,european_aqi,nitrogen_dioxide,ozone,carbon_monoxide,sulphur_dioxide,ammonia&timezone=Asia/Kolkata&forecast_days=1"

# Weather + solar API
weather_url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&hourly=temperature_2m,apparent_temperature,relative_humidity_2m,surface_pressure,cloudcover,precipitation,visibility,wind_speed_10m,wind_direction_10m,shortwave_radiation,direct_radiation,diffuse_radiation&timezone=Asia/Kolkata&forecast_days=1"

file_name = "earth_pulse_log.csv"

# Create CSV if not exists
if not os.path.exists(file_name):
    with open(file_name, mode="w", newline="") as file:
        writer = csv.writer(file)
        writer.writerow([
            "time",
            "pm2_5", "pm10", "aqi",
            "no2", "ozone", "co", "so2", "ammonia",
            "temperature", "feels_like", "humidity", "pressure",
            "cloudcover", "precipitation", "visibility",
            "wind_speed", "wind_direction",
            "shortwave_radiation", "direct_radiation", "diffuse_radiation"
        ])

print("🌍 Earth Pulse Logging Started...\n")


def safe_get(data, key, idx):
    try:
        return data["hourly"][key][idx]
    except:
        return None


while True:
    try:
        aqi_data = requests.get(aqi_url, timeout=10).json()
        weather_data = requests.get(weather_url, timeout=10).json()

        current_time = datetime.now().strftime("%Y-%m-%dT%H:00")
        time_list = aqi_data["hourly"]["time"]

        if current_time in time_list:
            idx = time_list.index(current_time)
        else:
            idx = 0

        row = [
            safe_get(aqi_data, "time", idx),

            safe_get(aqi_data, "pm2_5", idx),
            safe_get(aqi_data, "pm10", idx),
            safe_get(aqi_data, "european_aqi", idx),
            safe_get(aqi_data, "nitrogen_dioxide", idx),
            safe_get(aqi_data, "ozone", idx),
            safe_get(aqi_data, "carbon_monoxide", idx),
            safe_get(aqi_data, "sulphur_dioxide", idx),
            safe_get(aqi_data, "ammonia", idx),

            safe_get(weather_data, "temperature_2m", idx),
            safe_get(weather_data, "apparent_temperature", idx),
            safe_get(weather_data, "relative_humidity_2m", idx),
            safe_get(weather_data, "surface_pressure", idx),

            safe_get(weather_data, "cloudcover", idx),
            safe_get(weather_data, "precipitation", idx),
            safe_get(weather_data, "visibility", idx),

            safe_get(weather_data, "wind_speed_10m", idx),
            safe_get(weather_data, "wind_direction_10m", idx),

            safe_get(weather_data, "shortwave_radiation", idx),
            safe_get(weather_data, "direct_radiation", idx),
            safe_get(weather_data, "diffuse_radiation", idx),
        ]

        print("Saved:", row)

        with open(file_name, mode="a", newline="") as file:
            writer = csv.writer(file)
            writer.writerow(row)

    except Exception as e:
        print("Error:", e)

    time.sleep(300)  # every 5 minutes
