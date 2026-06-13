"""
ExportEngine: Saves the final canvas as a high-quality PNG.
Also provides a helper for returning the image as bytes (for HTTP response).
"""

from __future__ import annotations

import io
import os
from datetime import datetime

from PIL import Image


class ExportEngine:

    def save(self, image: Image.Image, output_dir: str, filename: str | None = None) -> str:
        """Save to disk and return absolute file path."""
        os.makedirs(output_dir, exist_ok=True)

        if filename is None:
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"automark_story_{ts}.png"

        if not filename.lower().endswith(".png"):
            filename += ".png"

        path = os.path.join(output_dir, filename)
        img = image.convert("RGB")
        img.save(path, format="PNG", optimize=False, compress_level=1)
        return path

    def to_bytes(self, image: Image.Image) -> bytes:
        """Return PNG-encoded bytes (for streaming HTTP responses)."""
        buf = io.BytesIO()
        image.convert("RGB").save(buf, format="PNG", optimize=False, compress_level=1)
        buf.seek(0)
        return buf.read()

    def to_jpeg_preview(self, image: Image.Image, quality: int = 85) -> bytes:
        """Return a JPEG-encoded preview (smaller, for web preview)."""
        buf = io.BytesIO()
        img = image.convert("RGB")
        # Scale down for preview: max 540 wide
        max_w = 540
        if img.width > max_w:
            scale = max_w / img.width
            img = img.resize(
                (max_w, int(img.height * scale)), Image.LANCZOS
            )
        img.save(buf, format="JPEG", quality=quality, optimize=True)
        buf.seek(0)
        return buf.read()
