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

PROMPT = """Create a highly photorealistic, natural full-body lifestyle photograph for the Missesmaam7 Facebook page, using the uploaded photo as the primary identity reference.
CRITICAL IDENTITY PRESERVATION: depict the same adult woman as in the reference. Preserve her recognizable facial identity, face shape, eyes, eyebrows, nose, lips, skin tone, age, and natural facial proportions. Do not change her identity, ethnicity, age, or blend her face with another person. Keep realistic skin pores, natural facial detail, and believable anatomy.
VISUAL STYLE TARGET: match a candid premium DSLR lifestyle photograph: one adult Indian woman standing naturally in a beautiful real-world outdoor setting, preferably a lush rooftop terrace or garden with potted plants and greenery, warm soft daylight, gentle background depth, realistic shadows, natural colours, and uncluttered composition. Show her from head to toe with full outfit and feet visible; place her near the centre with comfortable space around her. Natural relaxed expression and believable casual pose, not a fashion runway pose.
Vary the outfit, colour palette, pose, garden arrangement, camera distance, and background details for every post while keeping this same realistic everyday lifestyle-photo aesthetic. Use tasteful modest contemporary Indian casual clothing such as a simple top with a flowing skirt, kurta with palazzo, or elegant casual dress. Clothing should look naturally fitted and opaque. Barefoot only when it suits a safe home-terrace setting; otherwise simple flats or sandals.
Photorealistic DSLR quality, natural skin texture, realistic hands and feet, accurate proportions, soft golden-hour or bright diffused daylight. No illustration, CGI, anime, beauty-filter skin, exaggerated body proportions, glamour retouching, text, captions, logos, watermarks, collages, borders, or extra people. Vertical 4:5 or portrait-oriented composition if supported; otherwise square 1:1 crop with the entire person safely inside frame. Prioritize facial resemblance and natural realism. Exact identity cannot be guaranteed."""

STYLE_PRESETS = [
    {
        "id": "garden",
        "name": "Sunlit garden",
        "prompt": "flowering garden, pastel floral outfit, morning sunlight, candid three-quarter pose"
    },
    {
        "id": "heritage",
        "name": "Heritage courtyard",
        "prompt": "Indian haveli courtyard, teal traditional outfit, sandstone arches, late-afternoon light"
    },
    {
        "id": "studio",
        "name": "Minimal studio",
        "prompt": "warm beige studio, ivory outfit, softbox lighting, elegant seated pose"
    },
    {
        "id": "monsoon",
        "name": "Monsoon window",
        "prompt": "rainy window setting, sage outfit, diffused daylight, relaxed seated pose"
    },
    {
        "id": "rooftop",
        "name": "Golden-hour rooftop",
        "prompt": "city rooftop at golden hour, rose outfit, skyline bokeh, candid portrait"
    },
    {
        "id": "coastal",
        "name": "Coastal breeze",
        "prompt": "coastal promenade, powder-blue outfit, soft seaside daylight, relaxed pose"
    },
    {
        "id": "cafe",
        "name": "Book cafe",
        "prompt": "warm book cafe, maroon outfit, window light, candid lifestyle portrait"
    },
    {
        "id": "botanical",
        "name": "Botanical conservatory",
        "prompt": "glass conservatory, tropical plants, cream-and-green outfit, filtered daylight"
    },
    {
        "id": "festive",
        "name": "Festive lantern evening",
        "prompt": "festive courtyard, distant warm lanterns, wine-coloured traditional outfit, evening portrait"
    },
    {
        "id": "urban",
        "name": "Pastel urban editorial",
        "prompt": "pastel modern architecture, lavender outfit, bright soft daylight, fashion editorial"
    },
    {
        "id": "terrace",
        "name": "Terrace morning",
        "prompt": "sunlit terrace, potted plants, peach outfit, fresh morning light, smiling candid pose"
    },
    {
        "id": "gallery",
        "name": "Modern art gallery",
        "prompt": "minimal art gallery, charcoal outfit, directional lighting, poised editorial portrait"
    }
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
        data={"prompt": prompt, "model": MODEL, "size": "1024x1024", "seed": str(random.randint(1, 2147483646))},
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

    recent_style_ids = {item.get("style_id") for item in queue if item.get("style_id") and item.get("status") in ("pending", "published")}
    available_styles = [style for style in STYLE_PRESETS if style["id"] not in recent_style_ids] or STYLE_PRESETS.copy()
    selected_style = random.choice(available_styles)
    prompt = PROMPT + "\n\nDistinct visual direction for this post: " + selected_style["prompt"] + ". Make the outfit, pose, setting, composition and lighting follow this concept."

    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    ASSET_DIR.mkdir(parents=True, exist_ok=True)
    image_path = ASSET_DIR / f"portrait-{stamp}.jpg"
    generate_portrait(api_key, reference_bytes, image_path, prompt)

    caption = random.choice(CAPTIONS)
    queue.append({
        "image": str(image_path.relative_to(ROOT)).replace("\\", "/"),
        "caption": caption,
        "status": "pending",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "generator": f"Pollinations/{MODEL}",
        "style_id": selected_style["id"],
        "style_name": selected_style["name"],
    })
    QUEUE_FILE.write_text(json.dumps(queue, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Generated a reference-guided portrait with Pollinations: {image_path.name}")

if __name__ == "__main__":
    main()
