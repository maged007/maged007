"""
Renderer: Composites scored images onto the 1080×1620 canvas.

Canvas split:
  • Top 2/3  (1080 px tall) — image collage, layout slots scaled to fit
  • Bottom 1/3 (540 px tall) — solid black text zone with centred caption
  • AutoMark logo — bottom-left corner of the image zone
"""

from __future__ import annotations

import os

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from .layouts import (
    CANVAS_WIDTH, CANVAS_HEIGHT,
    CORNER_RADIUS, SHADOW_BLUR, SHADOW_OFFSET_Y, SHADOW_OPACITY,
)
from .smart_crop_engine import SmartCropEngine
from .text_overlay import TextOverlayEngine

# ── Zone geometry ──────────────────────────────────────────────
IMAGE_ZONE_H = int(CANVAS_HEIGHT * 2 / 3)   # 1080 px  (top 2/3)
TEXT_ZONE_Y  = IMAGE_ZONE_H                  # 1080
TEXT_ZONE_H  = CANVAS_HEIGHT - IMAGE_ZONE_H  # 540 px   (bottom 1/3)

# Y-scale: compress all slot coords so they fill the image zone
_Y_SCALE = IMAGE_ZONE_H / CANVAS_HEIGHT      # ≈ 0.6667

# Logo placement (bottom-left of image zone)
LOGO_MAX_W   = 150
LOGO_MAX_H   = 100
LOGO_MARGIN  = 18
LOGO_PATH    = os.path.join(
    os.path.dirname(__file__), "..", "static", "logo.png"
)


def _scale_slot(slot: dict) -> dict:
    """Compress a slot's Y coords so it fits in the top IMAGE_ZONE_H pixels."""
    return {
        "slot": slot["slot"],
        "x":    slot["x"],
        "y":    max(0, int(round(slot["y"] * _Y_SCALE))),
        "w":    slot["w"],
        "h":    max(1, int(round(slot["h"] * _Y_SCALE))),
    }


class Renderer:

    def __init__(self) -> None:
        self._cropper = SmartCropEngine()
        self._text    = TextOverlayEngine()

    def render(
        self,
        layout: dict,
        scored_images: list,
        output_path: str | None = None,
        caption: str | None = None,
    ) -> Image.Image:

        canvas       = Image.new("RGBA", (CANVAS_WIDTH, CANVAS_HEIGHT), (255, 255, 255, 255))
        shadow_layer = Image.new("RGBA", (CANVAS_WIDTH, CANVAS_HEIGHT), (0, 0, 0, 0))

        # ── 1. Render images in scaled slots (top 2/3) ──────────
        scaled_slots = [_scale_slot(s) for s in layout["slots"]]

        for i, slot in enumerate(scaled_slots):
            if i >= len(scored_images):
                break

            pil_img = Image.open(scored_images[i].analysis.path).convert("RGB")
            cropped  = self._cropper.crop(pil_img, slot["w"], slot["h"])
            mask     = self._rounded_rect_mask(slot["w"], slot["h"], CORNER_RADIUS)

            self._draw_shadow(shadow_layer, slot, mask)
            cropped_rgba = cropped.convert("RGBA")
            cropped_rgba.putalpha(mask)

            canvas = Image.alpha_composite(canvas, shadow_layer)
            shadow_layer = Image.new("RGBA", (CANVAS_WIDTH, CANVAS_HEIGHT), (0, 0, 0, 0))
            canvas.paste(cropped_rgba, (slot["x"], slot["y"]), mask=mask)

        # ── 2. Logo — bottom-left of image zone ─────────────────
        self._draw_logo(canvas)

        # ── 3. Black text zone (bottom 1/3) ─────────────────────
        self._draw_text_zone(canvas, caption or "")

        return canvas.convert("RGB")

    # ── Private helpers ─────────────────────────────────────────

    def _rounded_rect_mask(self, w: int, h: int, radius: int) -> Image.Image:
        mask = Image.new("L", (w, h), 0)
        draw = ImageDraw.Draw(mask)
        draw.rounded_rectangle([(0, 0), (w - 1, h - 1)], radius=radius, fill=255)
        return mask

    def _draw_shadow(self, shadow_layer: Image.Image, slot: dict, mask: Image.Image) -> None:
        shadow_img  = Image.new("RGBA", (CANVAS_WIDTH, CANVAS_HEIGHT), (0, 0, 0, 0))
        shadow_mask = Image.new("L", (slot["w"], slot["h"]), 0)
        draw = ImageDraw.Draw(shadow_mask)
        draw.rounded_rectangle(
            [(0, 0), (slot["w"] - 1, slot["h"] - 1)],
            radius=CORNER_RADIUS,
            fill=SHADOW_OPACITY,
        )
        shadow_img.paste(
            Image.new("RGBA", (slot["w"], slot["h"]), (0, 0, 0, SHADOW_OPACITY)),
            (slot["x"], slot["y"] + SHADOW_OFFSET_Y),
            mask=shadow_mask,
        )
        blurred = shadow_img.filter(ImageFilter.GaussianBlur(radius=SHADOW_BLUR))
        shadow_layer.paste(blurred, (0, 0), mask=blurred.split()[3])

    def _draw_logo(self, canvas: Image.Image) -> None:
        """Paste the AutoMark logo into the bottom-left of the image zone."""
        if not os.path.exists(LOGO_PATH):
            return
        try:
            logo = Image.open(LOGO_PATH).convert("RGBA")
            logo.thumbnail((LOGO_MAX_W, LOGO_MAX_H), Image.LANCZOS)
            x = LOGO_MARGIN
            y = IMAGE_ZONE_H - LOGO_MARGIN - logo.height
            canvas.paste(logo, (x, y), mask=logo.split()[3])
        except Exception:
            pass  # logo is optional — never crash if file is bad

    def _draw_text_zone(self, canvas: Image.Image, caption: str) -> None:
        """Fill the bottom 1/3 with a black box and centred white caption."""
        draw = ImageDraw.Draw(canvas)

        # Solid black background
        draw.rectangle(
            [(0, TEXT_ZONE_Y), (CANVAS_WIDTH - 1, CANVAS_HEIGHT - 1)],
            fill=(0, 0, 0, 255),
        )

        if not caption.strip():
            return

        self._text.render_in_zone(
            canvas,
            caption,
            zone_x=0,
            zone_y=TEXT_ZONE_Y,
            zone_w=CANVAS_WIDTH,
            zone_h=TEXT_ZONE_H,
        )
