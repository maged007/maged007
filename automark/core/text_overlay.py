"""
TextOverlayEngine: Renders a sale caption over the hero image.

Features:
  - Summarises captions longer than 60 words down to sale-relevant content
    (keeps sentences mentioning price, model, mileage, condition, etc.).
  - Draws a semi-transparent black frame (30% opacity) at the bottom of the
    hero image, with rounded corners matching the design system.
  - Renders the caption in white on top of that frame.
  - Full Arabic support (reshaping + bidi) when the optional libs are present,
    so RTL Egyptian car-sale captions display correctly.

Design intent: this overlay is built for "used-car-for-sale" Instagram stories.
"""

from __future__ import annotations

import os
import re

from PIL import Image, ImageDraw, ImageFont

from .layouts import CORNER_RADIUS

# Optional Arabic shaping — degrade gracefully if not installed.
try:
    import arabic_reshaper
    from bidi.algorithm import get_display
    _ARABIC_SUPPORT = True
except Exception:  # pragma: no cover
    _ARABIC_SUPPORT = False


# ── Configuration ──────────────────────────────────────────────────
MAX_WORDS = 60                 # captions longer than this get summarised
BASE_FONT_SIZE = 12            # the "font 12" requested by the user …
FONT_SCALE = 3.5               # … scaled up so it is readable on a 1080px canvas
RENDER_FONT_SIZE = int(BASE_FONT_SIZE * FONT_SCALE)   # → 42 px

BOX_OPACITY = 77               # 30% of 255 (black frame transparency)
BOX_RADIUS = CORNER_RADIUS     # 24 px, matches image corners
BOX_MARGIN = 24                # gap between the frame and the hero image edges
TEXT_PADDING = 28              # inner padding inside the frame
LINE_SPACING = 1.30            # line-height multiplier
TEXT_COLOR = (255, 255, 255, 255)
MAX_BOX_HEIGHT_RATIO = 0.55    # frame never taller than 55% of the hero slot

FONTS_DIR = os.path.join(os.path.dirname(__file__), "..", "static", "fonts")

# Sentences containing these tokens are considered "sale-relevant" and kept first.
SALE_KEYWORDS = {
    # Arabic
    "سعر", "جنيه", "الف", "ألف", "موديل", "كيلو", "كيلومتر", "عداد", "فابريكا",
    "رخصة", "ملكية", "حالة", "ممتازة", "ممتاز", "اوتوماتيك", "أوتوماتيك", "مانوال",
    "فتحة", "جلد", "بصمة", "شاشة", "كاميرا", "سنتر", "اقساط", "أقساط", "كاش",
    "تقبل", "البدل", "نقل", "صيانة", "توكيل", "زيرو", "نضيفة", "نظيفة", "بانوراما",
    # English
    "price", "model", "year", "km", "mileage", "automatic", "manual", "leather",
    "sunroof", "warranty", "cash", "installment", "condition", "excellent",
    "owner", "service", "original", "clean", "low",
}


class TextOverlayEngine:

    def __init__(self) -> None:
        # Two fonts: Arabic-capable for RTL text, Latin for English captions.
        # (NotoSansArabic lacks Latin glyphs, DejaVu lacks Arabic — so we pick
        #  the right one per line based on the script it contains.)
        self._font_ar = self._load_font(RENDER_FONT_SIZE, arabic=True)
        self._font_latin = self._load_font(RENDER_FONT_SIZE, arabic=False)

    # ────────────────────────────────────────────────────────────── #
    # Public API
    # ────────────────────────────────────────────────────────────── #

    def summarize(self, text: str, max_words: int = MAX_WORDS) -> str:
        """
        Trim a caption to <= max_words, prioritising sale-relevant sentences.
        Returns the (possibly shortened) caption.
        """
        text = (text or "").strip()
        if not text:
            return ""

        words = text.split()
        if len(words) <= max_words:
            return text

        # Split into sentences (Arabic + Latin punctuation).
        sentences = [s.strip() for s in re.split(r"(?<=[.!?؟।\n])\s+|،", text) if s.strip()]
        if not sentences:
            return self._hard_truncate(words, max_words)

        # Score each sentence by sale-keyword hits; keep original index for ordering.
        scored = []
        for idx, sent in enumerate(sentences):
            score = self._sale_score(sent)
            scored.append((score, idx, sent))

        # Pick the most sale-relevant sentences first, then restore reading order.
        scored.sort(key=lambda t: (-t[0], t[1]))

        selected: list[tuple[int, str]] = []
        word_budget = 0
        for score, idx, sent in scored:
            n = len(sent.split())
            if word_budget + n > max_words and selected:
                break
            selected.append((idx, sent))
            word_budget += n
            if word_budget >= max_words:
                break

        selected.sort(key=lambda t: t[0])  # restore original order
        result = " ".join(s for _, s in selected).strip()

        # Safety net: still hard-truncate if a single huge sentence overflowed.
        if len(result.split()) > max_words:
            result = self._hard_truncate(result.split(), max_words)

        if not result.endswith(("…", ".", "!")):
            result += " …"
        return result

    def render(self, canvas: Image.Image, text: str, hero_slot: dict) -> Image.Image:
        """
        Draw the caption frame + text over the hero slot of an RGBA canvas.
        Returns the same canvas (modified in place via alpha composite).
        """
        text = (text or "").strip()
        if not text:
            return canvas

        caption = self.summarize(text)

        # Lay out wrapped lines within the available width.
        max_text_width = hero_slot["w"] - 2 * BOX_MARGIN - 2 * TEXT_PADDING
        lines = self._wrap(caption, max_text_width)

        line_height = int(RENDER_FONT_SIZE * LINE_SPACING)
        max_lines = max(
            1,
            int((hero_slot["h"] * MAX_BOX_HEIGHT_RATIO - 2 * TEXT_PADDING) // line_height),
        )
        if len(lines) > max_lines:
            lines = lines[:max_lines]
            lines[-1] = self._ellipsize_line(lines[-1], max_text_width)

        # Frame geometry — anchored to the bottom of the hero image.
        text_block_h = len(lines) * line_height
        box_h = text_block_h + 2 * TEXT_PADDING
        box_w = hero_slot["w"] - 2 * BOX_MARGIN
        box_x = hero_slot["x"] + BOX_MARGIN
        box_y = hero_slot["y"] + hero_slot["h"] - BOX_MARGIN - box_h

        overlay = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)

        # Semi-transparent black frame (30% opacity).
        draw.rounded_rectangle(
            [(box_x, box_y), (box_x + box_w, box_y + box_h)],
            radius=BOX_RADIUS,
            fill=(0, 0, 0, BOX_OPACITY),
        )

        # Render each line; right-align for RTL (Arabic), left-align otherwise.
        is_rtl = self._contains_arabic(caption)
        ty = box_y + TEXT_PADDING
        for line in lines:
            font = self._font_for(line)
            display = self._prepare_display(line)
            line_w = draw.textlength(display, font=font)
            if is_rtl:
                tx = box_x + box_w - TEXT_PADDING - line_w
            else:
                tx = box_x + TEXT_PADDING
            # Soft shadow under text for extra legibility.
            draw.text((tx + 2, ty + 2), display, font=font, fill=(0, 0, 0, 160))
            draw.text((tx, ty), display, font=font, fill=TEXT_COLOR)
            ty += line_height

        return Image.alpha_composite(canvas, overlay)

    # ────────────────────────────────────────────────────────────── #
    # Private helpers
    # ────────────────────────────────────────────────────────────── #

    def _load_font(self, size: int, arabic: bool) -> ImageFont.FreeTypeFont:
        """Load a font for the requested script, with sensible fallbacks."""
        if arabic:
            candidates = [
                os.path.join(FONTS_DIR, "NotoSansArabic-Bold.ttf"),
                os.path.join(FONTS_DIR, "NotoSansArabic-Regular.ttf"),
                "/Library/Fonts/Arial Unicode.ttf",            # macOS
                "/System/Library/Fonts/Supplemental/Arial.ttf",
            ]
        else:
            candidates = [
                os.path.join(FONTS_DIR, "DejaVuSans-Bold.ttf"),
                "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
                "/System/Library/Fonts/Supplemental/Arial Bold.ttf",  # macOS
                "/System/Library/Fonts/Helvetica.ttc",                # macOS
            ]
        for path in candidates:
            if os.path.exists(path):
                try:
                    return ImageFont.truetype(path, size)
                except Exception:
                    continue
        # Last resort: Pillow's scalable default.
        return ImageFont.load_default(size=size)

    def _font_for(self, text: str) -> ImageFont.FreeTypeFont:
        """Pick the Arabic font if the text contains Arabic, else Latin."""
        return self._font_ar if self._contains_arabic(text) else self._font_latin

    def _sale_score(self, sentence: str) -> int:
        low = sentence.lower()
        score = sum(1 for kw in SALE_KEYWORDS if kw in low or kw in sentence)
        # Numbers (prices, mileage, year) are strong sale signals.
        score += len(re.findall(r"\d{3,}", sentence))
        return score

    def _hard_truncate(self, words: list[str], max_words: int) -> str:
        return " ".join(words[:max_words]).strip() + " …"

    def _contains_arabic(self, text: str) -> bool:
        return any("؀" <= ch <= "ۿ" for ch in text)

    def _prepare_display(self, text: str) -> str:
        """Reshape + bidi-reorder Arabic so it renders connected and RTL."""
        if _ARABIC_SUPPORT and self._contains_arabic(text):
            return get_display(arabic_reshaper.reshape(text))
        return text

    def _wrap(self, text: str, max_width: int) -> list[str]:
        """Word-wrap (logical order) so each line fits within max_width px."""
        measure = ImageDraw.Draw(Image.new("RGBA", (10, 10)))
        words = text.split()
        lines: list[str] = []
        current = ""
        for word in words:
            candidate = f"{current} {word}".strip()
            display = self._prepare_display(candidate)
            if measure.textlength(display, font=self._font_for(candidate)) <= max_width or not current:
                current = candidate
            else:
                lines.append(current)
                current = word
        if current:
            lines.append(current)
        return lines

    def _ellipsize_line(self, line: str, max_width: int) -> str:
        measure = ImageDraw.Draw(Image.new("RGBA", (10, 10)))
        words = line.split()
        while words:
            candidate = " ".join(words) + " …"
            if measure.textlength(self._prepare_display(candidate), font=self._font_for(candidate)) <= max_width:
                return candidate
            words.pop()
        return "…"
