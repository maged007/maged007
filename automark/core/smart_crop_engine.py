"""
SmartCropEngine: Crops an image to a target (w, h) without distortion.

Algorithm:
  1. Build a gradient-magnitude saliency map.
  2. Find the bounding box of the highest-energy region (top 15% of pixels).
  3. Compute a crop window of the target aspect ratio centred on that region,
     with a gravity bias (vehicles tend to sit in the lower-centre).
  4. Clamp to image bounds and scale up/down with high-quality resampling.
"""

from __future__ import annotations

import cv2
import numpy as np
from PIL import Image


class SmartCropEngine:

    # Weight given to gradient saliency vs centre-gravity anchor
    _SALIENCY_WEIGHT = 0.65
    _CENTER_WEIGHT = 0.35

    def crop(self, pil_img: Image.Image, target_w: int, target_h: int) -> Image.Image:
        src_w, src_h = pil_img.size
        target_aspect = target_w / target_h
        src_aspect = src_w / src_h

        if abs(src_aspect - target_aspect) < 0.02:
            # Already correct aspect ratio — just resize
            return pil_img.resize((target_w, target_h), Image.LANCZOS)

        # Determine crop window size maintaining target aspect
        if src_aspect > target_aspect:
            # Wider than target: crop sides
            crop_h = src_h
            crop_w = int(round(crop_h * target_aspect))
        else:
            # Taller than target: crop top/bottom
            crop_w = src_w
            crop_h = int(round(crop_w / target_aspect))

        # Find focus point
        cx, cy = self._find_focus(pil_img, src_w, src_h)

        # Compute crop box (x1, y1, x2, y2)
        x1 = int(cx - crop_w / 2)
        y1 = int(cy - crop_h / 2)
        x1 = max(0, min(x1, src_w - crop_w))
        y1 = max(0, min(y1, src_h - crop_h))
        x2 = x1 + crop_w
        y2 = y1 + crop_h

        cropped = pil_img.crop((x1, y1, x2, y2))
        return cropped.resize((target_w, target_h), Image.LANCZOS)

    # ------------------------------------------------------------------ #

    def _find_focus(self, pil_img: Image.Image, src_w: int, src_h: int) -> tuple[float, float]:
        bgr = cv2.cvtColor(np.array(pil_img.convert("RGB")), cv2.COLOR_RGB2BGR)

        sal = self._saliency_map(bgr)
        sal_cx, sal_cy = self._saliency_centroid(sal, src_w, src_h)

        # Centre-gravity anchor: slightly below geometric centre for vehicles
        ctr_cx = src_w * 0.5
        ctr_cy = src_h * 0.55  # vehicles sit low in frame

        cx = sal_cx * self._SALIENCY_WEIGHT + ctr_cx * self._CENTER_WEIGHT
        cy = sal_cy * self._SALIENCY_WEIGHT + ctr_cy * self._CENTER_WEIGHT

        return cx, cy

    def _saliency_map(self, bgr: np.ndarray) -> np.ndarray:
        """
        Combined saliency: gradient magnitude + colour saturation,
        weighted by a spatial Gaussian prior that favours the centre-lower
        area where vehicles typically appear.  Sky rows are suppressed for
        landscape images to prevent the horizon from pulling focus.
        """
        h, w = bgr.shape[:2]
        gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)

        # Gradient magnitude
        gx = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3)
        gy = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=3)
        grad = np.sqrt(gx ** 2 + gy ** 2)

        # Saturation (vivid colour = vehicle body rather than neutral bg)
        hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
        sat = hsv[:, :, 1].astype(np.float64)

        sal = grad * 0.70 + sat * 0.30
        sal = cv2.normalize(sal, None, 0, 255, cv2.NORM_MINMAX, cv2.CV_8U)
        sal = cv2.GaussianBlur(sal, (51, 51), 0)

        # Suppress sky band in landscape images (top 22%)
        if w > h * 1.15:
            sky_rows = int(h * 0.22)
            sal[:sky_rows, :] = 0

        # Spatial Gaussian prior — peak at (cx=50%, cy=58%)
        yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
        cx_p, cy_p = w * 0.50, h * 0.58
        sx, sy = w * 0.55, h * 0.55
        prior = np.exp(-((xx - cx_p) ** 2 / (2 * sx ** 2) + (yy - cy_p) ** 2 / (2 * sy ** 2)))
        prior = (prior * 255).astype(np.uint8)

        sal = cv2.multiply(sal, prior, scale=1.0 / 255.0)
        sal = cv2.normalize(sal, None, 0, 255, cv2.NORM_MINMAX, cv2.CV_8U)
        return sal

    def _saliency_centroid(
        self, sal: np.ndarray, src_w: int, src_h: int
    ) -> tuple[float, float]:
        """Weighted centroid of the top-15% saliency pixels."""
        threshold = np.percentile(sal, 85)
        mask = sal >= threshold
        ys, xs = np.where(mask)
        if len(xs) == 0:
            return src_w / 2.0, src_h / 2.0
        weights = sal[ys, xs].astype(float)
        cx = float(np.average(xs, weights=weights))
        cy = float(np.average(ys, weights=weights))
        return cx, cy
