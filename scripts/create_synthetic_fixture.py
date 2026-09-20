#!/usr/bin/env python3
"""Create a deterministic non-biometric image for pipeline/database tests."""

from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image, ImageDraw, PngImagePlugin


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="assets/synthetic_two_people.png")
    args = parser.parse_args()
    image = Image.new("RGB", (800, 500), (232, 236, 240))
    draw = ImageDraw.Draw(image)
    for cx, color in ((260, (57, 82, 125)), (540, (125, 78, 58))):
        draw.ellipse((cx - 100, 90, cx + 100, 290), fill=(235, 190, 150), outline=(40, 40, 40), width=3)
        draw.ellipse((cx - 45, 155, cx - 25, 175), fill=(20, 20, 20))
        draw.ellipse((cx + 25, 155, cx + 45, 175), fill=(20, 20, 20))
        draw.arc((cx - 45, 190, cx + 45, 250), 10, 170, fill=(70, 30, 30), width=4)
        draw.rectangle((cx - 140, 290, cx + 140, 500), fill=color)
    metadata = PngImagePlugin.PngInfo()
    metadata.add_text("Description", "synthetic test image with two illustrated people")
    metadata.add_text("TestFixture", "non-biometric deterministic fixture")
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    image.save(output, pnginfo=metadata)
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
