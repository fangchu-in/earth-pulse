"""
Earth Pulse — Hill Picture Processing Pipeline
process_images.py

Watches /earth_pulse/pictures/raw/ for new images (from Pi camera or upload).
For each new image:
  1. Reads EXIF data to extract the original capture time
  2. Converts to IST and names file YYYY-MM-DD_HH-MM.jpg
  3. Resizes to 1280×720, JPEG quality 80, preserving EXIF metadata
  4. Uploads processed image to Cloudflare R2
  5. Saves a metadata record to Supabase (timelapse_frames table)
  6. Moves raw file to /delete/ folder
  7. Cron deletes /delete/ folder contents every 18 hours

Cron entries (add to Pi 3B crontab with `crontab -e`):
  # Process new images every 5 minutes
  */5 * * * * /home/fangchu/earth_pulse/venv/bin/python /home/fangchu/earth_pulse/pictures/process_images.py >> /home/fangchu/earth_pulse/pictures/process_images.log 2>&1

  # Delete raw files from /delete/ every 18 hours
  0 */18 * * * find /home/fangchu/earth_pulse/pictures/delete/ -name "*.jpg" -delete && find /home/fangchu/earth_pulse/pictures/delete/ -name "*.jpeg" -delete && find /home/fangchu/earth_pulse/pictures/delete/ -name "*.png" -delete

Install dependencies:
  pip install Pillow boto3 requests --break-system-packages
  (or inside venv: pip install Pillow boto3 requests)

R2 credentials — add to /home/fangchu/earth_pulse/.env:
  R2_ACCESS_KEY_ID=your_r2_access_key
  R2_SECRET_ACCESS_KEY=your_r2_secret_key
  R2_BUCKET=earthpulse-files
  R2_ENDPOINT=https://e340725bb3d0ace4725db23e1516a2a1.r2.cloudflarestorage.com
"""

import os
import io
import datetime
import shutil
import requests
import json
from pathlib import Path
from zoneinfo import ZoneInfo

try:
    from PIL import Image, ExifTags
    import boto3
    from botocore.client import Config
except ImportError as e:
    print(f"❌ Missing dependency: {e}")
    print("   Run: pip install Pillow boto3")
    exit(1)

# ── Load .env ─────────────────────────────────────────────────────────────────
def load_env(path="/home/fangchu/earth_pulse/.env"):
    env = {}
    try:
        with open(path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    env[k.strip()] = v.strip()
    except FileNotFoundError:
        print(f"  ⚠️  .env not found at {path}")
    return env

_env = load_env()

# ── CONFIG ────────────────────────────────────────────────────────────────────
IST = ZoneInfo("Asia/Kolkata")

BASE_DIR      = Path("/home/fangchu/earth_pulse/pictures")
RAW_DIR       = BASE_DIR / "raw"
PROCESSED_DIR = BASE_DIR / "processed"
DELETE_DIR    = BASE_DIR / "delete"
META_DIR      = BASE_DIR / "meta"

# Processed image spec
TARGET_WIDTH   = 1280
TARGET_HEIGHT  = 720
JPEG_QUALITY   = 80   # 70-80% is the sweet spot: good visual quality, small file

# Cloudflare R2
R2_BUCKET   = _env.get("R2_BUCKET",   "earthpulse-files")
R2_ENDPOINT = _env.get("R2_ENDPOINT", "https://e340725bb3d0ace4725db23e1516a2a1.r2.cloudflarestorage.com")
R2_KEY_ID   = _env.get("R2_ACCESS_KEY_ID",     "")
R2_SECRET   = _env.get("R2_SECRET_ACCESS_KEY", "")

# Supabase
SUPABASE_URL = "https://krmczyqwblsoekceanlj.supabase.co"
SUPABASE_KEY = "sb_publishable_DrHFT5J0vmrkYraUXIlpQQ_gsk1rdq6"

# Public URL base for R2 (set up a custom domain or use Cloudflare's public URL)
# If you haven't set up a public domain, use the R2 endpoint directly.
R2_PUBLIC_BASE = f"{R2_ENDPOINT}/{R2_BUCKET}"
# ─────────────────────────────────────────────────────────────────────────────

# Image file extensions we'll process
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".JPG", ".JPEG", ".PNG"}


def ensure_dirs():
    """Create all required directories if they don't exist."""
    for d in [RAW_DIR, PROCESSED_DIR, DELETE_DIR, META_DIR]:
        d.mkdir(parents=True, exist_ok=True)


def get_r2_client():
    """Return an S3-compatible boto3 client for Cloudflare R2."""
    if not R2_KEY_ID or not R2_SECRET:
        return None
    return boto3.client(
        "s3",
        endpoint_url=R2_ENDPOINT,
        aws_access_key_id=R2_KEY_ID,
        aws_secret_access_key=R2_SECRET,
        config=Config(signature_version="s3v4"),
        region_name="auto"
    )


def get_exif_datetime(img):
    """
    Extract DateTimeOriginal from EXIF. Returns a datetime object in IST.
    Falls back to DateTimeDigitized, then DateTime, then None.
    EXIF stores time as naive local time — we assume the camera is set to IST.
    """
    exif_data = img._getexif()
    if not exif_data:
        return None

    # Map EXIF tag numbers to names
    tag_map = {v: k for k, v in ExifTags.TAGS.items()}

    for field in ["DateTimeOriginal", "DateTimeDigitized", "DateTime"]:
        tag_id = tag_map.get(field)
        if tag_id and tag_id in exif_data:
            raw = exif_data[tag_id]
            try:
                # EXIF format: "YYYY:MM:DD HH:MM:SS"
                dt = datetime.datetime.strptime(raw, "%Y:%m:%d %H:%M:%S")
                # Assume camera clock is IST (you're in Pune, camera not set to UTC)
                return dt.replace(tzinfo=IST)
            except Exception:
                continue
    return None


def make_filename(dt_ist, existing_names):
    """
    Generate YYYY-MM-DD_HH-MM.jpg from IST datetime.
    If a file with that name already exists (same minute), appends _2, _3 etc.
    This handles burst shots or multiple uploads in the same minute.
    """
    base = dt_ist.strftime("%Y-%m-%d_%H-%M")
    name = f"{base}.jpg"
    suffix = 2
    while name in existing_names:
        name = f"{base}_{suffix}.jpg"
        suffix += 1
    return name


def resize_with_exif(input_path):
    """
    Open image, resize to TARGET_WIDTH x TARGET_HEIGHT (letterbox/crop to fit),
    and return (PIL Image, original EXIF bytes).
    EXIF is preserved in the output so metadata is not lost.
    """
    img = Image.open(input_path)

    # Get raw EXIF bytes before any processing
    try:
        exif_bytes = img.info.get("exif", b"")
    except Exception:
        exif_bytes = b""

    # Resize — use LANCZOS for best quality downscale
    # Strategy: fit within 1280x720, maintaining aspect ratio (no crop)
    img.thumbnail((TARGET_WIDTH, TARGET_HEIGHT), Image.LANCZOS)

    return img, exif_bytes


def upload_to_r2(client, local_path, r2_key):
    """Upload a file to Cloudflare R2. Returns the public URL or None on failure."""
    if client is None:
        print("  ⚠️  R2 client not configured — skipping upload")
        return None
    try:
        client.upload_file(
            str(local_path),
            R2_BUCKET,
            r2_key,
            ExtraArgs={"ContentType": "image/jpeg"}
        )
        return f"{R2_PUBLIC_BASE}/{r2_key}"
    except Exception as e:
        print(f"  ⚠️  R2 upload failed: {e}")
        return None


def fetch_climate_for_time(dt_ist):
    """
    Fetch the closest climate reading from Supabase for a given IST datetime.
    Used to annotate processed images with weather conditions.
    Returns a dict with climate data, or empty dict if unavailable.
    """
    try:
        # Round to nearest hour for lookup
        hour = dt_ist.replace(minute=0, second=0, microsecond=0)
        # Query ±1 hour window
        from_dt = (hour - datetime.timedelta(hours=1)).isoformat()
        to_dt   = (hour + datetime.timedelta(hours=1)).isoformat()

        headers = {
            "apikey":        SUPABASE_KEY,
            "Authorization": f"Bearer {SUPABASE_KEY}"
        }
        res = requests.get(
            f"{SUPABASE_URL}/rest/v1/climate_readings"
            f"?select=recorded_at,temperature,humidity,aqi,google_aqi_india,"
            f"dominant_pollutant,cloudcover,precipitation,wind_speed"
            f"&recorded_at=gte.{from_dt}&recorded_at=lte.{to_dt}"
            f"&order=recorded_at.asc&limit=3",
            headers=headers, timeout=10
        )
        rows = res.json()
        if rows and isinstance(rows, list):
            return rows[0]   # closest available reading
    except Exception as e:
        print(f"  ⚠️  Climate lookup failed: {e}")
    return {}


def push_frame_to_supabase(frame_record):
    """
    Insert or update a record in the timelapse_frames table.
    Table columns: filename, captured_at, r2_url, temperature, humidity,
                   aqi, google_aqi_india, dominant_pollutant, cloudcover,
                   precipitation, wind_speed, source
    """
    try:
        headers = {
            "apikey":        SUPABASE_KEY,
            "Authorization": f"Bearer {SUPABASE_KEY}",
            "Content-Type":  "application/json",
            "Prefer":        "resolution=merge-duplicates"
        }
        res = requests.post(
            f"{SUPABASE_URL}/rest/v1/timelapse_frames",
            json=frame_record,
            headers=headers,
            timeout=10
        )
        if res.status_code in [200, 201]:
            print("  ✅ Supabase frame record: saved")
        else:
            print(f"  ⚠️  Supabase frame failed ({res.status_code}): {res.text[:200]}")
    except Exception as e:
        print(f"  ⚠️  Supabase error: {e}")


def save_meta(filename, frame_record):
    """Save a local JSON metadata file as backup (in /meta/)."""
    try:
        meta_path = META_DIR / f"{filename}.json"
        with open(meta_path, "w") as f:
            json.dump(frame_record, f, indent=2, default=str)
    except Exception as e:
        print(f"  ⚠️  Meta save failed: {e}")


def is_birdnet_recording():
    """
    Check if BirdNET is currently recording audio.
    Looks for a .wav file being written in the recordings directory.
    Returns True if a recent recording is in progress — we skip camera capture
    during active recording to avoid CPU contention.
    This check is used by the Pi camera capture script, not here.
    """
    recordings_dir = Path("/home/fangchu/earth_pulse/birds/recordings")
    now = datetime.datetime.now()
    try:
        for wav in recordings_dir.rglob("*.wav"):
            mtime = datetime.datetime.fromtimestamp(wav.stat().st_mtime)
            # If a WAV file was modified in the last 60 seconds, recording is active
            if (now - mtime).total_seconds() < 60:
                return True
    except Exception:
        pass
    return False


def process_image(raw_path, r2_client, existing_names):
    """
    Full pipeline for one image file:
    1. Read EXIF, extract capture time
    2. Resize preserving EXIF
    3. Generate filename from IST datetime
    4. Save to processed/
    5. Upload to R2
    6. Fetch climate data for that moment
    7. Push record to Supabase
    8. Move raw to delete/
    Returns the output filename on success, None on failure.
    """
    print(f"\n  📸 Processing: {raw_path.name}")

    # ── Step 1: Open and read EXIF ────────────────────────────────────────────
    try:
        img = Image.open(raw_path)
    except Exception as e:
        print(f"  ❌ Cannot open image: {e}")
        return None

    dt_ist = get_exif_datetime(img)

    if dt_ist is None:
        # No EXIF datetime — use file modification time as fallback
        mtime = raw_path.stat().st_mtime
        dt_ist = datetime.datetime.fromtimestamp(mtime, tz=IST)
        print(f"  ⚠️  No EXIF datetime — using file mtime: {dt_ist.strftime('%Y-%m-%d %H:%M IST')}")
    else:
        print(f"  📅 EXIF datetime: {dt_ist.strftime('%Y-%m-%d %H:%M IST')}")

    # Determine source (uploaded via web vs Pi camera)
    source = "upload" if "_upload" in raw_path.stem else "pi_camera"

    # ── Step 2: Resize preserving EXIF ───────────────────────────────────────
    try:
        img, exif_bytes = resize_with_exif(raw_path)
    except Exception as e:
        print(f"  ❌ Resize failed: {e}")
        return None

    # ── Step 3: Generate output filename ─────────────────────────────────────
    output_name = make_filename(dt_ist, existing_names)
    existing_names.add(output_name)
    output_path = PROCESSED_DIR / output_name

    # ── Step 4: Save processed image ─────────────────────────────────────────
    try:
        save_kwargs = {"quality": JPEG_QUALITY, "optimize": True, "format": "JPEG"}
        if exif_bytes:
            save_kwargs["exif"] = exif_bytes
        img.save(output_path, **save_kwargs)
        size_kb = output_path.stat().st_size / 1024
        print(f"  💾 Saved: {output_name} ({size_kb:.0f} KB, {img.width}×{img.height}px)")
    except Exception as e:
        print(f"  ❌ Save failed: {e}")
        return None

    # ── Step 5: Upload to R2 ─────────────────────────────────────────────────
    # Folder structure in R2: timelapse/YYYY/MM/YYYY-MM-DD_HH-MM.jpg
    r2_folder = f"timelapse/{dt_ist.strftime('%Y/%m')}"
    r2_key    = f"{r2_folder}/{output_name}"
    r2_url    = upload_to_r2(r2_client, output_path, r2_key)

    if r2_url:
        print(f"  ☁️  R2: {r2_key}")
    else:
        print(f"  ⚠️  R2 upload failed — image saved locally only")

    # ── Step 6: Fetch matching climate data ───────────────────────────────────
    climate = fetch_climate_for_time(dt_ist)

    # ── Step 7: Build and push Supabase record ────────────────────────────────
    frame_record = {
        "filename":          output_name,
        "captured_at":       dt_ist.isoformat(),
        "r2_url":            r2_url,
        "r2_key":            r2_key,
        "source":            source,
        "width":             img.width,
        "height":            img.height,
        "size_kb":           round(size_kb),
        # Climate at time of capture (may be approximate ±1hr)
        "temperature":       climate.get("temperature"),
        "humidity":          climate.get("humidity"),
        "aqi":               climate.get("aqi"),
        "google_aqi_india":  climate.get("google_aqi_india"),
        "dominant_pollutant":climate.get("dominant_pollutant"),
        "cloudcover":        climate.get("cloudcover"),
        "precipitation":     climate.get("precipitation"),
        "wind_speed":        climate.get("wind_speed"),
    }

    push_frame_to_supabase(frame_record)
    save_meta(output_name, frame_record)

    # ── Step 8: Move raw to delete/ ───────────────────────────────────────────
    delete_path = DELETE_DIR / raw_path.name
    shutil.move(str(raw_path), str(delete_path))
    print(f"  🗑️  Raw moved to delete/: {raw_path.name}")

    return output_name


def main():
    now = datetime.datetime.now(IST)
    print(f"\n🏔️  Earth Pulse Image Processor — {now.strftime('%Y-%m-%d %H:%M IST')}")

    ensure_dirs()

    # Find all unprocessed images in raw/
    raw_files = sorted([
        f for f in RAW_DIR.iterdir()
        if f.is_file() and f.suffix.lower() in {".jpg", ".jpeg", ".png"}
    ])

    if not raw_files:
        print("  ✅ No new images in raw/ — nothing to do")
        return

    print(f"  Found {len(raw_files)} image(s) to process")

    # Get existing processed filenames to handle duplicate minutes
    existing_names = {f.name for f in PROCESSED_DIR.iterdir() if f.is_file()}

    # Set up R2 client once for the whole run
    r2_client = get_r2_client()
    if r2_client:
        print("  ☁️  R2 client: connected")
    else:
        print("  ⚠️  R2 credentials not set — images saved locally only")

    processed = 0
    failed    = 0

    for raw_path in raw_files:
        result = process_image(raw_path, r2_client, existing_names)
        if result:
            processed += 1
        else:
            failed += 1

    print(f"\n  ✅ Done. Processed: {processed} | Failed: {failed}")
    if failed > 0:
        print(f"  ⚠️  Failed files remain in raw/ for retry next run")


if __name__ == "__main__":
    main()
