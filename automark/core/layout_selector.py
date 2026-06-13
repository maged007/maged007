"""
LayoutSelector: Picks the optimal layout variant for the given images.

For each candidate layout, it computes a fitness score by matching
hero-image orientation against slot-1 aspect ratio and accumulating
slot–image orientation compatibility.
"""

from __future__ import annotations

from .layouts import LAYOUTS, LAYOUTS_BY_COUNT, get_slot_area
from .image_scoring_engine import ScoredImage


class LayoutSelector:

    def select(self, scored_images: list[ScoredImage]) -> dict:
        """Return the best-fit layout dict from LAYOUTS."""
        n = len(scored_images)
        if n < 1 or n > 6:
            raise ValueError(f"Image count must be 1–6, got {n}")

        candidates = LAYOUTS_BY_COUNT[n]
        if len(candidates) == 1:
            return LAYOUTS[candidates[0]]

        hero = scored_images[0]  # highest-scoring image
        best_id = candidates[0]
        best_fitness = -1.0

        for layout_id in candidates:
            layout = LAYOUTS[layout_id]
            fitness = self._fitness(layout, hero, scored_images)
            if fitness > best_fitness:
                best_fitness = fitness
                best_id = layout_id

        return LAYOUTS[best_id]

    # ------------------------------------------------------------------ #

    def _fitness(
        self,
        layout: dict,
        hero: ScoredImage,
        all_images: list[ScoredImage],
    ) -> float:
        slots = layout["slots"]
        hero_slot = slots[0]
        score = 0.0

        # Hero slot aspect ratio vs hero image aspect ratio
        slot_aspect = hero_slot["w"] / hero_slot["h"]
        img_aspect = hero.analysis.aspect_ratio

        # Closer aspect → less cropping needed → higher fitness
        ratio_diff = abs(slot_aspect - img_aspect)
        score += max(0.0, 5.0 - ratio_diff * 4)

        # Prefer landscape hero in wide slots, portrait hero in tall slots
        if hero.analysis.orientation == "landscape" and slot_aspect > 1.0:
            score += 3.0
        elif hero.analysis.orientation == "portrait" and slot_aspect < 1.0:
            score += 3.0

        # Check remaining slots vs remaining images (orientation match)
        for i, slot in enumerate(slots[1:], start=1):
            if i < len(all_images):
                img = all_images[i]
                s_asp = slot["w"] / slot["h"]
                i_asp = img.analysis.aspect_ratio
                diff = abs(s_asp - i_asp)
                score += max(0.0, 2.0 - diff * 2)

        # Slight preference for layouts where total slot area wastes little
        total_slot_area = sum(get_slot_area(s) for s in slots)
        canvas_area = 1080 * 1620
        coverage = total_slot_area / canvas_area
        score += coverage * 2.0

        return score
