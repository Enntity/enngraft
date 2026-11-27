"""Render the Living Software repository cards with Pillow on macOS."""

import argparse
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageOps

ROOT = Path(__file__).resolve().parents[1]
FONTS = Path("/System/Library/Fonts")
PLUM = "#160f1d"
CREAM = "#fff4df"
LAVENDER = "#d2c5d5"
MINT = "#9bf4df"


def render(art, height, product, subtitle, repository):
    width = 1280
    canvas = Image.new("RGB", (width, height), PLUM)
    artwork = ImageOps.fit(art, (710, height), centering=(0.6, 0.38))
    fade = Image.new("L", (710, 1))
    fade.putdata([round(215 * min(1, x / 290)) for x in range(710)])
    canvas.paste(artwork, (570, 0), fade.resize(artwork.size))
    draw = ImageDraw.Draw(canvas)
    mono = ImageFont.truetype(str(FONTS / "Menlo.ttc"), 20)
    serif = ImageFont.truetype(str(FONTS / "Supplemental/Georgia.ttf"), 101)
    sans = ImageFont.truetype(str(FONTS / "Avenir Next.ttc"), 31, index=5)
    center = height // 2

    draw.line((67, center - 105, 1213, center - 105), fill="#715b74")
    draw.text((67, center - 136), "ENNTITY LAB  /  LIVING SOFTWARE",
              font=mono, fill=MINT, anchor="lt")
    draw.text((62, center - 70), product, font=serif, fill=CREAM, anchor="lt")
    draw.text((69, center + 51), subtitle, font=sans, fill=LAVENDER, anchor="lt")
    draw.text((69, center + 115), repository, font=mono, fill=MINT, anchor="lt")
    return canvas


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--product", default="Enngraft")
    parser.add_argument("--subtitle", default="Install from source. Repair where it runs.")
    parser.add_argument("--repository", default="github.com/Enntity/enngraft")
    parser.add_argument("--output", type=Path, default=ROOT / "docs/brand")
    args = parser.parse_args()
    with Image.open(ROOT / "docs/brand/living-software-art.jpg") as source:
        art = source.convert("RGB")
    args.output.mkdir(parents=True, exist_ok=True)
    for filename, height in (("banner.jpg", 400), ("social-preview.jpg", 640)):
        render(art, height, args.product, args.subtitle, args.repository).save(
            args.output / filename, quality=91, optimize=True
        )


if __name__ == "__main__":
    main()
