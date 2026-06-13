"""
Renderer: Composites scored images onto the 1080×1620 canvas.

Steps per slot:
  1. SmartCrop image to exact slot dimensions.
  2. Apply rounded-corner mask (24 px radius).
  3. Render drop-shadow beneath the slot.
  4. Paste result onto the white canvas.
"""

from __future__ import annotations

import io

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from .layouts import CANVAS_WIDTH, CANVAS_HEIGHT, CORNER_RADIUS, SHADOW_BLUR, SHADOW_OFFSET_Y, SHADOW_OPACITY
from .smart_crop_engine import SmartCropEngine


class Renderer:

    def __init__(self) -> None:
        self._cropper = SmartCropEngine()

    def render(
        self,
        layout: dict,
        scored_images: list,   # list[ScoredImage], ordered hero-first
        output_path: str | None = None,
    ) -> Image.Image:
        canvas = Image.new("RGBA", (CANVAS_WIDTH, CANVAS_HEIGHT), (255, 255, 255, 255))
        shadow_layer = Image.new("RGBA", (CANVAS_WIDTH, CANVAS_HEIGHT), (0, 0, 0, 0))

        slots = layout["slots"]

        for i, slot in enumerate(slots):
            if i >= len(scored_images):
                break

            img_analysis = scored_images[i].analysis
            pil_img = Image.open(img_analysis.path).convert("RGB")

            # Smart-crop to slot dimensions
            cropped = self._cropper.crop(pil_img, slot["w"], slot["h"])

            # Build rounded-corner mask
            mask = self._rounded_rect_mask(slot["w"], slot["h"], CORNER_RADIUS)

            # Render shadow onto shadow_layer
            self._draw_shadow(shadow_layer, slot, mask)

            # Apply mask to image
            cropped_rgba = cropped.convert("RGBA")
            cropped_rgba.putalpha(mask)

            # Paste shadow first, then image
            canvas = Image.alpha_composite(canvas, shadow_layer)
            # Reset shadow layer after each composite to avoid accumulation
            shadow_layer = Image.new("RGBA", (CANVAS_WIDTH, CANVAS_HEIGHT), (0, 0, 0, 0))

            canvas.paste(cropped_rgba, (slot["x"], slot["y"]), mask=mask)

        return canvas.convert("RGB")

    # ------------------------------------------------------------------ #

    def _rounded_rect_mask(self, w: int, h: int, radius: int) -> Image.Image:
        """White rounded-rectangle alpha mask."""
        mask = Image.new("L", (w, h), 0)
        draw = ImageDraw.Draw(mask)
        draw.rounded_rectangle([(0, 0), (w - 1, h - 1)], radius=radius, fill=255)
        return mask

    def _draw_shadow(
        self, shadow_layer: Image.Image, slot: dict, mask: Image.Image
    ) -> None:
        """Paints a soft drop-shadow for the slot onto shadow_layer."""
        # Create shadow shape slightly offset
        shadow_img = Image.new("RGBA", (CANVAS_WIDTH, CANVAS_HEIGHT), (0, 0, 0, 0))
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
