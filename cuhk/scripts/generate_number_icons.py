# -*- coding: utf-8 -*-
"""Generate red circular numbered icons (1-13) with transparent background."""
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "assets" / "numbered-icons"

SIZE = 128
RED = (220, 38, 38, 255)  # #DC2626
WHITE = (255, 255, 255, 255)
BORDER = (180, 20, 20, 255)


def load_font(size: int):
    candidates = [
        "C:/Windows/Fonts/arialbd.ttf",
        "C:/Windows/Fonts/segoeuib.ttf",
        "C:/Windows/Fonts/msyhbd.ttc",
        "C:/Windows/Fonts/arial.ttf",
    ]
    for path in candidates:
        p = Path(path)
        if p.exists():
            try:
                return ImageFont.truetype(str(p), size)
            except OSError:
                continue
    return ImageFont.load_default()


def draw_icon(n: int) -> Image.Image:
    img = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    pad = 4
    draw.ellipse(
        [pad, pad, SIZE - pad - 1, SIZE - pad - 1],
        fill=RED,
        outline=BORDER,
        width=3,
    )

    text = str(n)
    font_size = 58 if n < 10 else 48
    font = load_font(font_size)
    bbox = draw.textbbox((0, 0), text, font=font)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    x = (SIZE - tw) / 2 - bbox[0]
    y = (SIZE - th) / 2 - bbox[1] - 2
    draw.text((x, y), text, fill=WHITE, font=font)
    return img


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for n in range(1, 14):
        path = OUT_DIR / f"{n:02d}.png"
        draw_icon(n).save(path, "PNG")
        print("Wrote", path)
    print("Done:", OUT_DIR)


if __name__ == "__main__":
    main()
