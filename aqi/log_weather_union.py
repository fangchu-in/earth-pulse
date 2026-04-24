#!/usr/bin/env python3
"""
Earth Pulse — Weather Union Logger
Logs hyperlocal weather from station ZWL008983 to Supabase every 15 minutes.
Deploy on Pi 3B+ (indoor AQI Pi).
Crontab entry (run: crontab -e):
*/15 * * * * /home/fangchu/earth_pulse/venv/bin/python3 /home/fangchu/earth_pulse/aqi/log_weather_union.py >> /home/fangchu/earth_pulse/logs/wu.log 2>&1
"""
import sys
import requests
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

sys.path.insert(0, '/home/fangchu/earth_pulse/aqi')
try:
    from alert import send_alert, check_data_gap
except ImportError:
    def send_alert(s, b, n='wu'): pass
    def check_data_gap(t, c, m, n): pass

SUPABASE_URL = 'https://krmczyqwblsoekceanlj.supabase.co'
SUPABASE_KEY = 'sb_publishable_DrHFT5J0vmrkYraUXIlpQQ_gsk1rdq6'
WU_API_KEY   = 'b289f920fb76e23fec65afbcd40add80'
LOCALITY_ID  = 'ZWL008983'
IST          = ZoneInfo('Asia/Kolkata')

def fetch_wu():
    r = requests.get(
        'https://weatherunion.com/gw/weather/external/v0/get_locality_weather_data',
        params={'locality_id': LOCALITY_ID},
        headers={'X-Zomato-Api-Key': WU_API_KEY},
        timeout=10
    )
    r.raise_for_status()
    data = r.json()
    if str(data.get('status')) != '200':
        raise ValueError(f"WU error: {data.get('message')}")
    return data['locality_weather_data']

def log_to_supabase(wd):
    now_ist = datetime.now(timezone.utc).astimezone(IST).strftime('%Y-%m-%d %H:%M:%S+05:30')
    payload = {
        'recorded_at':       now_ist,
        'temperature':       wd.get('temperature'),
        'humidity':          wd.get('humidity'),
        'wind_speed':        wd.get('wind_speed'),
        'wind_direction':    wd.get('wind_direction'),
        'rain_intensity':    wd.get('rain_intensity'),
        'rain_accumulation': wd.get('rain_accumulation'),
    }
    # Remove None values
    payload = {k: v for k, v in payload.items() if v is not None}
    r = requests.post(
        f'{SUPABASE_URL}/rest/v1/weather_union_readings',
        headers={
            'apikey':        SUPABASE_KEY,
            'Authorization': f'Bearer {SUPABASE_KEY}',
            'Content-Type':  'application/json',
            'Prefer':        'resolution=ignore-duplicates,return=minimal'
        },
        json=payload,
        timeout=10
    )
    r.raise_for_status()
    return payload

if __name__ == '__main__':
    # Check for data gap at start — alerts if last WU reading was > 45 mins ago
    check_data_gap('weather_union_readings', 'recorded_at', 45, 'wu')
    try:
        wd     = fetch_wu()
        logged = log_to_supabase(wd)
        print(f"[{logged['recorded_at']}] T={logged.get('temperature')}°C "
              f"H={logged.get('humidity')}% "
              f"W={logged.get('wind_speed')}m/s "
              f"Rain={logged.get('rain_intensity')}mm/min")
    except Exception as e:
        print(f"ERROR: {e}")
        send_alert('Weather Union logger error', str(e), 'wu')
        raise
