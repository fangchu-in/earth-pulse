# Earth Pulse — Node Setup Guide
**Connecting a Raspberry Pi to the Earth Pulse environmental network**
*Baner, Pune · earthpulse.pages.dev · Updated April 2026*

---

## What is Earth Pulse?

Earth Pulse is an open citizen science environmental observatory on the edge of the Western Ghats, Pune. It monitors air quality, microclimate, acoustic bird biodiversity, and soundscape health — continuously, since January 2022.

Every node you add extends the network's spatial coverage. Your data appears on the live website, contributes to the historical archive, and is freely available under CC BY 4.0.

**Current network:** 1 active node (Baner Hill, 18.55°N 73.78°E, 560m)

---

## What you need

| Item | Purpose | Est. cost |
|------|---------|-----------|
| Raspberry Pi 3B or 3B+ | Main computer | ₹3,500–4,500 (or refurbished ₹1,500) |
| MicroSD card, 32GB Class 10 | OS + storage | ₹350–500 |
| USB microphone (cardioid) | BirdNET + soundscape | ₹800–1,200 |
| SDS011 PM2.5/PM10 sensor | Air quality | ₹1,400–1,800 |
| USB-to-serial adapter (CH340) | Connect SDS011 | ₹150 |
| Pi Camera Module v2 or v3 | Timelapse (optional) | ₹800–1,500 |
| 5V 3A USB-C power supply | Power | ₹350–500 |
| Weatherproof enclosure | Protection outdoors | ₹200–500 |
| Small heatsink kit | Thermal management | ₹80 |

**Minimum viable node (mic only):** Pi + mic + SD card + PSU ≈ ₹5,000

---

## Step 1 — Flash the OS

1. Download **Raspberry Pi Imager** from raspberrypi.com/software
2. Select OS: **Raspberry Pi OS Lite (64-bit)** — no desktop needed
3. Click the ⚙️ gear icon before flashing:
   - Set hostname: `earthpulse-node-[yourcity]` e.g. `earthpulse-node-pashan`
   - Enable SSH
   - Set username: `pi` (or your name)
   - Set Wi-Fi SSID and password
4. Flash to SD card, insert into Pi, power on
5. Find the Pi's IP on your router, then connect:

```bash
ssh pi@192.168.x.x
```

---

## Step 2 — Initial Pi setup

```bash
# Update everything
sudo apt update && sudo apt upgrade -y

# Install system dependencies
sudo apt install -y python3-pip python3-venv git ffmpeg libportaudio2

# Create project directory
mkdir -p /home/pi/earth_pulse/{aqi,audio,logs}
cd /home/pi/earth_pulse

# Create Python virtual environment
python3 -m venv venv
source venv/bin/activate

# Install Python packages
pip install requests numpy scipy soundfile tflite-runtime
```

---

## Step 3 — Clone the Earth Pulse repository

```bash
cd /home/pi/earth_pulse
git clone https://github.com/fangchu-in/earth-pulse .
```

---

## Step 4 — Create your .env credentials file

```bash
nano /home/pi/earth_pulse/.env
```

Add these lines (get values from the Earth Pulse admin — contact fangchu@gmail.com):

```
# Supabase — shared database for all nodes
SUPABASE_URL=https://krmczyqwblsoekceanlj.supabase.co
SUPABASE_KEY=sb_publishable_DrHFT5J0vmrkYraUXIlpQQ_gsk1rdq6

# Google Air Quality API (get free key at console.cloud.google.com)
GOOGLE_AQI_KEY=your_google_key_here

# Your node identity — used to tag all your data in the database
NODE_ID=pashan_01          # unique ID: cityname_number
NODE_LAT=18.5272           # your exact latitude
NODE_LON=73.8078           # your exact longitude
NODE_ELEVATION=560         # metres above sea level
NODE_LOCATION=Pashan, Pune # human-readable location name
```

**Security note:** This file contains API keys. Never commit it to GitHub. The `.gitignore` already excludes it.

---

## Step 5 — Test your microphone

```bash
# List audio devices
arecord -l

# You should see your USB mic listed as card 1 or 2
# Test a 5-second recording
arecord -D plughw:1,0 -f S16_LE -r 48000 -c 1 -d 5 test.wav

# Play it back to verify
aplay test.wav
```

Note your microphone card number (e.g. `plughw:1,0`) — you'll need it in the config.

---

## Step 6 — Set up BirdNET acoustic monitoring

BirdNET is an AI model that identifies birds from audio. It runs entirely on the Pi — no internet needed for detections.

```bash
cd /home/pi/earth_pulse
source venv/bin/activate

# Download BirdNET-Analyzer
git clone https://github.com/kahst/BirdNET-Analyzer.git
cd BirdNET-Analyzer
pip install -r requirements.txt

# Test with your microphone
python3 analyze.py --i test.wav --lat 18.55 --lon 73.78 --week -1
```

The BirdNET script (`birdnet.py` in the repo) records 15-second audio clips every 15 minutes and pushes detections to Supabase with your `NODE_ID` tagged to every row.

---

## Step 7 — Set up NDSI Soundscape Index (optional but valuable)

The Normalized Difference Soundscape Index measures ecosystem health acoustically — ratio of natural sounds (birds, insects, rain) to human noise (traffic, construction).

```bash
pip install librosa
```

The `soundscape.py` script in the repo computes NDSI from the same audio clips as BirdNET — no extra hardware needed.

---

## Step 8 — Set up SDS011 air quality sensor

```bash
# Check the sensor appears as a serial device
ls /dev/ttyUSB*
# Should show /dev/ttyUSB0

# Test it
pip install pyserial
python3 -c "
import serial, time
s = serial.Serial('/dev/ttyUSB0', 9600)
time.sleep(2)
data = s.read(10)
pm25 = int.from_bytes(data[2:4], 'little') / 10
pm10 = int.from_bytes(data[4:6], 'little') / 10
print(f'PM2.5: {pm25} µg/m³  PM10: {pm10} µg/m³')
"
```

---

## Step 9 — Run the setup script

```bash
cd /home/pi/earth_pulse
source venv/bin/activate
bash setup.sh
```

This script:
- Validates your `.env` file
- Tests Supabase connectivity
- Verifies mic is detected
- Tests SDS011 if connected
- Installs all cron jobs

---

## Step 10 — Install cron jobs

```bash
crontab -e
```

Add these lines:

```cron
# Environment — load .env for all cron jobs
BASH_ENV=/home/pi/earth_pulse/.env

# AQI + weather logger — every hour on the hour
0 * * * * /home/pi/earth_pulse/venv/bin/python3 /home/pi/earth_pulse/aqi/aqi.py >> /home/pi/earth_pulse/logs/aqi.log 2>&1

# BirdNET acoustic detection — every 15 minutes
*/15 * * * * /home/pi/earth_pulse/venv/bin/python3 /home/pi/earth_pulse/audio/birdnet.py >> /home/pi/earth_pulse/logs/birdnet.log 2>&1

# Soundscape index (NDSI) — every 30 minutes
*/30 * * * * /home/pi/earth_pulse/venv/bin/python3 /home/pi/earth_pulse/audio/soundscape.py >> /home/pi/earth_pulse/logs/ndsi.log 2>&1

# Gap fill — daily at 2am (backfills missed readings after power failures)
0 2 * * * /home/pi/earth_pulse/venv/bin/python3 /home/pi/earth_pulse/aqi/gap_fill.py >> /home/pi/earth_pulse/logs/gapfill.log 2>&1

# Optional: Pi Camera timelapse — every 3 hours during daylight (6am–6pm)
0 6,9,12,15,18 * * * /home/pi/earth_pulse/venv/bin/python3 /home/pi/earth_pulse/camera/timelapse.py >> /home/pi/earth_pulse/logs/camera.log 2>&1
```

---

## Step 11 — Register your node

Email **fangchu@gmail.com** with:
- Your `NODE_ID`
- Location name and coordinates
- What sensors you have (mic, SDS011, camera)
- A photo of your setup if possible

We'll add your node to the Earth Pulse map on the website and confirm your data is flowing correctly.

---

## Step 12 — Verify data is arriving

Check your node's data in Supabase:

- Climate readings: `https://earthpulse.pages.dev/data.html` → login → Explorer
- Bird detections: `https://earthpulse.pages.dev/birds.html`
- Admin (network owner only): `https://earthpulse.pages.dev/admin.html`

You can also query directly:
```
https://krmczyqwblsoekceanlj.supabase.co/rest/v1/bird_detections?node_id=eq.pashan_01&limit=10
```

---

## Placement guidelines

**Microphone:**
- Mount outdoors, ideally on a wall or railing
- Point toward vegetation / trees, not road traffic
- Minimum 2m above ground
- Shelter from direct rain (small overhang or mesh cover)
- Avoid pointing toward AC units, generators, or machinery

**SDS011 (PM sensor):**
- Mount outdoors in shade — direct sunlight affects readings
- Horizontal orientation, intake facing down
- Away from cooking exhausts and vehicle exhausts
- The sensor needs ~30 seconds warmup before each reading

**Pi Camera (if used):**
- South-facing if possible (towards hills/nature)
- Fixed, stable mount — vibration blurs timelapses
- Lens sheltered from rain but with clear view

**Pi itself:**
- Keep indoors or in weatherproof enclosure
- Ventilated — the Pi 3B runs warm
- UPS or battery backup recommended — even a phone powerbank extends uptime during power cuts

---

## Troubleshooting

**Cron jobs not running:**
```bash
systemctl status cron
grep CRON /var/log/syslog | tail -20
```

**Mic not detected:**
```bash
lsusb        # check USB mic appears
arecord -l   # list recording devices
```

**SDS011 not appearing:**
```bash
ls /dev/ttyUSB*
dmesg | grep tty    # check kernel detected it
sudo usermod -aG dialout pi   # add user to serial group, then reboot
```

**Supabase connection refused:**
```bash
curl -s "https://krmczyqwblsoekceanlj.supabase.co/rest/v1/climate_readings?limit=1" \
  -H "apikey: sb_publishable_DrHFT5J0vmrkYraUXIlpQQ_gsk1rdq6" | head -c 100
```

**Check all logs at once:**
```bash
tail -f /home/pi/earth_pulse/logs/*.log
```

---

## Data schema — what your node sends

Every row your node writes to Supabase includes a `node_id` column so data from different locations is always distinguishable.

**`climate_readings`** (hourly):
`recorded_at, node_id, aqi, pm2_5, pm10, temperature, humidity, wind_speed, wind_direction, precipitation, solar_radiation, google_aqi_india`

**`bird_detections`** (per detection):
`detected_at, node_id, species_common, species_scientific, confidence, latitude, longitude`

**`soundscape_readings`** (every 30 min):
`recorded_at, node_id, ndsi, biophony_db, anthrophony_db, rain_detected`

**`timelapse_frames`** (per photo):
`captured_at, node_id, filename, r2_url, temperature, humidity, aqi`

---

## Cost to run

| Item | Monthly cost |
|------|-------------|
| Electricity (Pi 3B, ~5W continuous) | ₹30–50 |
| Google AQI API (720 calls/month) | Free (10,000/month free tier) |
| Supabase database | Free (500MB free tier) |
| Internet bandwidth | Negligible (~50MB/month) |
| **Total** | **₹30–50/month** |

---

## What your data contributes

Once your node is running, your data:

1. **Appears live** on earthpulse.pages.dev within 1 hour
2. **Joins the spatial network** — multiple nodes enable pollution mapping across Pune
3. **Extends the archive** — every hour adds to a dataset that will be valuable for years
4. **Enables correlations** — bird activity vs AQI, soundscape health vs construction, monsoon tracking across the Sahyadri

---

## Contact & support

**Project:** Earth Pulse · earthpulse.pages.dev
**Network admin:** fangchu@gmail.com
**GitHub:** github.com/fangchu-in/earth-pulse
**Data licence:** CC BY 4.0 — free to use with attribution

*This guide is version-controlled in the Earth Pulse GitHub repository. If you find errors or have improvements, open an issue or pull request.*
