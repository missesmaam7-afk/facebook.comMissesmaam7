import base64
import json
import os
import random
from datetime import datetime, timezone
from pathlib import Path

import requests
from PIL import Image
from io import BytesIO

ROOT = Path(__file__).resolve().parents[1]
QUEUE_FILE = ROOT / "queue" / "posts.json"
ASSET_DIR = ROOT / "assets" / "queue"
API_URL = "https://generativelanguage.googleapis.com/v1beta/interactions"
MODEL = "gemini-nano-banana-2.1"

CAPTIONS = [
    "Aaj ka din apne liye bhi rakho 🌷 Kabhi-kabhi chhoti si muskurahat aur khud ke liye thoda waqt hi kaafi hota hai. #SelfLove #PositiveVibes",
    "Apni khushi ko waqt do ✨ Har din ek nayi shuruaat ka mauka deta hai. #DailyThoughts #GoodVibes",
    "Chhoti khushiyan, khoobsurat pal 🌸 Aaj ek pal apne naam karo. #LifeMoments #Smile",
    "Khud par bharosa rakho 💗 Tumhari kahani apni jagah khaas hai. #Confidence #BeYourself",
]

PROMPT = """Create one photorealistic, tasteful social-media portrait photo for the Missesmaam7 Facebook page, using the supplied reference photo as the identity reference.
CRITICAL IDENTITY PRESERVATION: depict the same adult woman as in the reference. Preserve her recognizable facial identity, face shape, eyes, eyebrows, nose, lips, skin tone, age, and natural facial proportions. Do not beautify into a different person, do not change ethnicity or age, and do not blend with another face. Keep realistic skin texture and natural human anatomy.
Create a fresh everyday editorial portrait with a different tasteful outfit, pose, background/location, and natural lighting from a typical reference selfie. Make the result look like a real DSLR photograph, not illustration, not CGI, not a beauty filter, not plastic skin. Natural Indian fashion/lifestyle aesthetic, clean composition, flattering but realistic light, high detail.
Safe, non-explicit, non-vulgar clothing and pose. No text, captions, logos, watermarks, collages, or extra people. Square 1:1 composition suitable for a Facebook photo post.
The reference photo is authorized for this use. Preserve the person's identity as closely as the model can; if exact identity cannot be maintained, prioritize facial resemblance over dramatic changes to styling or scene."""

def generate_portrait(api_key: str, reference_bytes: bytes, out_path: Path) -> None:
    try:
        with Image.open(BytesIO(reference_bytes)) as im:
            mime = "image/png" if im.format == "PNG" else "image/jpeg"
    except Exception as exc:
        raise RuntimeError("FACE_REFERENCE_IMAGE_BASE64 must decode to a valid JPG or PNG image.") from exc

    payload = {
        "model": MODEL,
        "input": [
            {"type": "text", "text": PROMPT},
            {"type": "image", "mime_type": mime, "data": base64.b64encode(reference_bytes).decode("ascii")},
        ],
    }
    response = requests.post(
        API_URL,
        headers={"x-goog-api-key": api_key, "Content-Type": "application/json"},
        json=payload,
        timeout=300,
    )
    if not response.ok:
        raise RuntimeError(f"Google image generation failed ({response.status_code}): {response.text[:1200]}")
    data = response.json()

    # Interactions API returns image content blocks in model_output steps.
    for step in data.get("steps", []):
        if step.get("type") != "model_output":
            continue
        for block in step.get("content", []):
            if block.get("type") == "image" and block.get("data"):
                image_bytes = base64.b64decode(block["data"])
                with Image.open(BytesIO(image_bytes)) as im:
                    im.convert("RGB").save(out_path, format="JPEG", quality=94, optimize=True)
                return

    raise RuntimeError("Google API returned no image. Check that this API key has access to the selected image model and that image generation is enabled.")

def main():
    api_key = os.environ.get("GEMINI_API_KEY", "").strip()
    reference_b64 = os.environ.get("FACE_REFERENCE_IMAGE_BASE64", "").strip()
    if not api_key:
        raise RuntimeError("Missing GEMINI_API_KEY GitHub Actions secret.")
    if not reference_b64:
        raise RuntimeError("Missing FACE_REFERENCE_IMAGE_BASE64 GitHub Actions secret. Add a compressed reference photo as a secret; do not commit a private face photo to this public repository.")

    queue = json.loads(QUEUE_FILE.read_text(encoding="utf-8"))
    if any(item.get("status") == "pending" for item in queue):
        print("A pending post already exists; skipping generation to avoid duplicate queue entries.")
        return

    try:
        reference_bytes = base64.b64decode(reference_b64, validate=True)
    except Exception as exc:
        raise RuntimeError("FACE_REFERENCE_IMAGE_BASE64 is not valid base64.") from exc

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
        "generator": MODEL,
    })
    QUEUE_FILE.write_text(json.dumps(queue, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Generated a reference-guided portrait: {image_path.name}")

if __name__ == "__main__":
    main()
