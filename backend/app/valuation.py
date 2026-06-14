"""محرّك التقدير بطريقة المقارنات (Comparables).

يأخذ بيانات السوق الحقيقية لكل (موديل + سنة) ويحسب سعراً تقديرياً:
1. يبدأ من وسيط السوق (median) للفئة المرجعية في سنة السيارة (مع استيفاء خطي بين السنين).
2. يعدّل حسب الفئة المختارة (نسبة سعرها الجديد للفئة المرجعية).
3. يعدّل حسب فرق المسافة عن المتوقع.
4. يطبّق معاملات الحالة والمواصفات الإقليمية.
5. يعطي نطاقاً + درجة ثقة بناءً على عدد العينات.

المنطق نقي (لا يعتمد على الشبكة) ليسهل اختباره.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


# معاملات قابلة للتعديل (نفس فلسفة pricing_config في التطبيق).
DEFAULT_CONFIG = {
    "current_year": 2025,
    "expected_km_per_year": 18000,
    "km_penalty_per_km": {
        "toyota:land_cruiser": 0.7,
        "nissan:patrol": 0.6,
        "lexus:es": 0.5,
        "mitsubishi:pajero": 0.25,
        "hyundai:elantra": 0.2,
    },
    "default_km_penalty_per_km": 0.4,
    "condition_factors": {
        "excellent": 1.05,
        "very_good": 1.0,
        "good": 0.93,
        "fair": 0.85,
        "needs_work": 0.72,
    },
    "region_factors": {
        "gcc": 1.0,
        "japanese": 0.97,
        "european": 0.95,
        "american": 0.92,
        "canadian": 0.9,
        "unknown": 0.85,
    },
    "range_spread": 0.07,
}


@dataclass
class EstimateResult:
    estimated: float
    low: float
    high: float
    market_low: float
    market_high: float
    samples: int
    confidence: str  # high / medium / low
    based_on_year_price: float


class ValuationEngine:
    def __init__(self, market_stats: dict, config: Optional[dict] = None):
        self.stats = market_stats.get("models", market_stats)
        self.config = config or DEFAULT_CONFIG

    # ---- مساعدات ----
    def model_key(self, brand_id: str, model_id: str) -> str:
        return f"{brand_id}:{model_id}"

    def _interp_year_median(self, by_year: dict, year: int) -> float:
        years = sorted(int(y) for y in by_year)
        if not years:
            return 0.0
        if str(year) in by_year:
            return float(by_year[str(year)]["median"])
        if year <= years[0]:
            return float(by_year[str(years[0])]["median"])
        if year >= years[-1]:
            return float(by_year[str(years[-1])]["median"])
        lower = max(y for y in years if y <= year)
        upper = min(y for y in years if y >= year)
        p_low = float(by_year[str(lower)]["median"])
        p_high = float(by_year[str(upper)]["median"])
        t = (year - lower) / (upper - lower)
        return p_low + (p_high - p_low) * t

    def _nearest_year_entry(self, by_year: dict, year: int) -> dict:
        years = sorted(int(y) for y in by_year)
        nearest = min(years, key=lambda y: abs(y - year))
        return by_year[str(nearest)]

    def _confidence(self, samples: int) -> str:
        if samples >= 20:
            return "high"
        if samples >= 8:
            return "medium"
        return "low"

    # ---- الحساب الرئيسي ----
    def estimate(
        self,
        brand_id: str,
        model_id: str,
        trim_id: str,
        year: int,
        km: int,
        condition: str = "very_good",
        region: str = "gcc",
    ) -> EstimateResult:
        key = self.model_key(brand_id, model_id)
        model_stats = self.stats.get(key)
        if model_stats is None:
            raise KeyError(f"لا توجد بيانات سوق للموديل: {key}")

        by_year = model_stats["by_year"]
        base = self._interp_year_median(by_year, year)

        # تعديل الفئة بنسبة سعر الجديد.
        trim_prices = model_stats.get("trim_new_prices", {})
        ref_trim = model_stats.get("reference_trim")
        ref_new = float(trim_prices.get(ref_trim, 0) or 0)
        trim_new = float(trim_prices.get(trim_id, ref_new) or ref_new)
        trim_mult = (trim_new / ref_new) if ref_new > 0 else 1.0
        price_for_car = base * trim_mult

        # تعديل المسافة.
        age = max(self.config["current_year"] - year, 0)
        expected_km = self.config["expected_km_per_year"] * age
        km_diff = km - expected_km
        km_penalty = self.config["km_penalty_per_km"].get(
            key, self.config["default_km_penalty_per_km"]
        )
        price_after_km = price_for_car - km_diff * km_penalty

        # الحالة والمواصفات.
        cond_factor = self.config["condition_factors"].get(condition, 1.0)
        region_factor = self.config["region_factors"].get(region, 1.0)
        estimated = price_after_km * cond_factor * region_factor

        # حدود من نطاق السوق الفعلي للسنة الأقرب (مضروبة في معامل الفئة).
        entry = self._nearest_year_entry(by_year, year)
        market_low = float(entry["low"]) * trim_mult
        market_high = float(entry["high"]) * trim_mult
        samples = int(entry.get("samples", 0))

        # نبقي التقدير ضمن حدود السوق المعقولة (بهامش بسيط).
        estimated = max(market_low * 0.85, min(estimated, market_high * 1.1))

        spread = self.config["range_spread"]
        low = estimated * (1 - spread)
        high = estimated * (1 + spread)

        return EstimateResult(
            estimated=round(estimated),
            low=round(low),
            high=round(high),
            market_low=round(market_low),
            market_high=round(market_high),
            samples=samples,
            confidence=self._confidence(samples),
            based_on_year_price=round(base),
        )
