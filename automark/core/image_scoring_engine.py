"""
ImageScoringEngine: Assigns a numeric score to each image.
Score = base type score  +  quality bonuses/penalties.
"""

from __future__ import annotations

from dataclasses import dataclass

from .vehicle_analyzer import ImageAnalysis, IMAGE_TYPES


@dataclass
class ScoredImage:
    analysis: ImageAnalysis
    base_score: int
    quality_bonus: float
    final_score: float
    rank: int = 0  # set after sorting


class ImageScoringEngine:

    # Quality bonus weights
    _BRIGHTNESS_IDEAL = 0.55   # target mid-tone
    _BRIGHTNESS_WEIGHT = 15.0
    _CONTRAST_WEIGHT = 10.0
    _SATURATION_WEIGHT = 8.0

    def score(self, analyses: list[ImageAnalysis]) -> list[ScoredImage]:
        scored = [self._score_one(a) for a in analyses]
        scored.sort(key=lambda s: s.final_score, reverse=True)
        for rank, s in enumerate(scored):
            s.rank = rank
        return scored

    def _score_one(self, analysis: ImageAnalysis) -> ScoredImage:
        _, base_score = IMAGE_TYPES.get(analysis.image_type, ("Unknown", 50))

        quality_bonus = self._quality_bonus(analysis)
        final = float(base_score) + quality_bonus

        return ScoredImage(
            analysis=analysis,
            base_score=base_score,
            quality_bonus=quality_bonus,
            final_score=final,
        )

    def _quality_bonus(self, a: ImageAnalysis) -> float:
        bonus = 0.0

        # Brightness closeness to ideal
        brightness_delta = abs(a.brightness - self._BRIGHTNESS_IDEAL)
        bonus += (1.0 - brightness_delta * 2) * self._BRIGHTNESS_WEIGHT

        # Contrast reward (sharp images score higher)
        bonus += min(a.contrast, 1.0) * self._CONTRAST_WEIGHT

        # Saturation reward (vivid colours score higher)
        bonus += min(a.saturation, 1.0) * self._SATURATION_WEIGHT

        # Resolution bonus (higher-res images are preferred)
        megapixels = (a.width * a.height) / 1_000_000
        bonus += min(megapixels, 12) * 0.5  # up to +6 for 12 MP

        # Penalty for very dark images
        if a.dark_ratio > 0.4:
            bonus -= 10.0

        return round(bonus, 2)
