"""
QualityValidator: Validates that the rendered canvas meets AutoMark specs.
Returns a list of validation issues (empty list = passes).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from PIL import Image

from .layouts import CANVAS_WIDTH, CANVAS_HEIGHT


@dataclass
class ValidationResult:
    passed: bool
    issues: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


class QualityValidator:

    # Allowed dimension tolerance (±1 px rounding)
    _DIM_TOLERANCE = 2

    def validate(self, image: Image.Image) -> ValidationResult:
        issues: list[str] = []
        warnings: list[str] = []

        # Canvas dimensions
        w, h = image.size
        if abs(w - CANVAS_WIDTH) > self._DIM_TOLERANCE:
            issues.append(f"Width is {w}px, expected {CANVAS_WIDTH}px")
        if abs(h - CANVAS_HEIGHT) > self._DIM_TOLERANCE:
            issues.append(f"Height is {h}px, expected {CANVAS_HEIGHT}px")

        # Mode check
        if image.mode not in ("RGB", "RGBA"):
            issues.append(f"Unexpected mode {image.mode!r}, expected RGB/RGBA")

        # No fully black canvas (indicates render failure)
        import numpy as np
        arr = np.array(image.convert("RGB"))
        mean_brightness = arr.mean()
        if mean_brightness < 5:
            issues.append("Canvas is nearly black — render may have failed")

        # Check that white background percentage is reasonable
        white_mask = (arr[:, :, 0] > 250) & (arr[:, :, 1] > 250) & (arr[:, :, 2] > 250)
        white_ratio = white_mask.mean()
        if white_ratio > 0.95:
            warnings.append("Canvas is almost entirely white — images may not have rendered")
        # Note: the gapless mosaic intentionally leaves no white margins, so a
        # low white ratio is expected and is no longer flagged.

        return ValidationResult(passed=len(issues) == 0, issues=issues, warnings=warnings)
