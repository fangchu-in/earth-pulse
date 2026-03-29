"""
Earth Pulse — BirdNET Bird Detection Runner
Uses Python 3.11 birdnet_venv. Run via cron every 10 minutes during active hours.

Cron entry (add with: crontab -e):
*/10 * * * * /home/fangchu/earth_pulse/birdnet_venv/bin/python /home/fangchu/earth_pulse/birds/birdnet_runner.py >> /home/fangchu/earth_pulse/birds/birdnet.log 2>&1

Schedule logic (handled inside script, not cron):
- Dawn chorus  : sunrise - 45min  → sunrise + 2.5hrs
- Evening chorus: sunset - 1hr    → sunset + 30min
- Night watch  : 10pm → 5am, runs every 30min (handled by cron interval)
"""

import os
import subprocess
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from astral import LocationInfo
from astral.sun import sun
from supabase import create_client

# ─── CONFIG ───────────────────────────────────────────────────────────────────
LAT          = 18.5526156
LON          = 73.7818663
TIMEZONE     = "Asia/Kolkata"
RECORD_SECS  = 300        # record 300 seconds per detection cycle
MIN_CONF     = 0.35      # only log detections above 70% confidence
AUDIO_DIR    = "/home/fangchu/earth_pulse/birds/recordings"
ENV_FILE     = "/home/fangchu/earth_pulse/.env"

# Load credentials from .env file
def load_env(path):
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

env = load_env(ENV_FILE)
SUPABASE_URL = env.get("SUPABASE_URL", "")
SUPABASE_KEY = env.get("SUPABASE_KEY", "")
# ──────────────────────────────────────────────────────────────────────────────


def get_sun_times():
    """Get today's sunrise and sunset for Balewadi."""
    location = LocationInfo(
        name="Balewadi",
        region="India",
        timezone=TIMEZONE,
        latitude=LAT,
        longitude=LON
    )
    s = sun(location.observer, date=datetime.now().date(),
            tzinfo=ZoneInfo(TIMEZONE))
    return s["sunrise"], s["sunset"]


def should_record_now():
    """
    Returns (should_record, session_type) based on current time vs sun schedule.
    Session types: 'dawn', 'evening', 'night', None
    """
    from datetime import timedelta
    now = datetime.now(tz=ZoneInfo(TIMEZONE))
    sunrise, sunset = get_sun_times()

    dawn_start   = sunrise - timedelta(minutes=45)
    dawn_end     = sunrise + timedelta(hours=2, minutes=30)
    evening_start = sunset - timedelta(hours=1)
    evening_end   = sunset + timedelta(minutes=30)

    # Night watch: 10pm to 5am, but only every 30 mins
    # Cron runs every 10 mins — we check if minute is :00 or :30 for night
    night_start  = now.replace(hour=22, minute=0, second=0, microsecond=0)
    night_end    = now.replace(hour=5,  minute=0, second=0, microsecond=0)

    if dawn_start <= now <= dawn_end:
        return True, "dawn"
    elif evening_start <= now <= evening_end:
        return True, "evening"
    elif now.hour >= 22 or now.hour < 5:
        # Night watch only on :00 and :30 minutes
        if now.minute < 10 or (29 <= now.minute <= 39):
            return True, "night"

    return False, None


def record_audio(filepath, duration=RECORD_SECS):
    """Record audio from USB mic (card 2)."""
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    cmd = [
        "arecord",
        "-D", "plughw:2,0",
        "-f", "S16_LE",
        "-r", "48000",
        "-c", "1",
        "-d", str(duration),
        filepath
    ]
    result = subprocess.run(cmd, capture_output=True)
    return result.returncode == 0


def analyze_recording(filepath):
    """Run BirdNET analysis and return detections."""
    from birdnetlib import Recording
    from birdnetlib.analyzer import Analyzer

    analyzer = Analyzer()
    rec = Recording(
        analyzer,
        filepath,
        lat=LAT,
        lon=LON,
        date=datetime.now(),
        min_conf=MIN_CONF
    )
    rec.analyze()
    return rec.detections


def get_current_aqi():
    """Pull current AQI from Supabase for correlation."""
    try:
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        result = (
            supabase.table("climate_readings")
            .select("aqi, temperature")
            .order("recorded_at", desc=True)
            .limit(1)
            .execute()
        )
        if result.data:
            return result.data[0].get("aqi"), result.data[0].get("temperature")
    except Exception:
        pass
    return None, None


def check_new_species_this_year(species_scientific):
    """Check if this species has been detected before this year."""
    try:
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        year_start = f"{datetime.now().year}-01-01"
        result = (
            supabase.table("bird_detections")
            .select("id")
            .eq("species_scientific", species_scientific)
            .gte("detected_at", year_start)
            .limit(1)
            .execute()
        )
        return len(result.data) == 0  # True = first time this year
    except Exception:
        return False


def push_detections(detections, session_type, aqi, temperature):
    """Push all detections to Supabase."""
    if not detections:
        return

    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    now = datetime.now(tz=ZoneInfo(TIMEZONE)).isoformat()

    for d in detections:
        is_new = check_new_species_this_year(d["scientific_name"])

        row = {
            "detected_at":              now,
            "species_common":           d["common_name"],
            "species_scientific":       d["scientific_name"],
            "confidence":               round(d["confidence"], 4),
            "aqi_at_detection":         aqi,
            "temperature_at_detection": temperature,
            "is_new_species_this_year": is_new,
        }

        try:
            supabase.table("bird_detections").insert(row).execute()
            new_tag = " *** FIRST THIS YEAR ***" if is_new else ""
            print(f"  ✅ {d['common_name']} ({d['confidence']:.0%}){new_tag}")
        except Exception as e:
            print(f"  ⚠️  Supabase error for {d['common_name']}: {e}")


def main():
    now = datetime.now(tz=ZoneInfo(TIMEZONE))
    print(f"\n🐦 Earth Pulse BirdNET — {now.strftime('%Y-%m-%d %H:%M')}")

    should_record, session = should_record_now()

    if not should_record:
        sunrise, sunset = get_sun_times()
        print(f"  Outside recording window. Sunrise: {sunrise.strftime('%H:%M')} | Sunset: {sunset.strftime('%H:%M')}")
        print(f"  Next dawn recording starts at {(sunrise - __import__('datetime').timedelta(minutes=45)).strftime('%H:%M')}")
        return

    print(f"  Session: {session.upper()} chorus")

    # Build filepath with timestamp
    timestamp = now.strftime("%Y%m%d_%H%M%S")
    audio_path = f"{AUDIO_DIR}/{session}/{timestamp}.wav"

    # Record
    print(f"  Recording {RECORD_SECS}s of audio...")
    if not record_audio(audio_path):
        print("  ❌ Recording failed — check mic connection")
        return

    # Analyze
    print(f"  Analyzing with BirdNET (228 local species)...")
    detections = analyze_recording(audio_path)

    if not detections:
        print(f"  No detections above {MIN_CONF:.0%} confidence")
        # Remove silent recording to save space
        os.remove(audio_path)
        return

    print(f"  Detected {len(detections)} species:")

    # Get current AQI for correlation
    aqi, temperature = get_current_aqi()

    # Push to Supabase
    push_detections(detections, session, aqi, temperature)

    # Keep audio file only for high-confidence detections (>85%)
    high_conf = any(d["confidence"] > 0.85 for d in detections)
    if not high_conf:
        os.remove(audio_path)
    else:
        print(f"  💾 Audio saved: {audio_path}")

    print(f"  AQI at detection: {aqi} | Temp: {temperature}°C")


if __name__ == "__main__":
    main()
