"""
اختبارات محرّك التسعير (النسخة 2). تشغيل:
    python3 -m unittest discover -s tests -v
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from pricing_engine import (  # noqa: E402
    CONDITIONS, CarInput, estimate_price, find_model, list_models, load_market,
)


class TestPricingEngine(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.market = load_market()

    # --- صحة عامة -----------------------------------------------------------
    def test_altima_loaded(self):
        self.assertIn("altima", list_models(self.market))

    def test_unknown_model_raises(self):
        with self.assertRaises(ValueError):
            estimate_price(CarInput("ferrari", 2020, 50000), self.market)

    def test_low_high_ordering(self):
        e = estimate_price(CarInput("altima", 2021, 70000), self.market)
        self.assertLess(e.low, e.price)
        self.assertLess(e.price, e.high)
        self.assertEqual(e.currency, "AED")

    # --- مرساة سعر الوكيل ----------------------------------------------------
    def test_new_year_equals_dealer_price(self):
        """موديل السنة الجديدة بحالة ممتازة = سعر الوكيل للفئة بالظبط."""
        _, _, m = find_model(self.market, "altima")
        for trim, price in m["new_prices_gcc"].items():
            e = estimate_price(CarInput("altima", m["new_year"], 0, "gcc", "excellent", trim), self.market)
            self.assertEqual(e.price, round(price / 500) * 500)

    def test_higher_trim_costs_more(self):
        base = estimate_price(CarInput("altima", 2022, 50000, trim="S"), self.market)
        top = estimate_price(CarInput("altima", 2022, 50000, trim="Platinum"), self.market)
        self.assertGreater(top.price, base.price)

    # --- منطق السوق ---------------------------------------------------------
    def test_older_is_cheaper(self):
        new = estimate_price(CarInput("altima", 2024, 30000), self.market)
        old = estimate_price(CarInput("altima", 2016, 30000), self.market)
        self.assertGreater(new.price, old.price)

    def test_more_km_cheaper_less_km_dearer(self):
        lo = estimate_price(CarInput("altima", 2021, 40000), self.market)
        mid = estimate_price(CarInput("altima", 2021, 90000), self.market)
        hi = estimate_price(CarInput("altima", 2021, 180000), self.market)
        self.assertGreater(lo.price, mid.price)
        self.assertGreater(mid.price, hi.price)

    def test_gcc_more_than_import(self):
        gcc = estimate_price(CarInput("altima", 2020, 80000, spec="gcc"), self.market)
        imp = estimate_price(CarInput("altima", 2020, 80000, spec="american"), self.market)
        self.assertGreater(gcc.price, imp.price)

    # --- الحالة: 5 شرائح، الأعلى = الأساس، تنازلية ----------------------------
    def test_condition_monotonic_decreasing(self):
        prices = [estimate_price(CarInput("altima", 2020, 80000, condition=c), self.market).price
                  for c in CONDITIONS]   # excellent .. weak
        for a, b in zip(prices, prices[1:]):
            self.assertGreaterEqual(a, b)
        self.assertGreater(prices[0], prices[-1])  # ممتازة > ضعيفة

    def test_excellent_is_the_anchor(self):
        """ممتازة هي الأعلى (السعر الأساسي مثبّت عليها)."""
        e = estimate_price(CarInput("altima", 2021, 60000, condition="excellent"), self.market)
        for c in ["very_good", "good", "fair", "weak"]:
            self.assertGreaterEqual(
                e.price, estimate_price(CarInput("altima", 2021, 60000, condition=c), self.market).price)

    # --- نقطة الوسط لأحدث سنة ------------------------------------------------
    def test_newest_used_year_between_dealer_and_listings(self):
        """أحدث سنة مستعملة (جيدة) تقع بين سعر الوكيل ووسيط الإعلانات تقريباً."""
        _, _, m = find_model(self.market, "altima")
        dealer = m["new_prices_gcc"]["SV"]
        e = estimate_price(CarInput("altima", m["new_year"] - 1, 16000, "gcc", "good", "SV"), self.market)
        self.assertLess(e.price, dealer)          # أقل من سعر الوكيل
        self.assertGreater(e.price, dealer * 0.5)  # لكن ليس منهاراً

    # --- الأرضية -------------------------------------------------------------
    def test_floor_respected(self):
        _, _, m = find_model(self.market, "altima")
        e = estimate_price(CarInput("altima", 2008, 400000, "american", "weak", "S"), self.market)
        self.assertGreaterEqual(e.price, m["floor"] * 0.95)

    # --- عزل البراند ---------------------------------------------------------
    def test_brand_default_retention_fallback(self):
        """لو الموديل ملوش retention خاص، يستخدم معدّل البراند (آلية العزل)."""
        market = load_market()
        brand_key, brand, m = find_model(market, "altima")
        saved = m.pop("retention_pct")
        try:
            e = estimate_price(CarInput("altima", 2020, 80000), market)
            self.assertGreater(e.price, 0)  # يعمل بمعدّل البراند الافتراضي
        finally:
            m["retention_pct"] = saved

    # --- عامل العرض/الطلب ----------------------------------------------------
    def test_demand_factor_scales_price(self):
        """عامل الطلب يضرب السعر؛ موديل >100% أغلى من نفس المنحنى بـ100%."""
        market = load_market()
        _, _, m = find_model(market, "rav4")
        base = estimate_price(CarInput("rav4", 2024, 20000, "gcc", "excellent", "EXR"), market).price
        saved = m.pop("demand_factor_pct")  # شيله مؤقتاً = 100% (افتراضي)
        try:
            neutral = estimate_price(CarInput("rav4", 2024, 20000, "gcc", "excellent", "EXR"), market).price
            self.assertGreater(base, neutral)  # طلب RAV4 >100% فالسعر أعلى
            self.assertAlmostEqual(base / neutral, saved / 100.0, delta=0.02)
        finally:
            m["demand_factor_pct"] = saved

    def test_demand_factor_defaults_to_100(self):
        """غياب demand_factor_pct = 100% (لا تغيير) — يضمن ثبات الموديلات بدون العامل."""
        market = load_market()
        _, _, m = find_model(market, "sunny")  # نيسان صني — ملوش عامل طلب
        self.assertNotIn("demand_factor_pct", m)
        e = estimate_price(CarInput("sunny", 2022, 60000), market)
        self.assertGreater(e.price, 0)

    # --- الدقة مقابل السوق الحقيقي -------------------------------------------
    def test_accuracy_against_anchors(self):
        errs = []
        for key in list_models(self.market):
            _, _, m = find_model(self.market, key)
            for a in m.get("anchors", []):
                e = estimate_price(CarInput(
                    model=key, year=a["year"], km=a["km"],
                    spec=a.get("spec", "gcc"), trim=a.get("trim"), condition="good"), self.market)
                err = abs(e.price - a["price"]) / a["price"]
                errs.append(err)
                self.assertLess(err, 0.30, f"{key} {a['year']} خطأ {err:.0%}")
        self.assertLess(sum(errs) / len(errs), 0.15, "MAPE فوق 15%")


if __name__ == "__main__":
    unittest.main(verbosity=2)
