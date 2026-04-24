#!/usr/bin/env python3
"""
generate_weekly.py — runs every Monday at 6am IST
Calls the Cloudflare Worker to generate the weekly blog post.
Cron entry:
  30 0 * * 1  /home/fangchu/earth_pulse/venv/bin/python3 /home/fangchu/earth_pulse/aqi/generate_weekly.py >> /home/fangchu/earth_pulse/logs/weekly.log 2>&1
  (00:30 UTC Monday = 6:00am IST)
"""
import os, sys, json, requests
from datetime import datetime, timezone, timedelta
from pathlib import Path
# ── Config ────────────────────────────────────────────────────────────────────
WORKER_URL = 'https://earthpulse-weekly.fangchu.workers.dev/generate'
ENV_FILE   = Path('/home/fangchu/earth_pulse/.env')
def load_env():
    env = {}
    if ENV_FILE.exists():
        for line in ENV_FILE.read_text().splitlines():
            if '=' in line and not line.startswith('#'):
                k, v = line.split('=', 1)
                env[k.strip()] = v.strip()
    return env
def get_week_start():
    """Return last completed week's Monday in IST as YYYY-MM-DD string."""
    ist = datetime.now(timezone.utc) + timedelta(hours=5, minutes=30)
    days_back = ist.weekday()  # Monday=0, Sunday=6
    # On Monday days_back=0 — go back 7 to get LAST Monday, not today
    if days_back == 0:
        days_back = 7
    monday = ist - timedelta(days=days_back)
    return monday.strftime('%Y-%m-%d')
def main():
    env = load_env()
    secret = env.get('WORKER_SECRET', os.environ.get('WORKER_SECRET', ''))
    if not secret:
        print('[weekly] ERROR: WORKER_SECRET not set in .env')
        sys.exit(1)
    week_start = get_week_start()
    # Safety guard — never publish future or current week
    today_ist = (datetime.now(timezone.utc) + timedelta(hours=5, minutes=30)).date()
    week_start_date = datetime.strptime(week_start, '%Y-%m-%d').date()
    if week_start_date >= today_ist:
        print(f'[weekly] ✗ Refusing to publish future week {week_start} — aborting')
        sys.exit(1)
    print(f'[weekly] Triggering generation for week starting {week_start}')
    try:
        resp = requests.post(
            WORKER_URL,
            headers={
                'Content-Type': 'application/json',
                'X-Worker-Secret': secret,
            },
            json={'week_start': week_start},
            timeout=120,
        )
        if not resp.text.strip():
            print(f'[weekly] ✗ Empty response from Worker (status {resp.status_code})')
            sys.exit(1)
        data = resp.json()
        if data.get('ok'):
            print(f'[weekly] ✓ Post generated: {data.get("title","")[:80]}')
            print(f'[weekly] ✓ Pulse Score: {data.get("pulseScore")}')
        else:
            print(f'[weekly] ✗ Worker error: {data}')
            sys.exit(1)
    except Exception as e:
        print(f'[weekly] ✗ Request failed: {e}')
        sys.exit(1)
if __name__ == '__main__':
    main()