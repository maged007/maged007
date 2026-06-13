"""
TextOverlayEngine: Renders the sale caption inside the dedicated black text zone.

Design:
  • Text is white, bold, horizontally AND vertically centred in the zone.
  • Arabic reshaping + bidi applied automatically (RTL text right-aligned).
  • If the wrapped text block is taller than the available height, lines are
    dropped from the bottom and the last kept line gets a trailing "…".
  • Summarisation: captions longer than MAX_WORDS are shortened first,
    keeping sale-relevant sentences (price / model / km / condition …).
"""

from __future__ import annotations

import os
import re

from PIL import Image, ImageDraw, ImageFont

from .layouts import CORNER_RADIUS

try:
    import arabic_reshaper
    from bidi.algorithm import get_display
    _ARABIC_SUPPORT = True
except Exception:
    _ARABIC_SUPPORT = False


# ── Config ──────────────────────────────────────────────────────
MAX_WORDS       = 60
BASE_FONT_SIZE  = 12
FONT_SCALE      = 3.5
RENDER_FONT_SIZE = int(BASE_FONT_SIZE * FONT_SCALE)   # 42 px
LINE_SPACING    = 1.35
TEXT_COLOR      = (255, 255, 255, 255)
TEXT_PAD_X      = 60    # horizontal padding inside the zone
TEXT_PAD_Y      = 40    # vertical padding inside the zone

FONTS_DIR = os.path.join(os.path.dirname(__file__), "..", "static", "fonts")

SALE_KEYWORDS = {
    "سعر","جنيه","الف","ألف","موديل","كيلو","كيلومتر","عداد","فابريكا",
    "رخصة","ملكية","حالة","ممتازة","ممتاز","اوتوماتيك","أوتوماتيك","مانوال",
    "فتحة","جلد","بصمة","شاشة","كاميرا","سنتر","اقساط","أقساط","كاش",
    "تقبل","البدل","نقل","صيانة","توكيل","زيرو","نضيفة","نظيفة","بانوراما",
    "price","model","year","km","mileage","automatic","manual","leather",
    "sunroof","warranty","cash","installment","condition","excellent",
    "owner","service","original","clean","low",
}


class TextOverlayEngine:

    def __init__(self) -> None:
        self._font_ar    = self._load_font(RENDER_FONT_SIZE, arabic=True)
        self._font_latin = self._load_font(RENDER_FONT_SIZE, arabic=False)

    # ── Public ─────────────────────────────────────────────────

    def summarize(self, text: str, max_words: int = MAX_WORDS) -> str:
        text = (text or "").strip()
        if not text:
            return ""
        words = text.split()
        if len(words) <= max_words:
            return text

        sentences = [s.strip() for s in re.split(r"(?<=[.!?؟।\n])\s+|،|,", text) if s.strip()]
        if not sentences:
            return self._hard_truncate(words, max_words)

        scored = sorted(
            [(self._sale_score(s), i, s) for i, s in enumerate(sentences)],
            key=lambda t: (-t[0], t[1]),
        )
        selected: list[tuple[int, str]] = []
        budget = 0
        for score, idx, sent in scored:
            n = len(sent.split())
            if budget + n > max_words and selected:
                break
            selected.append((idx, sent))
            budget += n
            if budget >= max_words:
                break

        selected.sort(key=lambda t: t[0])
        result = " ".join(s for _, s in selected).strip()
        if len(result.split()) > max_words:
            result = self._hard_truncate(result.split(), max_words)
        if not result.endswith(("…", ".", "!")):
            result += " …"
        return result

    def render_in_zone(
        self,
        canvas: Image.Image,
        caption: str,
        zone_x: int,
        zone_y: int,
        zone_w: int,
        zone_h: int,
    ) -> None:
        """
        Draw centred white text inside the given zone rectangle on the canvas.
        Mutates canvas in-place (the zone background must already be drawn).
        """
        caption = self.summarize(caption)
        if not caption.strip():
            return

        is_rtl = self._contains_arabic(caption)
        font    = self._font_for(caption)
        max_w   = zone_w - 2 * TEXT_PAD_X
        max_h   = zone_h - 2 * TEXT_PAD_Y
        lh      = int(RENDER_FONT_SIZE * LINE_SPACING)

        lines = self._wrap(caption, max_w)

        # Trim lines that don't fit, ellipsise last kept line
        max_lines = max(1, max_h // lh)
        if len(lines) > max_lines:
            lines = lines[:max_lines]
            lines[-1] = self._ellipsise(lines[-1], max_w, font)

        total_h = len(lines) * lh
        # Vertical centre
        ty = zone_y + (zone_h - total_h) // 2

        overlay = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
        draw    = ImageDraw.Draw(overlay)

        for line in lines:
            display = self._prepare_display(line)
            font_l  = self._font_for(line)
            line_w  = draw.textlength(display, font=font_l)

            # Horizontal centre (RTL lines are also centred, not right-flushed)
            tx = zone_x + (zone_w - line_w) // 2

            # Soft shadow
            draw.text((tx + 2, ty + 2), display, font=font_l, fill=(0, 0, 0, 180))
            draw.text((tx, ty),         display, font=font_l, fill=TEXT_COLOR)
            ty += lh

        canvas.paste(overlay, (0, 0), mask=overlay.split()[3])

    # ── Private ────────────────────────────────────────────────

    def _load_font(self, size: int, arabic: bool) -> ImageFont.FreeTypeFont:
        if arabic:
            candidates = [
                os.path.join(FONTS_DIR, "NotoSansArabic-Bold.ttf"),
                os.path.join(FONTS_DIR, "NotoSansArabic-Regular.ttf"),
                "/Library/Fonts/Arial Unicode.ttf",
                "/System/Library/Fonts/Supplemental/Arial.ttf",
            ]
        else:
            candidates = [
                os.path.join(FONTS_DIR, "DejaVuSans-Bold.ttf"),
                "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
                "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
                "/System/Library/Fonts/Helvetica.ttc",
            ]
        for path in candidates:
            if os.path.exists(path):
                try:
                    return ImageFont.truetype(path, size)
                except Exception:
                    continue
        return ImageFont.load_default(size=size)

    def _font_for(self, text: str) -> ImageFont.FreeTypeFont:
        return self._font_ar if self._contains_arabic(text) else self._font_latin

    def _contains_arabic(self, text: str) -> bool:
        return any("؀" <= ch <= "ۿ" for ch in text)

    def _prepare_display(self, text: str) -> str:
        if _ARABIC_SUPPORT and self._contains_arabic(text):
            return get_display(arabic_reshaper.reshape(text))
        return text

    def _wrap(self, text: str, max_width: int) -> list[str]:
        measure = ImageDraw.Draw(Image.new("RGBA", (10, 10)))
        words   = text.split()
        lines: list[str] = []
        current = ""
        for word in words:
            candidate = f"{current} {word}".strip()
            display   = self._prepare_display(candidate)
            if measure.textlength(display, font=self._font_for(candidate)) <= max_width or not current:
                current = candidate
            else:
                lines.append(current)
                current = word
        if current:
            lines.append(current)
        return lines

    def _ellipsise(self, line: str, max_width: int, font: ImageFont.FreeTypeFont) -> str:
        measure = ImageDraw.Draw(Image.new("RGBA", (10, 10)))
        words = line.split()
        while words:
            candidate = " ".join(words) + " …"
            if measure.textlength(self._prepare_display(candidate), font=self._font_for(candidate)) <= max_width:
                return candidate
            words.pop()
        return "…"

    def _sale_score(self, sentence: str) -> int:
        low   = sentence.lower()
        score = sum(1 for kw in SALE_KEYWORDS if kw in low or kw in sentence)
        score += len(re.findall(r"\d{3,}", sentence))
        return score

    def _hard_truncate(self, words: list[str], max_words: int) -> str:
        return " ".join(words[:max_words]) + " …"
