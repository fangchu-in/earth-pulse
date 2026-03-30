import os
from PIL import Image
from datetime import datetime, timedelta
import piexif
import boto3

# ─────────────────────────────────────────────
# 📁 PATH CONFIG (CHANGE ONLY IF NEEDED)
# ─────────────────────────────────────────────
BASE = "/home/fangchu/earth_pulse/pictures"

RAW = f"{BASE}/raw"
PROCESSED = f"{BASE}/processed"
DELETE = f"{BASE}/delete"

os.makedirs(RAW, exist_ok=True)
os.makedirs(PROCESSED, exist_ok=True)
os.makedirs(DELETE, exist_ok=True)

# ─────────────────────────────────────────────
# ☁️ CLOUDFLARE R2 CONFIG (FILL THESE)
# ─────────────────────────────────────────────

# 👉 From Cloudflare dashboard URL
R2_ACCOUNT_ID = "e340725bb3d0ace4725db23e1516a2a1"

# 👉 Your bucket name
R2_BUCKET = "earthpulse-files"

# 👉 Create from: R2 → Manage API Tokens
R2_ACCESS_KEY = "d86eefd24044c011eee6d74dd1930982"
R2_SECRET_KEY = "030f2d0372692dcbc1623bd476b4266c7f707ba941eed0a74f86b5bb7f057130"

# 👉 DO NOT CHANGE
R2_ENDPOINT = f"https://{R2_ACCOUNT_ID}.r2.cloudflarestorage.com"

# ─────────────────────────────────────────────
# 🔌 R2 CONNECTION
# ─────────────────────────────────────────────
s3 = boto3.client(
    "s3",
    endpoint_url=R2_ENDPOINT,
    aws_access_key_id=R2_ACCESS_KEY,
    aws_secret_access_key=R2_SECRET_KEY
)

# ─────────────────────────────────────────────
# 🧠 HELPER FUNCTIONS
# ─────────────────────────────────────────────

def get_exif_time(path):
    """
    Extract timestamp from EXIF.
    Fallback to file modified time if EXIF missing.
    """
    try:
        exif = piexif.load(path)
        dt = exif["0th"][piexif.ImageIFD.DateTime].decode()
        return datetime.strptime(dt, "%Y:%m:%d %H:%M:%S")
    except:
        return datetime.fromtimestamp(os.path.getmtime(path))


def to_ist(dt):
    """
    Convert UTC/local → IST
    """
    return dt + timedelta(hours=5, minutes=30)


def get_unique_filename(folder, filename):
    """
    Prevent overwrite if same timestamp appears twice
    """
    name, ext = os.path.splitext(filename)
    counter = 1

    new_path = os.path.join(folder, filename)

    while os.path.exists(new_path):
        filename = f"{name}_{counter}{ext}"
        new_path = os.path.join(folder, filename)
        counter += 1

    return filename, new_path


def upload_to_r2(local_path, filename, dt):
    """
    Upload to Cloudflare R2 using date-based folders
    """
    folder = dt.strftime("hill/%Y/%m/%d")
    key = f"{folder}/{filename}"

    s3.upload_file(
        local_path,
        R2_BUCKET,
        key,
        ExtraArgs={"ContentType": "image/jpeg"}
    )

    print(f"☁️ Uploaded → {key}")


def process_image(file):
    """
    Core pipeline:
    RAW → RESIZE → SAVE → UPLOAD → MOVE
    """
    raw_path = os.path.join(RAW, file)

    try:
        # 1. Get timestamp
        dt = get_exif_time(raw_path)
        dt = to_ist(dt)

        # 2. Create filename
        filename = dt.strftime("%Y-%m-%d_%H-%M.jpg")

        # 3. Avoid duplicates
        filename, output_path = get_unique_filename(PROCESSED, filename)

        # 4. Open image
        img = Image.open(raw_path)

        # 5. Resize (efficient + good quality)
        img.thumbnail((1280, 720))

        # 6. Save processed image
        img.save(output_path, "JPEG", quality=75, optimize=True)

        print(f"🖼️ Processed → {filename}")

        # 7. Upload to R2
        upload_to_r2(output_path, filename, dt)

        # 8. Move RAW → DELETE folder
        os.rename(raw_path, os.path.join(DELETE, file))

        print(f"🗑️ Moved RAW → delete/{file}")

    except Exception as e:
        print(f"❌ Error processing {file}: {e}")


# ─────────────────────────────────────────────
# 🚀 MAIN RUNNER
# ─────────────────────────────────────────────

def main():
    files = os.listdir(RAW)

    if not files:
        print("📭 No new images")
        return

    for file in files:
        if file.lower().endswith((".jpg", ".jpeg")):
            process_image(file)


if __name__ == "__main__":
    main()