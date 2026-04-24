#!/usr/bin/env python3
"""
Earth Pulse — Weather Union Gap Filler
Detects gaps > 30 minutes in weather_union_readings and backfills using
Open-Meteo historical API (free, no key needed) as a substitute.

Run manually after power failures:
  python3 /home/fangchu/earth_pulse/aqi/gap_fill_wu.py

Or add to crontab to run daily at 2am:
  0 2 * * * /home/fangchu/earth_pulse/venv/bin/python3 /home/fangchu/earth_pulse/aqi/gap_fill_wu.py >> /home/fangchu/earth_pulse/logs/wu_gapfill.log 2>&1
"""

import requests
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import sys
sys.path.insert(0, '/home/fangchu/earth_pulse/aqi')
try:
    from alert import send_alert
except ImportError:
    def send_alert(s, b, n='wu_gap'): pass

SUPABASE_URL = 'https://krmczyqwblsoekceanlj.supabase.co'
SUPABASE_KEY = 'sb_publishable_DrHFT5J0vmrkYraUXIlpQQ_gsk1rdq6'
IST          = ZoneInfo('Asia/Kolkata')
GAP_MINUTES  = 30  # flag gap if no reading for this many minutes

SB_HDR = {
    'apikey':        SUPABASE_KEY,
    'Authorization': f'Bearer {SUPABASE_KEY}',
    'Content-Type':  'application/json',
    'Prefer':        'resolution=ignore-duplicates,return=minimal'
}

def get_existing_timestamps(days_back=7):
    """Fetch all recorded_at values from last N days."""
    since = (datetime.now(IST) - timedelta(days=days_back)).astimezone(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    all_rows = []
    offset = 0
    batch = 1000
    while True:
        r = requests.get(
            f'{SUPABASE_URL}/rest/v1/weather_union_readings'
            f'?select=recorded_at&recorded_at=gte.{since}&order=recorded_at.asc&limit={batch}&offset={offset}',
            headers={**SB_HDR, 'Prefer': ''},
            timeout=15
        )
        r.raise_for_status()
        rows = r.json()
        if not rows:
            break
        all_rows.extend(rows)
        if len(rows) < batch:
            break
        offset += batch
    return {datetime.fromisoformat(row['recorded_at']).astimezone(IST) for row in all_rows}

def find_gaps(timestamps, days_back=7):
    """Find 15-minute slots with no reading."""
    now   = datetime.now(IST).replace(second=0, microsecond=0)
    start = now - timedelta(days=days_back)
    # Round start to nearest 15 min
    start = start.replace(minute=(start.minute//15)*15, second=0, microsecond=0)
    gaps  = []
    slot  = start
    while slot <= now:
        # Check if any reading within 8 minutes of this slot
        if not any(abs((ts - slot).total_seconds()) < 480 for ts in timestamps):
            gaps.append(slot)
        slot += timedelta(minutes=15)
    return gaps

def fetch_open_meteo_for_gaps(gaps):
    """Fetch Open-Meteo data for gap dates. Uses forecast API (recent) or archive (older)."""
    if not gaps:
        return {}
    dates      = sorted({g.date() for g in gaps})
    start_date = dates[0].strftime('%Y-%m-%d')
    end_date   = dates[-1].strftime('%Y-%m-%d')
    cutoff     = (datetime.now(IST) - timedelta(days=6)).date()
    print(f"Fetching Open-Meteo from {start_date} to {end_date} for {len(gaps)} gaps...")

    lookup = {}
    PARAMS = {
        'latitude':       18.5526,
        'longitude':      73.7819,
        'hourly':         'temperature_2m,relativehumidity_2m,windspeed_10m,winddirection_10m,precipitation',
        'timezone':       'Asia/Kolkata',
        'windspeed_unit': 'ms'
    }

    def parse_response(data):
        for i, t in enumerate(data['hourly']['time']):
            dt = datetime.fromisoformat(t).replace(tzinfo=IST)
            lookup[dt] = {
                'temperature':       data['hourly']['temperature_2m'][i],
                'humidity':          data['hourly']['relativehumidity_2m'][i],
                'wind_speed':        data['hourly']['windspeed_10m'][i],
                'wind_direction':    data['hourly']['winddirection_10m'][i],
                'rain_intensity':    round((data['hourly']['precipitation'][i] or 0) / 60, 4),
                'rain_accumulation': data['hourly']['precipitation'][i],
            }

    # Recent gaps (last 6 days) → forecast API
    recent = [d for d in dates if d >= cutoff]
    if recent:
        r = requests.get('https://api.open-meteo.com/v1/forecast', params={
            **PARAMS, 'past_days': 6, 'forecast_days': 1
        }, timeout=30)
        r.raise_for_status()
        parse_response(r.json())

    # Older gaps → archive API
    older = [d for d in dates if d < cutoff]
    if older:
        r = requests.get('https://archive-api.open-meteo.com/v1/archive', params={
            **PARAMS,
            'start_date': older[0].strftime('%Y-%m-%d'),
            'end_date':   older[-1].strftime('%Y-%m-%d')
        }, timeout=30)
        r.raise_for_status()
        parse_response(r.json())

    return lookup

def backfill_gaps(gaps, om_lookup):
    """Insert gap rows using Open-Meteo as substitute source."""
    inserted = 0
    for gap_dt in gaps:
        # Find nearest hourly Open-Meteo reading
        om_dt = gap_dt.replace(minute=0, second=0, microsecond=0)
        if om_dt not in om_lookup:
            print(f"  No OM data for {gap_dt} — skipping")
            continue
        vals = om_lookup[om_dt]
        payload = {
            'recorded_at':       gap_dt.strftime('%Y-%m-%d %H:%M:%S+05:30'),
            'temperature':       vals['temperature'],
            'humidity':          vals['humidity'],
            'wind_speed':        vals['wind_speed'],
            'wind_direction':    vals['wind_direction'],
            'rain_intensity':    vals['rain_intensity'],
            'rain_accumulation': vals['rain_accumulation'],
        }
        payload = {k: v for k, v in payload.items() if v is not None}
        r = requests.post(
            f'{SUPABASE_URL}/rest/v1/weather_union_readings',
            headers=SB_HDR, json=payload, timeout=10
        )
        if r.status_code in (200, 201):
            inserted += 1
        elif r.status_code == 409:
            pass  # duplicate — already exists
        else:
            print(f"  Insert failed {r.status_code}: {r.text[:80]}")
    return inserted

if __name__ == '__main__':
    print(f"[{datetime.now(IST).strftime('%Y-%m-%d %H:%M')}] Weather Union gap fill starting...")
    try:
        timestamps = get_existing_timestamps(days_back=7)
        print(f"Found {len(timestamps)} existing readings in last 7 days")
        gaps = find_gaps(timestamps, days_back=7)
        print(f"Found {len(gaps)} missing 15-min slots")
        if not gaps:
            print("No gaps — all good.")
        else:
            om_data  = fetch_open_meteo_for_gaps(gaps)
            inserted = backfill_gaps(gaps, om_data)
            print(f"Backfilled {inserted} rows using Open-Meteo as substitute")
    except Exception as e:
        print(f"ERROR: {e}")
        send_alert('WU gap fill error', str(e), 'wu_gap')
        raise
