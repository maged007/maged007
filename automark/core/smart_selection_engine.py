"""
SmartSelectionEngine: Picks the best complementary subset of images for the grid.

Given a pool of any size (up to 8), selects up to 4 images that cover
distinct perspectives of the vehicle:
  Slot 1 → hero exterior (best quality exterior shot)
  Slot 2 → secondary exterior (different angle from slot 1)
  Slot 3 → cabin shot (interior / dashboard / seats), fallback to exterior
  Slot 4 → detail shot (wheel / engine / screen), fallback to cabin/exterior

Within each group, the highest-scored image is always chosen.
"""

from __future__ import annotations

from .image_scoring_engine import ScoredImage

# ── Type group definitions ────────────────────────────────────────────────
_EXTERIOR = frozenset({"front_34_exterior", "front_exterior", "side_exterior", "rear_exterior"})
_CABIN    = frozenset({"interior", "dashboard", "seats"})
_DETAIL   = frozenset({"wheel", "engine", "screen", "logo"})

# Preferred type groups for each grid slot (0-indexed)
_SLOT_PREFERENCE: list[frozenset[str]] = [
    _EXTERIOR,                      # slot 0: hero — best exterior
    _EXTERIOR,                      # slot 1: secondary exterior (different subtype)
    _CABIN | _EXTERIOR,             # slot 2: cabin, fallback to exterior
    _DETAIL | _CABIN | _EXTERIOR,   # slot 3: detail, fallback to cabin/exterior
]


class SmartSelectionEngine:

    def select(self, scored: list[ScoredImage], target_n: int) -> list[ScoredImage]:
        """
        From scored (sorted score-desc, length ≥ target_n), return a
        diversity-optimised list of target_n images.

        scored[0] is always kept as slot 0 (hero), allowing the caller to
        apply a hero-pin override before calling this method.
        """
        if not scored:
            return []

        target_n = min(target_n, len(scored))
        selected: list[ScoredImage] = [scored[0]]
        remaining: list[ScoredImage] = list(scored[1:])

        for slot_idx in range(1, target_n):
            if not remaining:
                break

            preferred = _SLOT_PREFERENCE[slot_idx] if slot_idx < len(_SLOT_PREFERENCE) else None
            chosen: ScoredImage | None = None

            if preferred:
                # For the second exterior slot, avoid the exact same subtype
                # already used in slot 1 (e.g. don't pick two front_34_exterior)
                skip_types: set[str] = set()
                if slot_idx == 1:
                    skip_types.add(selected[0].analysis.image_type)

                for img in remaining:
                    t = img.analysis.image_type
                    if t in preferred and t not in skip_types:
                        chosen = img
                        break

            # Fallback: highest-scored image still in pool
            if chosen is None:
                chosen = remaining[0]

            selected.append(chosen)
            remaining.remove(chosen)

        # Re-assign contiguous ranks
        for i, s in enumerate(selected):
            s.rank = i

        return selected
