#!/usr/bin/env python3
"""Build docs/screenshots/06-logistics-details.png from logistics1–3 source captures."""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw

REPO_ROOT = Path(__file__).resolve().parents[1]
SHOTS = REPO_ROOT / "docs" / "screenshots"


def main() -> None:
    labels = ["Flight details", "Stay details", "Ground details"]
    parts: list[tuple[str, Image.Image]] = []
    for index, label in enumerate(labels, start=1):
        path = SHOTS / f"logistics{index}.png"
        if not path.exists():
            raise FileNotFoundError(path)
        parts.append((label, Image.open(path)))

    gap = 24
    pad = 16
    label_h = 28
    widths = [im.size[0] for _, im in parts]
    heights = [im.size[1] for _, im in parts]
    total_w = sum(widths) + gap * (len(parts) - 1) + pad * 2
    total_h = max(heights) + label_h + pad * 2
    canvas = Image.new("RGB", (total_w, total_h), "#f4efe6")
    draw = ImageDraw.Draw(canvas)
    x = pad
    for label, im in parts:
        draw.text((x, pad), label, fill="#5c5650")
        y = pad + label_h
        if im.mode == "RGBA":
            canvas.paste(im, (x, y), im)
        else:
            canvas.paste(im, (x, y))
        x += im.size[0] + gap

    out = SHOTS / "06-logistics-details.png"
    canvas.save(out, "PNG", optimize=True)
    print(f"Wrote {out} ({canvas.size[0]}x{canvas.size[1]})")


if __name__ == "__main__":
    main()
