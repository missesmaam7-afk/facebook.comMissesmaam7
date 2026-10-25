import json
import math
import random
from datetime import datetime, timezone
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
QUEUE_FILE = ROOT / "queue" / "posts.json"
ASSET_DIR = ROOT / "assets" / "queue"

POSTS = [
    ("Aaj ka din apne liye bhi rakho 🌷", "Kabhi-kabhi chhoti si muskurahat aur khud ke liye thoda waqt hi kaafi hota hai. Aaj apna khayal zaroor rakhna. #SelfLove #PositiveVibes"),
    ("Apni roshni khud bano ✨", "Har din perfect nahi hota, lekin har din ek nayi shuruaat ka mauka deta hai. Dheere chalo, bas rukna mat. #DailyThoughts #GoodVibes"),
    ("Chhoti khushiyan, khoobsurat pal 🌸", "Zindagi ki khoobsurati aksar un chhote lamhon mein hoti hai jinhe hum jaldi mein bhool jaate hain. Aaj ek pal apne naam karo. #LifeMoments #Smile"),
    ("Khud par bharosa rakho 💗", "Apni journey ko kisi aur se compare mat karo. Tumhara waqt, tumhari raftaar aur tumhari kahani apni jagah khaas hai. #Confidence #BeYourself"),
]

def load_font(size):
    for path in ("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
                 "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf"):
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            pass
    return ImageFont.load_default()

def make_art(path, headline, seed):
    random.seed(seed)
    size = 1024
    image = Image.new("RGB", (size, size))
    pixels = image.load()
    top = (255, 225, 220)
    bottom = (247, 202, 218)
    for y in range(size):
        t = y / (size - 1)
        row = tuple(int(top[i] * (1 - t) + bottom[i] * t) for i in range(3))
        for x in range(size):
            pixels[x, y] = row
    draw = ImageDraw.Draw(image, "RGBA")
    # Soft editorial-style botanical shapes, generated locally without paid APIs.
    draw.ellipse((-180, -130, 470, 520), fill=(255, 247, 231, 150))
    draw.ellipse((610, 580, 1200, 1170), fill=(219, 151, 178, 95))
    draw.ellipse((680, -120, 1150, 350), fill=(255, 244, 229, 115))
    for _ in range(22):
        x = random.randint(70, 950)
        y = random.randint(90, 930)
        r = random.randint(10, 25)
        draw.ellipse((x-r, y-r, x+r, y+r), fill=(255, 255, 255, random.randint(35, 90)))
    # Decorative petals near the corners
    for cx, cy, scale in [(145, 760, 1.0), (860, 255, 0.8), (820, 830, 0.65)]:
        for angle in range(0, 360, 60):
            rad = math.radians(angle)
            px = cx + math.cos(rad) * 38 * scale
            py = cy + math.sin(rad) * 38 * scale
            rr = 23 * scale
            draw.ellipse((px-rr, py-rr*1.4, px+rr, py+rr*1.4), fill=(255, 250, 246, 150))
        draw.ellipse((cx-12*scale, cy-12*scale, cx+12*scale, cy+12*scale), fill=(194, 116, 142, 210))
    # Central translucent card
    draw.rounded_rectangle((112, 270, 912, 745), radius=42, fill=(255, 250, 247, 220), outline=(255, 255, 255, 235), width=4)
    title_font = load_font(54)
    subtitle_font = load_font(27)
    words = headline.split()
    lines, line = [], ""
    for word in words:
        candidate = (line + " " + word).strip()
        if draw.textbbox((0, 0), candidate, font=title_font)[2] > 690 and line:
            lines.append(line)
            line = word
        else:
            line = candidate
    if line:
        lines.append(line)
    line_heights = [draw.textbbox((0, 0), s, font=title_font)[3] for s in lines]
    y = 390 - sum(line_heights) // 2
    for s, h in zip(lines, line_heights):
        box = draw.textbbox((0, 0), s, font=title_font)
        x = (size - (box[2] - box[0])) // 2
        draw.text((x, y), s, font=title_font, fill=(91, 55, 70, 255), stroke_width=0)
        y += h + 18
    footer = "EK CHHOTI SI YAAD — APNA KHAYAL RAKHO"
    box = draw.textbbox((0, 0), footer, font=subtitle_font)
    draw.text(((size - (box[2]-box[0]))//2, 650), footer, font=subtitle_font, fill=(137, 83, 105, 255))
    image.save(path, format="PNG", optimize=True)

def main():
    queue = json.loads(QUEUE_FILE.read_text(encoding="utf-8"))
    if any(item.get("status") == "pending" for item in queue):
        print("A pending post already exists; skipping generation to avoid duplicate queue entries.")
        return
    headline, caption = random.choice(POSTS)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    ASSET_DIR.mkdir(parents=True, exist_ok=True)
    image_path = ASSET_DIR / f"free-auto-{stamp}.png"
    make_art(image_path, headline, stamp)
    queue.append({
        "image": str(image_path.relative_to(ROOT)).replace("\\", "/"),
        "caption": caption,
        "status": "pending",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
    })
    QUEUE_FILE.write_text(json.dumps(queue, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Generated a free local image and caption: {image_path.name}")

if __name__ == "__main__":
    main()
