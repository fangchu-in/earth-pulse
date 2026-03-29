Earth Pulse is a personal, hyperlocal environmental observatory built in Baner, Pune at the foothills of the Sahyadris. It brings together air quality, weather, solar radiation, and bird activity into a single continuous dataset, updated in real time.
The system runs on Raspberry Pi devices and uses a combination of open APIs and on-device sensing. Air quality and weather data are sourced from Open-Meteo and logged hourly, while bird activity is captured using a USB microphone and analysed locally using BirdNET, an acoustic AI model that identifies species from sound.
Each detection is timestamped, enriched with environmental context such as AQI and temperature, and stored in a Supabase database. The data is then made publicly accessible through a lightweight web interface hosted on Cloudflare Pages.
The goal is simple: to observe how a small patch of land behaves over time. When the air worsens, do birds go quiet? When the first rains arrive, which species return? When does the dawn chorus peak through the year?
Rather than snapshots, Earth Pulse builds a continuous, living record.

🔍 What it currently tracks
Air Quality (PM2.5, PM10, AQI, gases)
Weather (temperature, humidity, pressure, wind)
Solar radiation (shortwave, direct, diffuse)
Bird detections (species, confidence, timestamps)
Time-of-day patterns (dawn, evening, night activity)

⚙️ Tech stack
Raspberry Pi (Zero 2W + 3B+)
Python (data ingestion, logging, BirdNET integration)
BirdNET (acoustic AI)
Supabase (database + API)
Cloudflare Pages (frontend hosting)
Open-Meteo APIs (climate + air quality)

🌱 Why this exists
Most environmental data is either too broad (city-level) or too sparse. Earth Pulse sits in between, capturing one location in depth, over time.
It is an attempt to make the invisible visible:
how air, weather, and life interact
how patterns emerge across days and seasons
how a place quietly changes!
