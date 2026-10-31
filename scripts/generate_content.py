import re
import base64
import json
import os
import random
from datetime import datetime, timezone
from pathlib import Path
from io import BytesIO

import requests
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
QUEUE_FILE = ROOT / "queue" / "posts.json"
ASSET_DIR = ROOT / "assets" / "queue"
API_URL = "https://gen.pollinations.ai/v1/images/edits"
MODEL = "black-forest-labs/flux.1-kontext-pro"

CAPTIONS = [
    "Aaj ka din apne liye bhi rakho 🌷 Kabhi-kabhi chhoti si muskurahat aur khud ke liye thoda waqt hi kaafi hota hai. #SelfLove #PositiveVibes",
    "Apni khushi ko waqt do ✨ Har din ek nayi shuruaat ka mauka deta hai. #DailyThoughts #GoodVibes",
    "Chhoti khushiyan, khoobsurat pal 🌸 Aaj ek pal apne naam karo. #LifeMoments #Smile",
    "Khud par bharosa rakho 💗 Tumhari kahani apni jagah khaas hai. #Confidence #BeYourself",
]

PROMPT = """Create one photorealistic, tasteful social-media portrait photo for the Missesmaam7 Facebook page, using the uploaded photo as the primary identity reference.
CRITICAL IDENTITY PRESERVATION: depict the same adult woman as in the reference. Preserve her recognizable facial identity, face shape, eyes, eyebrows, nose, lips, skin tone, age, and natural facial proportions. Do not beautify into a different person, change ethnicity or age, or blend with another face. Keep realistic skin texture and natural human anatomy.
Create a fresh everyday editorial portrait with a different tasteful outfit, pose, background/location, and natural lighting. DSLR photography, natural Indian fashion/lifestyle aesthetic, realistic light and detail.
Safe, non-explicit, non-vulgar clothing and pose. No text, captions, logos, watermarks, collages, or extra people. Square 1:1 composition suitable for a Facebook photo post. Prioritize facial resemblance over dramatic changes. Exact identity cannot be guaranteed."""

def generate_portrait(api_key: str, reference_bytes: bytes, out_path: Path) -> None:
    try:
        with Image.open(BytesIO(reference_bytes)) as im:
            fmt = im.format
            if fmt not in ("PNG", "JPEG"):
                raise ValueError("Unsupported image format")
            mime = "image/png" if fmt == "PNG" else "image/jpeg"
            im.verify()
    except Exception as exc:
        raise RuntimeError("FACE_REFERENCE_IMAGE_BASE64 must decode to a valid JPG or PNG image.") from exc

    response = requests.post(
        API_URL,
        headers={"Authorization": f"Bearer {api_key}"},
        files={"image": ("face-reference.png" if mime == "image/png" else "face-reference.jpg", reference_bytes, mime)},
        data={"prompt": PROMPT, "model": MODEL, "size": "1024x1024"},
        timeout=300,
    )
    if not response.ok:
        raise RuntimeError(f"Pollinations image editing failed ({response.status_code}): {response.text[:1200]}")

    content_type = response.headers.get("Content-Type", "").lower()
    if content_type.startswith("image/"):
        image_bytes = response.content
    else:
        try:
            result = response.json()
            item = result["data"][0]
            if item.get("b64_json"):
                image_bytes = base64.b64decode(item["b64_json"])
            elif item.get("url"):
                downloaded = requests.get(item["url"], timeout=180)
                downloaded.raise_for_status()
                image_bytes = downloaded.content
            else:
                raise ValueError("No image payload in API response")
        except Exception as exc:
            raise RuntimeError(f"Pollinations returned an unexpected image response: {response.text[:1000]}") from exc

    try:
        with Image.open(BytesIO(image_bytes)) as im:
            im.convert("RGB").save(out_path, format="JPEG", quality=94, optimize=True)
    except Exception as exc:
        raise RuntimeError("Pollinations response did not contain a valid image.") from exc

def main():
    api_key = os.environ.get("POLLINATIONS_API_KEY", "").strip()
    reference_b64 = os.environ.get("FACE_REFERENCE_IMAGE_BASE64", "").strip()
    if not api_key:
        raise RuntimeError("Missing POLLINATIONS_API_KEY GitHub Actions secret.")
    if not reference_b64:
        raise RuntimeError("Missing FACE_REFERENCE_IMAGE_BASE64 GitHub Actions secret. Add a compressed reference photo as a secret; do not commit a private face photo to this repository.")

    queue = json.loads(QUEUE_FILE.read_text(encoding="utf-8"))
    if any(item.get("status") == "pending" for item in queue):
        print("A pending post already exists; skipping generation to avoid duplicate queue entries.")
        return

    # Accept plain Base64, wrapped Base64 with whitespace, or a data:image/...;base64, prefix.
    normalized_reference = reference_b64.strip().strip('"').strip("'")
    if normalized_reference.lower().startswith("data:") and "," in normalized_reference:
        normalized_reference = normalized_reference.split(",", 1)[1]
    normalized_reference = "".join(normalized_reference.split())
    # Tolerate accidental copied quotes or punctuation around the Base64 payload.
    normalized_reference = re.sub(r"[^A-Za-z0-9+/=_-]", "", normalized_reference)
    normalized_reference = normalized_reference.replace("-", "+").replace("_", "/")
    normalized_reference += "=" * ((4 - len(normalized_reference) % 4) % 4)

    try:
        reference_bytes = base64.b64decode(normalized_reference, validate=True)
        if not reference_bytes:
            raise ValueError("Decoded image is empty.")
    except Exception as exc:
        raise RuntimeError(
            "FACE_REFERENCE_IMAGE_BASE64 could not be decoded. Update the GitHub secret "
            "with only the Base64 text copied from PowerShell; do not include labels or commands."
        ) from exc

    # Validate the decoded payload before contacting the image provider.
    # A real JPEG starts with FF D8 FF; a PNG starts with the 8-byte PNG signature.
    is_jpeg = reference_bytes.startswith(bytes([0xFF, 0xD8, 0xFF]))
    is_png = reference_bytes.startswith(bytes([0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A]))
    if not (is_jpeg or is_png):
        preview = reference_bytes[:16].hex(" ")
        raise RuntimeError(
            "FACE_REFERENCE_IMAGE_BASE64 is not the image file. "
            f"It decoded to only {len(reference_bytes)} bytes (first bytes: {preview}). "
            "The GitHub secret likely contains the wrong clipboard text. "
            "Recreate it from reference-face-small.jpg and update the existing secret "
            "by pasting the full clipboard contents."
        )
    if len(reference_bytes) < 256:
        raise RuntimeError(
            f"Reference image is unexpectedly small ({len(reference_bytes)} bytes); "
            "recreate FACE_REFERENCE_IMAGE_BASE64 from the actual JPG/PNG file."
        )

    print(f"Reference image validated ({len(reference_bytes)} bytes; {'JPEG' if is_jpeg else 'PNG'}).")

    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    ASSET_DIR.mkdir(parents=True, exist_ok=True)
    image_path = ASSET_DIR / f"portrait-{stamp}.jpg"
    generate_portrait(api_key, reference_bytes, image_path)

    caption = random.choice(CAPTIONS)
    queue.append({
        "image": str(image_path.relative_to(ROOT)).replace("\\", "/"),
        "caption": caption,
        "status": "pending",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "generator": f"Pollinations/{MODEL}",
    })
    QUEUE_FILE.write_text(json.dumps(queue, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Generated a reference-guided portrait with Pollinations: {image_path.name}")

if __name__ == "__main__":
    main()
