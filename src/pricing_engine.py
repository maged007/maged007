"""
محرّك تسعير السيارات المستعملة في السوق الإماراتي — النسخة 2.

الفلسفة: السعر مرساة على **سعر الوكيل (الجديد) لكل فئة**، ثم يُهلَك حسب العمر والكيلومترات،
وتُطبَّق معاملات المواصفات (خليجي/وارد) والحالة. كل المعدلات **نِسب مئوية** في data/market.json.
القيمة قبل معامل الحالة = سعر السيارة في حالة "ممتازة"؛ الحالات الأقل تخصم منها.

كل المعايرة مشتقة من داتا حقيقية (Automark). بدون أي مكتبات خارجية، فينتقل نفس المنطق 1:1
إلى واجهة الويب.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from typing import Optional

DATA_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "market.json")

CONDITIONS = ["excellent", "very_good", "good", "fair", "weak"]  # من الأعلى للأدنى

_MARKET_CACHE: Optional[dict] = None


# ---------------------------------------------------------------------------
# تحميل البيانات
# ---------------------------------------------------------------------------
def load_market(path: str = DATA_PATH) -> dict:
    global _MARKET_CACHE
    if _MARKET_CACHE is None or path != DATA_PATH:
        with open(path, "r", encoding="utf-8") as f:
            _MARKET_CACHE = json.load(f)
    return _MARKET_CACHE


def find_model(market: dict, model_name: str):
    """يرجّع (مفتاح_البراند, بيانات_البراند, بيانات_الموديل) لأي موديل عبر كل البراندات."""
    key = model_name.strip().lower()
    for brand_key, brand in market["brands"].items():
        if key in brand["models"]:
            return brand_key, brand, brand["models"][key]
    raise ValueError(f"الموديل '{model_name}' غير مدعوم. المتاح: {', '.join(list_models(market))}")


def list_models(market: Optional[dict] = None) -> list[str]:
    market = market or load_market()
    out = []
    for brand in market["brands"].values():
        out.extend(brand["models"].keys())
    return out


# ---------------------------------------------------------------------------
# مساعدات
# ---------------------------------------------------------------------------
def _clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))


def _round_to(x: float, base: int) -> int:
    return int(base * round(x / base))


# ---------------------------------------------------------------------------
# المدخلات / المخرجات
# ---------------------------------------------------------------------------
@dataclass
class CarInput:
    model: str
    year: int
    km: int
    spec: str = "gcc"           # gcc | american | canadian | european | japanese | other
    condition: str = "good"     # excellent | very_good | good | fair | weak
    trim: Optional[str] = None  # يستخدم الافتراضي لو None


@dataclass
class PriceEstimate:
    price: int
    low: int
    high: int
    currency: str = "AED"
    model: str = ""
    age: int = 0
    new_price: int = 0
    breakdown: dict = field(default_factory=dict)

    def as_dict(self) -> dict:
        return {
            "price": self.price, "low": self.low, "high": self.high,
            "currency": self.currency, "model": self.model, "age": self.age,
            "new_price": self.new_price, "breakdown": self.breakdown,
        }


# ---------------------------------------------------------------------------
# الحساب الأساسي
# ---------------------------------------------------------------------------
def estimate_price(car: CarInput, market: Optional[dict] = None) -> PriceEstimate:
    market = market or load_market()
    _, brand, m = find_model(market, car.model)

    new_year = m.get("new_year", market["meta"].get("base_year"))
    age = max(0, int(new_year) - int(car.year))

    # 1) مرساة سعر الوكيل حسب الفئة
    trim = car.trim or m["default_trim"]
    new_prices = m["new_prices_gcc"]
    new_price = new_prices.get(trim, new_prices[m["default_trim"]])

    # 2) الإهلاك حسب العمر (الاحتفاظ من الموديل وإلا الافتراضي للبراند)
    ret = m.get("retention_pct", brand["default_retention_pct"])
    if age <= 0:
        excellent = float(new_price)                       # موديل جديد = سعر الوكيل (حالة ممتازة)
    else:
        excellent = new_price * (ret["year1"] / 100.0) * (ret["annual"] / 100.0) ** (age - 1)

    # 3) الكيلومترات مقابل المتوقع للعمر (زيادة تنزّل / نقص يرفع، بحدود غير متماثلة)
    km_cfg = m["km"]
    expected_km = km_cfg["expected_km_per_year"] * age
    km_delta = car.km - expected_km
    km_adjust = -(km_cfg["pct_per_10k"] / 100.0) * (km_delta / 10_000.0)
    km_adjust = _clamp(km_adjust, -km_cfg["max_down_pct"] / 100.0, km_cfg["max_up_pct"] / 100.0)
    mileage_mult = 1.0 + km_adjust

    # 4) المواصفات (خليجي/وارد)
    spec_f = m["spec_factors_pct"]
    spec_mult = spec_f.get(car.spec, spec_f.get("other", 100)) / 100.0

    # 5) الحالة (5 شرائح، الأعلى = الأساس). الموديل يتجاوز العام لو موجود.
    cond_f = m.get("condition_factors_pct", market["condition_factors_pct"])
    cond_mult = cond_f.get(car.condition, cond_f["good"]) / 100.0

    # 6) عامل العرض/الطلب على الموديل (منفصل عن احتفاظ البراند). افتراضي 100% = لا تغيير.
    demand_mult = m.get("demand_factor_pct", 100) / 100.0

    value = excellent * demand_mult * mileage_mult * spec_mult * cond_mult

    # 7) أرضية السعر
    floor = m["floor"]
    floored = value <= floor
    value = max(value, floor)

    # 8) المدى السعري
    spread = m.get("range_spread_pct", 8) / 100.0
    price_r = _round_to(value, 500)
    low_r = _round_to(value * (1 - spread), 500)
    high_r = _round_to(value * (1 + spread), 500)

    return PriceEstimate(
        price=price_r, low=low_r, high=high_r,
        currency=market["meta"]["currency"], model=m["name_ar"],
        age=age, new_price=int(new_price),
        breakdown={
            "new_price": int(new_price),
            "trim": trim,
            "age_retention_pct": round((ret["year1"] / 100.0) * (ret["annual"] / 100.0) ** max(0, age - 1) * 100, 1) if age > 0 else 100.0,
            "excellent_value": round(excellent),
            "expected_km": expected_km,
            "mileage_mult": round(mileage_mult, 4),
            "demand_mult": demand_mult,
            "spec_mult": spec_mult,
            "condition": car.condition,
            "condition_mult": cond_mult,
            "floored": floored,
        },
    )


if __name__ == "__main__":
    for c in [
        CarInput("altima", 2026, 0, "gcc", "excellent", "SV"),
        CarInput("altima", 2021, 70000, "gcc", "good"),
        CarInput("altima", 2018, 200000, "american", "fair", "S"),
    ]:
        e = estimate_price(c)
        print(f"{c.model} {c.year} {c.condition} {c.spec}: {e.price:,} AED "
              f"(مدى {e.low:,}–{e.high:,}, جديد {e.new_price:,})")
