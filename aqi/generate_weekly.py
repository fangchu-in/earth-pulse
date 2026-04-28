#!/usr/bin/env python3
"""
generate_weekly.py — runs every Monday at 6:00am IST (00:30 UTC)
Calls the Cloudflare Worker to generate the weekly blog post.

Cron entry (unchanged):
  30 0 * * 1  /home/fangchu/earth_pulse/venv/bin/python3 /home/fangchu/earth_pulse/aqi/generate_weekly.py >> /home/fangchu/earth_pulse/logs/weekly.log 2>&1
"""
import os, sys, json, requests, time
from datetime import datetime, timezone, timedelta
from pathlib import Path

# ── Config ─────────────────────────────────────────────────────────────────
WORKER_URL  = 'https://earthpulse-weekly.fangchu.workers.dev/generate'
ENV_FILE    = Path('/home/fangchu/earth_pulse/.env')
MAX_RETRIES = 3
RETRY_DELAY = 30  # seconds between retries

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

def call_worker(secret, week_start, attempt):
    """Call the Worker with retry logic. Returns (ok, data)."""
    try:
        print(f'[weekly] Attempt {attempt}/{MAX_RETRIES} for week {week_start}')
        resp = requests.post(
            WORKER_URL,
            headers={
                'Content-Type': 'application/json',
                'X-Worker-Secret': secret,
            },
            json={'week_start': week_start},
            timeout=150,  # increased from 120 — Worker needs time for Supabase queries
        )
        if not resp.text.strip():
            print(f'[weekly] ✗ Empty response (HTTP {resp.status_code})')
            return False, None
        data = resp.json()
        return True, data
    except requests.exceptions.Timeout:
        print(f'[weekly] ✗ Timeout on attempt {attempt}')
        return False, None
    except requests.exceptions.ConnectionError as e:
        print(f'[weekly] ✗ Connection error on attempt {attempt}: {e}')
        return False, None
    except ValueError as e:
        print(f'[weekly] ✗ JSON parse error on attempt {attempt}: {e}')
        return False, None

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

    print(f'[weekly] Generating post for week starting {week_start}')

    # Retry loop
    for attempt in range(1, MAX_RETRIES + 1):
        ok, data = call_worker(secret, week_start, attempt)

        if ok and data:
            if data.get('ok'):
                print(f'[weekly] ✓ Post generated: {data.get("title","")[:80]}')
                print(f'[weekly] ✓ Pulse Score: {data.get("pulseScore")}')
                print(f'[weekly] ✓ Slug: {data.get("slug")}')
                sys.exit(0)
            elif data.get('message') == 'Already generated':
                print(f'[weekly] ✓ Post already exists for {week_start} — skipping')
                sys.exit(0)
            else:
                print(f'[weekly] ✗ Worker error: {data}')
                # Don't retry on logical errors — only on empty/timeout
                sys.exit(1)

        if attempt < MAX_RETRIES:
            print(f'[weekly] Waiting {RETRY_DELAY}s before retry...')
            time.sleep(RETRY_DELAY)

    print(f'[weekly] ✗ All {MAX_RETRIES} attempts failed for week {week_start}')
    sys.exit(1)

if __name__ == '__main__':
    main()
