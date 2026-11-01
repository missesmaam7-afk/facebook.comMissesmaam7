import re
import base64
import json
import os
import random
import time
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

BATCH_SIZE = 4
IMAGE_SIZE = "1024x1536"  # Full-resolution portrait orientation; saved without downscaling.

PROMPT = """Create ONE ultra-photorealistic standalone Indian fashion editorial photograph for every API request. Use the uploaded face image as the primary identity reference.
IDENTITY LOCK: the woman must remain the same adult woman shown in the uploaded face reference. Preserve her recognizable facial identity, facial proportions, eyes, eyebrows, nose, lips, skin tone, age and natural asymmetry. Do not invent a different face or change her ethnicity. Realistic skin pores and natural texture; no beauty-filter plastic skin.
MATCH THE PROVIDED OUTFIT REFERENCE EXACTLY IN ALL FOUR IMAGES: rich deep ruby-red traditional Indian saree, fine all-over gold floral embroidery, matching red sleeveless fitted blouse with the same delicate gold embroidered pattern, sheer red pallu with a prominent intricate gold embroidered border. Keep the saree colour, blouse design, embroidery, jewellery and styling consistent across the whole batch. Add small traditional gold jhumka earrings and delicate gold bangles. Elegant, tasteful Indian festive fashion styling.
MATCH THE PROVIDED LOCATION REFERENCE: luxurious pale cream/beige carved sandstone or ivory-marble palace courtyard, ornate carved pillars and arches, leafy green garden, small red/pink flowers and subtle heritage seating. Keep this same palace-courtyard visual world in every image. Warm late-afternoon golden sunlight, natural shadows and soft cinematic background blur.
PHOTOGRAPHIC QUALITY: real DSLR fashion photograph, warm natural skin tones, detailed individual hair strands and saree embroidery, sharp expressive eyes, realistic fabric drape, premium Indian fashion magazine editorial, 85mm portrait-lens look, shallow depth of field, balanced exposure, high detail.
POSE VARIATION ONLY: use the per-image pose instruction to change body pose, expression, framing and camera angle. Do not change the woman's identity, saree colour/design, blouse, jewellery or overall palace courtyard setting.
OUTPUT RULE: create exactly ONE separate full-size vertical portrait photograph per request. Never create a collage, grid, contact sheet, diptych, triptych, split screen, multi-panel image or duplicate subject. No text, captions, logos, watermarks, borders, frames, extra people, distorted anatomy, cartoon, illustration or CGI. Exact identity matching cannot be guaranteed."""

STYLE_PRESETS = [
    {"id":"red-saree-standing","name":"Red saree standing portrait","prompt":"full-length standing portrait beside a carved palace pillar, one hand gently touching her hair, graceful direct gaze, entire red saree and gold-bordered pallu visible"},
    {"id":"red-saree-seated","name":"Red saree seated courtyard","prompt":"seated gracefully on a carved sandstone courtyard bench, one elbow resting lightly and hand near cheek, warm gentle smile, medium-wide three-quarter composition"},
    {"id":"red-saree-over-shoulder","name":"Red saree over-shoulder pose","prompt":"elegant over-the-shoulder three-quarter pose, face turned naturally toward camera, long hair falling down her back and the same red gold-embroidered pallu clearly visible"},
    {"id":"red-saree-pallu-pose","name":"Red saree pallu pose","prompt":"standing near a carved arch while lightly arranging the sheer red embroidered pallu, eyes softly lowered with a subtle smile, medium full-body composition"},
    {"id":"red-saree-closeup","name":"Red saree close-up","prompt":"intimate head-and-shoulders beauty portrait, natural expressive face and gold jhumka earrings, red embroidered saree visible at shoulders, soft golden backlight"},
    {"id":"red-saree-garden","name":"Red saree garden portrait","prompt":"three-quarter portrait near leafy palace garden plants and subtle flowers, one hand resting lightly near hair, candid warm smile, elegant natural pose"},
    {"id":"red-saree-profile","name":"Red saree side profile","prompt":"graceful side-profile portrait beside an ivory carved pillar, face gently turned toward camera, flowing hair and gold-bordered red pallu catching warm sunlight"},
    {"id":"red-saree-balcony","name":"Red saree heritage balcony","prompt":"full-length standing pose beside a carved heritage balcony railing, one hand resting lightly on the stone railing, palace garden softly blurred behind her"}
]

def generate_portrait(api_key: str, reference_bytes: bytes, out_path: Path, prompt: str) -> None:
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
        data={"prompt": prompt, "model": MODEL, "size": IMAGE_SIZE, "quality": "high", "seed": str(random.randint(1, 2147483646))},
        timeout=300,
    )
    if response.status_code == 401:
        raise RuntimeError("Pollinations rejected POLLINATIONS_API_KEY (HTTP 401). The GitHub secret is missing, invalid, expired, or not a server-side sk_ secret key. Create a new secret key at https://enter.pollinations.ai/keys, update Settings > Secrets and variables > Actions > POLLINATIONS_API_KEY, then rerun the workflow. The key was not printed.")
    if response.status_code == 402:
        raise RuntimeError("Pollinations authenticated the API key but the account or key budget is exhausted (HTTP 402). Check the Pollinations balance and key budget at https://enter.pollinations.ai/keys.")
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
        raise RuntimeError("Missing POLLINATIONS_API_KEY GitHub Actions secret. Create a secret key at https://enter.pollinations.ai/keys and save it in GitHub Actions Secrets.")
    if not api_key.startswith("sk_"):
        raise RuntimeError("POLLINATIONS_API_KEY must be a Pollinations server-side secret key beginning with sk_. Do not use a pk_ App Key or paste the key into repository files.")
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

    recent_style_ids = {
        item.get("style_id") for item in queue
        if item.get("style_id") and item.get("status") in ("pending", "published")
    }
    available_styles = [style for style in STYLE_PRESETS if style["id"] not in recent_style_ids]
    if len(available_styles) < BATCH_SIZE:
        # If the recent-history filter leaves too few options, refill with styles
        # not already selected for this batch. No duplicate styles in one batch.
        available_ids = {style["id"] for style in available_styles}
        refill = [style for style in STYLE_PRESETS if style["id"] not in available_ids]
        available_styles.extend(refill)
    selected_styles = random.sample(available_styles, BATCH_SIZE)

    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    ASSET_DIR.mkdir(parents=True, exist_ok=True)
    for index, selected_style in enumerate(selected_styles, start=1):
        prompt = (
            PROMPT
            + "\n\nPose and camera variation for this image: "
            + selected_style["prompt"]
            + ". Make this image visibly different from the other images in this batch. "
              "Keep the same reference identity, premium beauty-campaign photography, "
              "same red saree outfit, same jewellery, same palace courtyard, and natural realistic skin."
        )
        image_path = ASSET_DIR / f"portrait-{stamp}-{index:02d}-{selected_style['id']}.jpg"
        print(f"Generating image {index}/{BATCH_SIZE}: {selected_style['name']}")
        generate_portrait(api_key, reference_bytes, image_path, prompt)
        queue.append({
            "image": str(image_path.relative_to(ROOT)).replace("\\", "/"),
            "caption": random.choice(CAPTIONS),
            "status": "pending",
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
            "generator": f"Pollinations/{MODEL}",
            "style_id": selected_style["id"],
            "style_name": selected_style["name"],
            "batch_id": stamp,
            "batch_index": index,
            "batch_size": BATCH_SIZE,
            "image_size": IMAGE_SIZE,
        })
        QUEUE_FILE.write_text(json.dumps(queue, ensure_ascii=False, indent=2) + "\\n", encoding="utf-8")
        # Gentle spacing between provider calls to reduce rate-limit/transient errors.
        if index < BATCH_SIZE:
            time.sleep(2)
    print(f"Generated {BATCH_SIZE} full-resolution, individually styled portraits in batch {stamp}.")
    QUEUE_FILE.write_text(json.dumps(queue, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Batch queue saved with {BATCH_SIZE} full-size portraits; publisher will post one queued image per scheduled run.")

if __name__ == "__main__":
    main()
