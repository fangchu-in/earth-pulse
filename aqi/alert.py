#!/usr/bin/env python3
"""
Earth Pulse — Error Alert Module
Sends email via Resend when a Pi script fails.
Import this in aqi.py and log_weather_union.py

Usage:
  from alert import send_alert
  send_alert("AQI script failed", "JSON parsing failed at 19:00 IST")
"""

import requests
import os
from datetime import datetime
from zoneinfo import ZoneInfo

RESEND_API_KEY  = os.environ.get('RESEND_API_KEY', '')   # set in crontab
ALERT_TO        = 'fangchu@gmail.com'
ALERT_FROM      = 'vaibhav@ektitli.org'
WORKER_URL      = 'https://earthpulse-email.fangchu.workers.dev'
IST             = ZoneInfo('Asia/Kolkata')

COOLDOWN_DIR    = '/home/fangchu/earth_pulse/logs'
COOLDOWN_MINS   = 60

def _cooldown_path(script_name):
    return f'{COOLDOWN_DIR}/.alert_cooldown_{script_name}'

def _in_cooldown(script_name):
    path = _cooldown_path(script_name)
    if not os.path.exists(path):
        return False
    try:
        with open(path) as f:
            last = float(f.read().strip())
        elapsed = (datetime.now().timestamp() - last) / 60
        return elapsed < COOLDOWN_MINS
    except:
        return False

def _set_cooldown(script_name):
    try:
        os.makedirs(COOLDOWN_DIR, exist_ok=True)
        with open(_cooldown_path(script_name), 'w') as f:
            f.write(str(datetime.now().timestamp()))
    except:
        pass

def send_alert(subject, body, script_name='earthpulse'):
    """
    Send an error alert email. Respects 60-minute cooldown per script
    so you don't get flooded during extended outages.
    """
    if _in_cooldown(script_name):
        print(f'  ⏸  Alert suppressed (cooldown active for {script_name})')
        return

    now_ist      = datetime.now(IST).strftime('%Y-%m-%d %H:%M IST')
    full_subject = f'⚠️ Earth Pulse Alert: {subject}'
    full_body    = f"""Earth Pulse monitoring alert from your Baner Pi.

Time: {now_ist}
Script: {script_name}

{body}

---
This alert was sent automatically from your Pi 3B+ (printkiosk).
Check the logs: tail -f /home/fangchu/earth_pulse/logs/{script_name}.log
Admin panel: https://earth-pulse.org/admin.html
"""

    # ── Primary: Resend API direct ────────────────────────────────────────────
    if RESEND_API_KEY:
        try:
            r = requests.post(
                'https://api.resend.com/emails',
                headers={
                    'Authorization': f'Bearer {RESEND_API_KEY}',
                    'Content-Type':  'application/json'
                },
                json={
                    'from':    ALERT_FROM,
                    'to':      [ALERT_TO],
                    'subject': full_subject,
                    'text':    full_body,
                    'html':    full_body.replace('\n', '<br>')
                },
                timeout=10
            )
            if r.status_code in (200, 201):
                print(f'  📧 Alert sent: {subject}')
                _set_cooldown(script_name)
                return
            else:
                print(f'  ⚠️  Resend failed ({r.status_code}), trying Worker…')
        except Exception as e:
            print(f'  ⚠️  Resend error: {e}, trying Worker…')

    # ── Fallback: Cloudflare Worker email endpoint ────────────────────────────
    try:
        r = requests.post(
            WORKER_URL + '/send',
            headers={'Authorization': 'Bearer earthpulse-admin'},
            json={
                'to':      ALERT_TO,
                'subject': full_subject,
                'html':    full_body.replace('\n', '<br>')
            },
            timeout=10
        )
        if r.status_code in (200, 201):
            print(f'  📧 Alert sent via Worker: {subject}')
            _set_cooldown(script_name)
        else:
            print(f'  ❌ Worker also failed ({r.status_code})')
    except Exception as e:
        print(f'  ❌ Could not send alert: {e}')


def check_data_gap(table, timestamp_col, max_gap_mins, script_name):
    """
    Check if there's a gap in Supabase data. Call this at the START
    of each script run to detect if previous runs failed silently.
    """
    SUPABASE_URL = 'https://krmczyqwblsoekceanlj.supabase.co'
    SUPABASE_KEY = 'sb_publishable_DrHFT5J0vmrkYraUXIlpQQ_gsk1rdq6'
    try:
        r = requests.get(
            f'{SUPABASE_URL}/rest/v1/{table}?select={timestamp_col}&order={timestamp_col}.desc&limit=1',
            headers={
                'apikey':        SUPABASE_KEY,
                'Authorization': f'Bearer {SUPABASE_KEY}'
            },
            timeout=10
        )
        rows = r.json()
        if not rows or not isinstance(rows, list):
            return
        last_ts  = datetime.fromisoformat(rows[0][timestamp_col].replace('Z', '+00:00'))
        gap_mins = (datetime.now(last_ts.tzinfo) - last_ts).total_seconds() / 60
        if gap_mins > max_gap_mins:
            hours = round(gap_mins / 60, 1)
            send_alert(
                f'{script_name} — {hours}h data gap detected',
                f'Last entry in {table} was {hours} hours ago ({rows[0][timestamp_col]}).\n\n'
                f'This suggests the script may have been failing silently.\n\n'
                f'Check the Pi and restart if needed:\n'
                f'  crontab -e               — verify schedule\n'
                f'  systemctl status cron    — check cron is running',
                script_name
            )
    except Exception as e:
        print(f'  ⚠️  Gap check failed: {e}')
