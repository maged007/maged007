"""
VehicleAnalyzer: Extracts structural metadata from vehicle images.
Uses OpenCV for gradient-based analysis, color stats, and orientation detection.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

import cv2
import numpy as np
from PIL import Image, ExifTags


@dataclass
class ImageAnalysis:
    path: str
    width: int
    height: int
    aspect_ratio: float
    orientation: str          # "landscape" | "portrait" | "square"
    brightness: float         # 0.0–1.0
    contrast: float           # 0.0–1.0
    edge_density: float       # 0.0–1.0 (normalized Canny edge coverage)
    has_faces: bool
    saturation: float         # 0.0–1.0
    sky_ratio: float          # fraction of top-third that is sky-blue
    dark_ratio: float         # fraction of pixels below brightness 30
    # User-supplied or auto-inferred type tag
    image_type: str           # see IMAGE_TYPES below


# Canonical type keys → display labels and base scores
IMAGE_TYPES: dict[str, tuple[str, int]] = {
    "front_34_exterior":  ("Front 3/4 Exterior", 100),
    "front_exterior":     ("Front Exterior",      95),
    "side_exterior":      ("Side Exterior",        90),
    "rear_exterior":      ("Rear Exterior",        85),
    "interior":           ("Interior",             70),
    "dashboard":          ("Dashboard",            65),
    "seats":              ("Seats",                60),
    "wheel":              ("Wheel",                50),
    "engine":             ("Engine",               45),
    "screen":             ("Screen",               40),
    "logo":               ("Logo",                 20),
    "auto":               ("Auto-detected",         0),  # will be resolved by scorer
}


class VehicleAnalyzer:
    def __init__(self) -> None:
        # Note: OpenCV's Haar cascade face detector is intentionally NOT used.
        # It is the most common source of native segfaults on macOS/Apple
        # Silicon and its result was not used by the type-inference heuristics.
        pass

    def analyze(self, image_path: str, user_type: str = "auto") -> ImageAnalysis:
        pil_img = self._open_corrected(image_path)
        w, h = pil_img.size

        bgr = cv2.cvtColor(np.array(pil_img.convert("RGB")), cv2.COLOR_RGB2BGR)

        aspect = w / h
        if aspect > 1.1:
            orientation = "landscape"
        elif aspect < 0.9:
            orientation = "portrait"
        else:
            orientation = "square"

        brightness = self._brightness(bgr)
        contrast = self._contrast(bgr)
        edge_density = self._edge_density(bgr)
        has_faces = False  # face detection disabled (see __init__)
        saturation = self._saturation(bgr)
        sky_ratio = self._sky_ratio(bgr)
        dark_ratio = self._dark_ratio(bgr)

        if user_type not in IMAGE_TYPES or user_type == "auto":
            inferred = self._infer_type(
                orientation, edge_density, saturation, sky_ratio, dark_ratio, has_faces
            )
        else:
            inferred = user_type

        return ImageAnalysis(
            path=image_path,
            width=w,
            height=h,
            aspect_ratio=aspect,
            orientation=orientation,
            brightness=brightness,
            contrast=contrast,
            edge_density=edge_density,
            has_faces=has_faces,
            saturation=saturation,
            sky_ratio=sky_ratio,
            dark_ratio=dark_ratio,
            image_type=inferred,
        )

    # ------------------------------------------------------------------ #
    # Private helpers
    # ------------------------------------------------------------------ #

    def _open_corrected(self, path: str) -> Image.Image:
        """Open image and apply EXIF orientation so dims are visual."""
        img = Image.open(path)
        try:
            exif = img._getexif()
            if exif:
                for tag, val in exif.items():
                    if ExifTags.TAGS.get(tag) == "Orientation":
                        ops = {
                            3: Image.ROTATE_180,
                            6: Image.ROTATE_270,
                            8: Image.ROTATE_90,
                        }
                        if val in ops:
                            img = img.transpose(ops[val])
        except Exception:
            pass
        return img.convert("RGB")

    def _brightness(self, bgr: np.ndarray) -> float:
        gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
        return float(gray.mean()) / 255.0

    def _contrast(self, bgr: np.ndarray) -> float:
        gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
        return float(gray.std()) / 128.0

    def _edge_density(self, bgr: np.ndarray) -> float:
        gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
        edges = cv2.Canny(gray, 50, 150)
        return float(np.count_nonzero(edges)) / edges.size

    def _saturation(self, bgr: np.ndarray) -> float:
        hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
        return float(hsv[:, :, 1].mean()) / 255.0

    def _sky_ratio(self, bgr: np.ndarray) -> float:
        """Fraction of the top-third rows that look like sky (light blue)."""
        h = bgr.shape[0]
        top = bgr[: h // 3, :, :]
        hsv = cv2.cvtColor(top, cv2.COLOR_BGR2HSV)
        # Sky hue range in HSV
        mask = cv2.inRange(hsv, (90, 20, 100), (140, 180, 255))
        return float(np.count_nonzero(mask)) / mask.size

    def _dark_ratio(self, bgr: np.ndarray) -> float:
        gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
        return float(np.count_nonzero(gray < 30)) / gray.size

    def _infer_type(
        self,
        orientation: str,
        edge_density: float,
        saturation: float,
        sky_ratio: float,
        dark_ratio: float,
        has_faces: bool,
    ) -> str:
        """
        Heuristic type inference.
        Landscape + sky → exterior shot; high edge + landscape → likely 3/4 front.
        Portrait + dark + low saturation → interior/dashboard.
        """
        if orientation == "landscape":
            if sky_ratio > 0.08:
                # Outdoor exterior shot
                if edge_density > 0.12:
                    return "front_34_exterior"
                return "side_exterior"
            if edge_density > 0.15:
                return "front_exterior"
            if dark_ratio > 0.25:
                return "interior"
            return "side_exterior"
        else:
            # Portrait or square
            if dark_ratio > 0.30 and saturation < 0.25:
                return "dashboard"
            if edge_density < 0.06:
                return "seats"
            if saturation > 0.40:
                return "interior"
            return "interior"
