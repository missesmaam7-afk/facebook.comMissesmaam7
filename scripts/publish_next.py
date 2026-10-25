import json
import os
import sys
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
QUEUE_FILE = ROOT / "queue" / "posts.json"
GRAPH_VERSION = os.getenv("FACEBOOK_GRAPH_API_VERSION", "v23.0")
PAGE_ID = os.getenv("FACEBOOK_PAGE_ID")
TOKEN = os.getenv("FACEBOOK_PAGE_ACCESS_TOKEN")


def main():
    if not PAGE_ID or not TOKEN:
        sys.exit("Missing FACEBOOK_PAGE_ID or FACEBOOK_PAGE_ACCESS_TOKEN GitHub secrets.")

    queue = json.loads(QUEUE_FILE.read_text(encoding="utf-8"))
    pending = next((p for p in queue if p.get("status") == "pending"), None)
    if not pending:
        print("No pending post in queue; nothing published.")
        return

    image_path = ROOT / pending["image"]
    if not image_path.is_file():
        sys.exit(f"Queued image not found: {image_path}")

    url = f"https://graph.facebook.com/{GRAPH_VERSION}/{PAGE_ID}/photos"
    with image_path.open("rb") as image_file:
        response = requests.post(
            url,
            data={
                "caption": pending.get("caption", ""),
                "access_token": TOKEN,
            },
            files={"source": image_file},
            timeout=120,
        )

    if not response.ok:
        # Do not mark the post as published when the API reports an error.
        sys.exit(f"Facebook API error {response.status_code}: {response.text[:1500]}")

    result = response.json()
    pending["status"] = "published"
    pending["facebook_post_id"] = result.get("post_id") or result.get("id")
    pending["published_at_utc"] = __import__("datetime").datetime.now(
        __import__("datetime").timezone.utc
    ).isoformat()
    QUEUE_FILE.write_text(json.dumps(queue, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Published queued photo. Facebook media id: {pending.get('facebook_post_id')}")


if __name__ == "__main__":
    main()
