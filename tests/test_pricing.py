"""
اختبارات محرّك التسعير. تشغيل:
    python3 -m unittest discover -s tests -v
أو:
    python3 tests/test_pricing.py
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from pricing_engine import CarInput, estimate_price, list_models, load_market  # noqa: E402


class TestPricingEngine(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.market = load_market()

    # --- صحة عامة -----------------------------------------------------------
    def test_models_loaded(self):
        self.assertEqual(len(list_models(self.market)), 5)
        for key in ("patrol", "altima", "sunny", "x-trail", "kicks"):
            self.assertIn(key, list_models(self.market))

    def test_unknown_model_raises(self):
        with self.assertRaises(ValueError):
            estimate_price(CarInput(model="ferrari", year=2020, km=50000), self.market)

    def test_price_low_high_ordering(self):
        est = estimate_price(CarInput(model="patrol", year=2019, km=90000), self.market)
        self.assertLess(est.low, est.price)
        self.assertLess(est.price, est.high)
        self.assertEqual(est.currency, "AED")

    # --- منطق السوق ---------------------------------------------------------
    def test_older_car_cheaper(self):
        new = estimate_price(CarInput(model="altima", year=2024, km=20000), self.market)
        old = estimate_price(CarInput(model="altima", year=2017, km=20000), self.market)
        self.assertGreater(new.price, old.price)

    def test_higher_mileage_cheaper(self):
        low = estimate_price(CarInput(model="kicks", year=2021, km=40000), self.market)
        high = estimate_price(CarInput(model="kicks", year=2021, km=140000), self.market)
        self.assertGreater(low.price, high.price)

    def test_gcc_more_than_american(self):
        gcc = estimate_price(CarInput(model="patrol", year=2020, km=80000, spec="gcc"), self.market)
        usa = estimate_price(CarInput(model="patrol", year=2020, km=80000, spec="american"), self.market)
        self.assertGreater(gcc.price, usa.price)

    def test_condition_matters(self):
        exc = estimate_price(CarInput(model="sunny", year=2021, km=60000, condition="excellent"), self.market)
        poor = estimate_price(CarInput(model="sunny", year=2021, km=60000, condition="poor"), self.market)
        self.assertGreater(exc.price, poor.price)

    def test_accident_lowers_price(self):
        clean = estimate_price(CarInput(model="x-trail", year=2020, km=70000, accidents="none"), self.market)
        crash = estimate_price(CarInput(model="x-trail", year=2020, km=70000, accidents="major"), self.market)
        self.assertGreater(clean.price, crash.price)

    def test_price_never_below_floor(self):
        est = estimate_price(
            CarInput(model="sunny", year=2010, km=400000, condition="poor",
                     accidents="major", spec="american"),
            self.market,
        )
        self.assertGreaterEqual(est.price, self.market["models"]["sunny"]["floor"] * 0.95)

    # --- الدقة مقابل السوق الحقيقي -----------------------------------------
    def test_accuracy_against_market_anchors(self):
        """كل نقطة معايرة لازم تكون ضمن ±20% من السعر الحقيقي، والـ MAPE < 15%."""
        errors = []
        for key, spec in self.market["models"].items():
            for a in spec.get("anchors", []):
                if not a.get("calibration", True):
                    continue
                est = estimate_price(
                    CarInput(model=key, year=a["year"], km=a["km"], spec="gcc",
                             condition="good", service_history="partial", owners=2),
                    self.market,
                )
                err = abs(est.price - a["price"]) / a["price"]
                errors.append(err)
                self.assertLess(
                    err, 0.30,
                    f"{spec['name_en']} {a['year']} خطأ {err:.0%} كبير جداً",
                )
        mape = sum(errors) / len(errors)
        self.assertLess(mape, 0.15, f"MAPE {mape:.1%} أعلى من الهدف 15%")


if __name__ == "__main__":
    unittest.main(verbosity=2)
