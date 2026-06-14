"""اختبارات محرّك التقدير (بدون شبكة).

شغّل: cd backend && python -m pytest -q   (أو) python -m unittest
"""

import json
import unittest
from pathlib import Path

import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.valuation import ValuationEngine  # noqa: E402
from app.ingest import Listing, recompute_stats  # noqa: E402

DATA = json.loads(
    (Path(__file__).resolve().parent.parent / "data" / "market_stats.json").read_text(
        encoding="utf-8"
    )
)


class ValuationTests(unittest.TestCase):
    def setUp(self):
        self.engine = ValuationEngine(DATA)

    def test_landcruiser_2020_reasonable(self):
        r = self.engine.estimate("toyota", "land_cruiser", "gxr", 2020, 90000)
        # المسافة المتوقعة 2020 = 90,000 → بدون عقوبة، خليجي/جيد جداً → ≈ وسيط السوق 196,000.
        self.assertAlmostEqual(r.estimated, 196000, delta=2000)
        self.assertGreater(r.high, r.estimated)
        self.assertLess(r.low, r.estimated)

    def test_higher_km_lower_price(self):
        low_km = self.engine.estimate("nissan", "patrol", "se", 2021, 40000).estimated
        high_km = self.engine.estimate("nissan", "patrol", "se", 2021, 200000).estimated
        self.assertLess(high_km, low_km)

    def test_higher_trim_higher_price(self):
        se = self.engine.estimate("nissan", "patrol", "se", 2021, 80000).estimated
        le = self.engine.estimate("nissan", "patrol", "le_platinum", 2021, 80000).estimated
        self.assertGreater(le, se)

    def test_condition_effect(self):
        exc = self.engine.estimate("lexus", "es", "es350_prestige", 2021, 60000, condition="excellent").estimated
        bad = self.engine.estimate("lexus", "es", "es350_prestige", 2021, 60000, condition="needs_work").estimated
        self.assertGreater(exc, bad)

    def test_region_effect(self):
        gcc = self.engine.estimate("lexus", "es", "es350_prestige", 2021, 60000, region="gcc").estimated
        usa = self.engine.estimate("lexus", "es", "es350_prestige", 2021, 60000, region="american").estimated
        self.assertGreater(gcc, usa)

    def test_newer_more_expensive(self):
        newer = self.engine.estimate("hyundai", "elantra", "smart", 2023, 40000).estimated
        older = self.engine.estimate("hyundai", "elantra", "smart", 2018, 40000).estimated
        self.assertGreater(newer, older)

    def test_unknown_model_raises(self):
        with self.assertRaises(KeyError):
            self.engine.estimate("ford", "raptor", "base", 2020, 50000)

    def test_confidence_levels(self):
        r = self.engine.estimate("toyota", "land_cruiser", "gxr", 2022, 60000)
        self.assertIn(r.confidence, ("high", "medium", "low"))


class IngestTests(unittest.TestCase):
    def test_recompute_normalizes_trims(self):
        ref_trims = {"nissan:patrol": "se"}
        prices = {"nissan:patrol": {"se": 258900, "le_platinum": 388900}}
        listings = [
            Listing("nissan", "patrol", "se", 2021, 80000, 158000),
            # نفس السنة لكن فئة أعلى وسعرها أعلى → بعد التطبيع يقترب من الـ se.
            Listing("nissan", "patrol", "le_platinum", 2021, 80000, 237000),
        ]
        stats = recompute_stats(listings, ref_trims, prices)
        by_year = stats["nissan:patrol"]["by_year"]["2021"]
        self.assertEqual(by_year["samples"], 2)
        # le_platinum/se ≈ 1.5، فـ 237000/1.5 ≈ 158000 → الوسيط قريب من 158000.
        self.assertAlmostEqual(by_year["median"], 158000, delta=3000)


if __name__ == "__main__":
    unittest.main()
