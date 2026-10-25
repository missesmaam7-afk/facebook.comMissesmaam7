import base64
import json
import os
import random
from datetime import datetime, timezone
from pathlib import Path

from openai import OpenAI

ROOT = Path(__file__).resolve().parents[1]
QUEUE_FILE = ROOT / "queue" / "posts.json"
ASSET_DIR = ROOT / "assets" / "queue"

THEMES = [
    {
        "theme": "cozy feminine lifestyle portrait, warm natural window light, tasteful elegant styling",
        "direction": "a warm, relatable caption about confidence and everyday beauty",
    },
    {
        "theme": "soft editorial fashion portrait, tasteful outfit, clean pastel background, realistic photography",
        "direction": "a short caption about personal style and self-confidence",
    },
    {
        "theme": "peaceful morning lifestyle portrait, natural greenery, candid expression, cinematic photography",
        "direction": "a friendly caption about positivity and a fresh start",
    },
    {
        "theme": "elegant evening portrait, warm golden-hour lighting, tasteful modern fashion, realistic photography",
        "direction": "a graceful caption about enjoying small moments",
    },
]


def main():
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("OPENAI_API_KEY not set; AI generation skipped. Publisher will use queued posts only.")
        return

    queue = json.loads(QUEUE_FILE.read_text(encoding="utf-8"))
    if any(item.get("status") == "pending" for item in queue):
        print("A pending post already exists; skipping generation to avoid duplicate queue entries.")
        return

    theme = random.choice(THEMES)
    client = OpenAI(api_key=api_key)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    ASSET_DIR.mkdir(parents=True, exist_ok=True)
    image_path = ASSET_DIR / f"auto-{stamp}.png"

    image_prompt = (
        "Create an original, tasteful, high-quality social media photograph for a lifestyle Facebook Page. "
        f"Visual direction: {theme['theme']}. Natural realistic skin texture, authentic photographic lighting, "
        "well-composed square image, no text, no logo, no watermark. Do not imitate a real person's identity."
    )
    image_result = client.images.generate(
        model=os.getenv("OPENAI_IMAGE_MODEL", "gpt-image-1-mini"),
        prompt=image_prompt,
        size="1024x1024",
    )
    b64_image = image_result.data[0].b64_json
    if not b64_image:
        raise RuntimeError("Image API returned no image data.")
    image_path.write_bytes(base64.b64decode(b64_image))

    caption_result = client.responses.create(
        model=os.getenv("OPENAI_TEXT_MODEL", "gpt-4.1-mini"),
        input=(
            "Write one original Facebook caption in natural Hinglish (Roman Hindi), 1-2 short sentences, "
            "friendly and non-spammy. Add at most 3 relevant hashtags. Do not claim the image depicts a real "
            "person or invent personal facts. Return only the caption. Direction: " + theme["direction"]
        ),
    )
    caption = (caption_result.output_text or "").strip()
    if not caption:
        raise RuntimeError("Caption API returned empty text.")

    queue.append({
        "image": str(image_path.relative_to(ROOT)).replace("\\", "/"),
        "caption": caption,
        "status": "pending",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
    })
    QUEUE_FILE.write_text(json.dumps(queue, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Generated one image and caption: {image_path.name}")


if __name__ == "__main__":
    main()
