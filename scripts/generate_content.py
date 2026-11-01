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

PROMPT = """Create an ultra-photorealistic luxury beauty-campaign portrait for the Missesmaam7 Facebook page, using the uploaded photo as the primary identity reference.
CRITICAL IDENTITY PRESERVATION: depict the same adult woman from the reference photo. Preserve her recognizable facial identity, face shape, eyes, eyebrows, nose, lips, skin tone, age, and natural facial proportions. Do not turn her into a different person or change her ethnicity. Keep realistic pores, fine skin texture, natural asymmetry, and believable anatomy.
BEAUTY CAMPAIGN LOOK: premium luxury fashion editorial, expressive eyes, natural glossy lips, subtle blush, refined understated earrings, tasteful elegant outfit, flattering soft studio or cinematic portrait lighting, shallow depth of field, creamy or softly coloured background, crisp eyes, realistic skin texture, high-end 85mm portrait-lens aesthetic.
For every image, vary the outfit, hairstyle arrangement, accessories, expression, background, lighting direction, and camera framing. Each image in the same batch must have a visibly different styling concept, while retaining the same recognizable reference identity. Use tasteful, non-explicit clothing.
Ultra-photorealistic DSLR finish, natural colour grading, detailed eyes and hair, realistic facial proportions. No text, captions, logos, watermarks, extra people, collage, borders, distortions, plastic skin, cartoon, illustration, or CGI. Exact identity matching cannot be guaranteed."""

STYLE_PRESETS = [
    {"id":"cream-pearl","name":"Cream studio and pearls","prompt":"warm creamy studio background, ivory satin elegant outfit, minimal pearl earrings, soft frontal beauty light, radiant genuine smile, close beauty portrait"},
    {"id":"champagne-luxe","name":"Champagne luxury","prompt":"champagne-beige studio background, champagne satin outfit, delicate gold earrings, warm diffused light, elegant confident smile, head-and-shoulders portrait"},
    {"id":"rose-editorial","name":"Rose editorial","prompt":"muted dusty-rose background, refined blush-pink outfit, tiny crystal earrings, soft peach blush, luminous side lighting, close editorial portrait"},
    {"id":"ivory-window","name":"Ivory window light","prompt":"ivory cream background with soft window-light falloff, elegant white outfit, pearl studs, natural candid smile, three-quarter portrait"},
    {"id":"mocha-luxe","name":"Mocha luxury","prompt":"warm mocha-brown seamless background, sophisticated cocoa outfit, delicate gold jewellery, cinematic soft key light, poised expression"},
    {"id":"soft-lilac","name":"Soft lilac beauty","prompt":"pale lilac studio background, elegant lavender outfit, minimal silver earrings, flattering soft light, bright natural smile"},
    {"id":"sage-elegance","name":"Sage elegance","prompt":"muted sage-green background, refined cream outfit, understated earrings, luminous diffused light, relaxed warm smile"},
    {"id":"midnight-editorial","name":"Midnight editorial","prompt":"deep muted navy studio background, elegant dark satin outfit with tasteful neckline, pearl earrings, controlled softbox lighting, sophisticated expression"},
    {"id":"peach-campaign","name":"Peach beauty campaign","prompt":"warm pale-peach background, elegant peach-toned outfit, subtle gold studs, soft peach blush, radiant genuine smile"},
    {"id":"silver-softbox","name":"Silver softbox portrait","prompt":"soft warm-grey studio background, dove-grey outfit, minimal silver earrings, clean softbox catchlights, polished natural smile"},
    {"id":"sunlit-cream","name":"Sunlit cream editorial","prompt":"sunlit creamy beige background, elegant pastel outfit, delicate pearl accessories, warm natural sunlight, relaxed joyful smile"},
    {"id":"classic-white","name":"Classic white campaign","prompt":"clean warm-white studio background, refined white satin outfit, tiny pearl earrings, soft frontal beauty lighting, serene genuine smile"}
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
        # Refill from the full pool, while keeping this batch itself unique.
        used_in_batch = set()
        while len(available_styles) < BATCH_SIZE:
            candidate = random.choice([s for s in STYLE_PRESETS if s["id"] not in used_in_batch])
            available_styles.append(candidate)
            used_in_batch.add(candidate["id"])
    selected_styles = random.sample(available_styles, BATCH_SIZE)

    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    ASSET_DIR.mkdir(parents=True, exist_ok=True)
    for index, selected_style in enumerate(selected_styles, start=1):
        prompt = (
            PROMPT
            + "\\n\\nDistinct style for this image: "
            + selected_style["prompt"]
            + ". Make this image visibly different from the other images in this batch. "
              "Keep the same reference identity, premium beauty-campaign photography, "
              "full portrait framing, and natural realistic skin."
        )
        image_path = ASSET_DIR / f"portrait-{stamp}-{index:02d}-{selected_style['id']}.jpg"
        print(f"Generating image {index}/{BATCH_SIZE}: {selected_style['name']}")
        generate_portrait(api_key, reference_bytes, image_path, prompt)
        queue.append({
            "image": str(image_path.relative_to(ROOT)).replace("\\\\", "/"),
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
        # Gentle spacing between provider calls to reduce rate-limit/transient errors.
        if index < BATCH_SIZE:
            time.sleep(2)
    print(f"Generated {BATCH_SIZE} full-resolution, individually styled portraits in batch {stamp}.")
    QUEUE_FILE.write_text(json.dumps(queue, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Generated a reference-guided portrait with Pollinations: {image_path.name}")

if __name__ == "__main__":
    main()
