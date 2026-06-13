"""
Renderer: Composites scored images onto the 1080×1620 canvas.

Layout:
  • Bottom — black text container, height auto-fits the caption (snug).
  • Top    — gapless image mosaic filling all remaining space (no gutters,
             no outer margins, flush edges).
  • Logo   — bottom-left corner of the image zone.

The image zone height is dynamic: the text box takes exactly the space the
(≤60-word) caption needs, and the images get everything that is left.
"""

from __future__ import annotations

import os

from PIL import Image, ImageDraw

from .layouts import CANVAS_WIDTH, CANVAS_HEIGHT, OUTER_MARGIN, GUTTER
from .smart_crop_engine import SmartCropEngine
from .text_overlay import TextOverlayEngine, TEXT_PAD_Y

# Keep the image zone dominant even with a long caption.
MIN_IMAGE_ZONE_RATIO = 0.55                       # images ≥ 55% of canvas
MAX_TEXT_ZONE_H = int(CANVAS_HEIGHT * (1 - MIN_IMAGE_ZONE_RATIO))

# Logo placement (bottom-left of the image zone)
LOGO_MAX_W  = 230
LOGO_MAX_H  = 90
LOGO_MARGIN = 22
LOGO_PATH   = os.path.join(os.path.dirname(__file__), "..", "static", "logo.png")


def _close_gaps(slot: dict) -> dict:
    """
    Expand a slot's edges to remove the 16px outer margins and 8px gutters,
    so the slots tile the full 1080×1620 canvas with no gaps.
    """
    half = GUTTER // 2
    x1, y1 = slot["x"], slot["y"]
    x2, y2 = slot["x"] + slot["w"], slot["y"] + slot["h"]

    nx1 = 0 if x1 <= OUTER_MARGIN else x1 - half
    ny1 = 0 if y1 <= OUTER_MARGIN else y1 - half
    nx2 = CANVAS_WIDTH  if x2 >= CANVAS_WIDTH  - OUTER_MARGIN else x2 + half
    ny2 = CANVAS_HEIGHT if y2 >= CANVAS_HEIGHT - OUTER_MARGIN else y2 + half

    return {"slot": slot["slot"], "x": nx1, "y": ny1, "w": nx2 - nx1, "h": ny2 - ny1}


def _scale_y(slot: dict, factor: float) -> dict:
    """Scale a slot's vertical extent so the mosaic fits the image zone."""
    return {
        "slot": slot["slot"],
        "x": slot["x"],
        "y": int(round(slot["y"] * factor)),
        "w": slot["w"],
        "h": max(1, int(round(slot["h"] * factor))),
    }


class Renderer:

    def __init__(self) -> None:
        self._cropper = SmartCropEngine()
        self._text = TextOverlayEngine()

    def render(
        self,
        layout: dict,
        scored_images: list,
        output_path: str | None = None,
        caption: str | None = None,
    ) -> Image.Image:
        caption = (caption or "").strip()

        # ── 1. Decide the text-zone height from the caption (dynamic) ──
        text_zone_h = 0
        text_lines: list[str] = []
        if caption:
            text_zone_h = self._text.measure_zone_height(caption, CANVAS_WIDTH)
            text_zone_h = min(text_zone_h, MAX_TEXT_ZONE_H)
            # Re-wrap with the line cap implied by the (possibly clamped) height
            max_lines = max(1, (text_zone_h - 2 * TEXT_PAD_Y) // self._text.line_height)
            text_lines = self._text.layout_lines(caption, CANVAS_WIDTH, max_lines=max_lines)

        image_zone_h = CANVAS_HEIGHT - text_zone_h
        text_zone_y = image_zone_h

        canvas = Image.new("RGBA", (CANVAS_WIDTH, CANVAS_HEIGHT), (255, 255, 255, 255))

        # ── 2. Gapless image mosaic in the image zone ──────────────────
        y_factor = image_zone_h / CANVAS_HEIGHT
        slots = [_scale_y(_close_gaps(s), y_factor) for s in layout["slots"]]

        for i, slot in enumerate(slots):
            if i >= len(scored_images):
                break
            pil_img = Image.open(scored_images[i].analysis.path).convert("RGB")
            cropped = self._cropper.crop(pil_img, slot["w"], slot["h"])
            canvas.paste(cropped.convert("RGBA"), (slot["x"], slot["y"]))

        # ── 3. Logo — bottom-left of image zone ────────────────────────
        self._draw_logo(canvas, image_zone_h)

        # ── 4. Black text container + centred caption ──────────────────
        if text_zone_h > 0:
            draw = ImageDraw.Draw(canvas)
            draw.rectangle(
                [(0, text_zone_y), (CANVAS_WIDTH - 1, CANVAS_HEIGHT - 1)],
                fill=(0, 0, 0, 255),
            )
            self._text.draw_lines(
                canvas, text_lines,
                zone_x=0, zone_y=text_zone_y,
                zone_w=CANVAS_WIDTH, zone_h=text_zone_h,
            )

        return canvas.convert("RGB")

    # ── Helpers ────────────────────────────────────────────────────────

    def _draw_logo(self, canvas: Image.Image, image_zone_h: int) -> None:
        if not os.path.exists(LOGO_PATH):
            return
        try:
            logo = Image.open(LOGO_PATH).convert("RGBA")
            logo.thumbnail((LOGO_MAX_W, LOGO_MAX_H), Image.LANCZOS)
            x = LOGO_MARGIN
            y = image_zone_h - LOGO_MARGIN - logo.height
            canvas.paste(logo, (x, y), mask=logo.split()[3])
        except Exception:
            pass  # logo is optional — never crash on a bad file
