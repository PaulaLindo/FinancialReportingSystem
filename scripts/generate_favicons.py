#!/usr/bin/env python3
"""Generate centered favicons from static/images/logo.png (icon mark only, no wordmark)."""

from __future__ import annotations

from pathlib import Path

from PIL import Image
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
LOGO = ROOT / "static" / "images" / "logo.png"
OUT_DIR = ROOT / "static" / "images"

# Rows above this fraction are treated as the square icon (excludes "VARYDIAN" text).
ICON_TOP_FRACTION = 0.48
# Minimal padding — mark fills the tab icon (16–32px).
PADDING_RATIO = 0.02
CONTENT_THRESHOLD = 250


def _content_bbox(arr: np.ndarray) -> tuple[int, int, int, int] | None:
    mask = (arr[:, :, :3] < CONTENT_THRESHOLD).any(axis=2)
    ys, xs = np.where(mask)
    if len(xs) == 0:
        return None
    return int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())


def extract_centered_icon_mark(logo_path: Path) -> Image.Image:
    src = Image.open(logo_path).convert("RGBA")
    w, h = src.size
    icon_h = max(1, int(h * ICON_TOP_FRACTION))
    icon_strip = src.crop((0, 0, w, icon_h))
    band = np.array(icon_strip)

    bbox = _content_bbox(band)
    if bbox is None:
        side = min(w, h)
        left = (w - side) // 2
        top = (h - side) // 2
        return src.crop((left, top, left + side, top + side))

    x0, y0, x1, y1 = bbox
    patch = icon_strip.crop((x0, y0, x1 + 1, y1 + 1))
    pw, ph = patch.size
    content_side = max(pw, ph)
    pad = int(content_side * PADDING_RATIO)
    side = content_side + 2 * pad

    canvas = Image.new("RGBA", (side, side), (255, 255, 255, 0))
    paste_x = (side - pw) // 2
    paste_y = (side - ph) // 2
    canvas.paste(patch, (paste_x, paste_y), patch)
    return canvas


def write_favicons(mark: Image.Image, out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    for size, name in ((16, "favicon-16.png"), (32, "favicon-32.png"), (180, "apple-touch-icon.png")):
        mark.resize((size, size), Image.Resampling.LANCZOS).save(out_dir / name)
    icon32 = mark.resize((32, 32), Image.Resampling.LANCZOS)
    icon32.save(out_dir / "favicon.ico", format="ICO", sizes=[(32, 32)])


def main() -> None:
    if not LOGO.is_file():
        raise SystemExit(f"Logo not found: {LOGO}")
    mark = extract_centered_icon_mark(LOGO)
    write_favicons(mark, OUT_DIR)
    print(f"Wrote favicons to {OUT_DIR} (mark size {mark.size[0]}x{mark.size[1]})")


if __name__ == "__main__":
    main()
