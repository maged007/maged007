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

from PIL import features as _pil_features

# When PIL is built with libraqm (HarfBuzz + FriBidi), it shapes Arabic
# correctly from raw Unicode using the font's own GSUB tables — this is the
# preferred path and lets us use Cairo for Arabic. Pillow's binary wheels
# bundle raqm on macOS/Windows/Linux, so this is the common case.
_RAQM = _pil_features.check("raqm")

# Fallback only used when raqm is unavailable: arabic_reshaper converts base
# letters into deprecated presentation forms, which require a font that ships
# them (NotoSansArabic) — Cairo does not.
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
        # Cairo handles both scripts (Arabic via raqm). The Noto font is only
        # used for Arabic when raqm is unavailable (presentation-form fallback).
        self._font_cairo = self._load_font(RENDER_FONT_SIZE, arabic=False)
        self._font_noto  = self._load_font(RENDER_FONT_SIZE, arabic=True)

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

    @property
    def line_height(self) -> int:
        return int(RENDER_FONT_SIZE * LINE_SPACING)

    def layout_lines(self, caption: str, zone_w: int, max_lines: int | None = None) -> list[str]:
        """
        Summarise + wrap the caption into display lines for the given zone width.
        If max_lines is set, surplus lines are dropped and the last is ellipsised.
        """
        caption = self.summarize(caption)
        if not caption.strip():
            return []
        max_w = zone_w - 2 * TEXT_PAD_X
        lines = self._wrap(caption, max_w)
        if max_lines is not None and len(lines) > max_lines:
            lines = lines[:max_lines]
            lines[-1] = self._ellipsise(lines[-1], max_w, self._font_for(lines[-1]))
        return lines

    def measure_zone_height(self, caption: str, zone_w: int) -> int:
        """
        Height (px) the text container needs to fit the caption snugly,
        including top/bottom padding. Returns 0 for empty captions.
        """
        lines = self.layout_lines(caption, zone_w)
        if not lines:
            return 0
        return len(lines) * self.line_height + 2 * TEXT_PAD_Y

    def draw_lines(
        self,
        canvas: Image.Image,
        lines: list[str],
        zone_x: int,
        zone_y: int,
        zone_w: int,
        zone_h: int,
    ) -> None:
        """Draw pre-wrapped lines, centred both axes, in white on the canvas."""
        if not lines:
            return
        lh = self.line_height
        total_h = len(lines) * lh
        ty = zone_y + (zone_h - total_h) // 2

        overlay = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)
        for line in lines:
            display = self._prepare_display(line)
            font_l = self._font_for(line)
            dk = self._dir_kwargs(line)
            line_w = draw.textlength(display, font=font_l, **dk)
            tx = zone_x + (zone_w - line_w) // 2     # horizontal centre
            draw.text((tx + 2, ty + 2), display, font=font_l, fill=(0, 0, 0, 180), **dk)
            draw.text((tx, ty), display, font=font_l, fill=TEXT_COLOR, **dk)
            ty += lh
        canvas.paste(overlay, (0, 0), mask=overlay.split()[3])

    # ── Private ────────────────────────────────────────────────

    def _load_font(self, size: int, arabic: bool) -> ImageFont.FreeTypeFont:
        # Cairo covers BOTH Arabic and Latin, so it is the primary choice for
        # either script. Fallbacks kept for environments without the bundled font.
        candidates = [
            os.path.join(FONTS_DIR, "Cairo-Bold.ttf"),
            os.path.join(FONTS_DIR, "Cairo-SemiBold.ttf"),
        ]
        if arabic:
            candidates += [
                os.path.join(FONTS_DIR, "NotoSansArabic-Bold.ttf"),
                "/Library/Fonts/Arial Unicode.ttf",
                "/System/Library/Fonts/Supplemental/Arial.ttf",
            ]
        else:
            candidates += [
                os.path.join(FONTS_DIR, "DejaVuSans-Bold.ttf"),
                "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
                "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
            ]
        for path in candidates:
            if os.path.exists(path):
                try:
                    return ImageFont.truetype(path, size)
                except Exception:
                    continue
        return ImageFont.load_default(size=size)

    def _font_for(self, text: str) -> ImageFont.FreeTypeFont:
        # Cairo for everything, except Arabic without raqm (needs Noto's
        # presentation-form glyphs produced by the reshaper fallback).
        if self._contains_arabic(text) and not _RAQM:
            return self._font_noto
        return self._font_cairo

    def _direction(self, text: str) -> str:
        return "rtl" if self._contains_arabic(text) else "ltr"

    def _dir_kwargs(self, text: str) -> dict:
        # `direction` is only valid when PIL has raqm; otherwise omit it.
        return {"direction": self._direction(text)} if _RAQM else {}

    def _contains_arabic(self, text: str) -> bool:
        return any("؀" <= ch <= "ۿ" for ch in text)

    def _prepare_display(self, text: str) -> str:
        # With raqm, HarfBuzz shapes raw Unicode correctly — leave it untouched.
        # Without raqm, fall back to the reshaper + bidi presentation forms.
        if not _RAQM and _ARABIC_SUPPORT and self._contains_arabic(text):
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
            w = measure.textlength(display, font=self._font_for(candidate), **self._dir_kwargs(candidate))
            if w <= max_width or not current:
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
            w = measure.textlength(self._prepare_display(candidate), font=self._font_for(candidate), **self._dir_kwargs(candidate))
            if w <= max_width:
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
