"""
محرّك تسعير السيارات المستعملة في السوق الإماراتي.
Used-car pricing engine calibrated for the UAE market (Nissan, v1).

المنطق: قيمة أساسية مبنية على العمر (منحنى إهلاك معاير على إعلانات حقيقية)،
ثم تُضرب فيها معاملات السوق الإماراتي: المواصفات (خليجي/أمريكي)، الكيلومترات،
الحالة، الحوادث، تاريخ الصيانة، وعدد المُلّاك.

The engine has zero third-party dependencies (Python standard library only),
so the exact same logic can be ported 1:1 to the web front-end.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from datetime import date
from typing import Optional

DATA_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "nissan_market.json")


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------
_MARKET_CACHE: Optional[dict] = None


def load_market(path: str = DATA_PATH) -> dict:
    """يحمّل ملف بيانات السوق (مع تخزين مؤقت)."""
    global _MARKET_CACHE
    if _MARKET_CACHE is None or path != DATA_PATH:
        with open(path, "r", encoding="utf-8") as f:
            _MARKET_CACHE = json.load(f)
    return _MARKET_CACHE


def list_models(market: Optional[dict] = None) -> list[str]:
    market = market or load_market()
    return list(market["models"].keys())


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def _current_year() -> int:
    return date.today().year


# ---------------------------------------------------------------------------
# Input / output structures
# ---------------------------------------------------------------------------
@dataclass
class CarInput:
    """مدخلات السيارة المراد تقييمها."""
    model: str
    year: int
    km: int
    spec: str = "gcc"               # gcc | american | canadian | european | japanese | other
    condition: str = "good"         # excellent | good | fair | poor
    accidents: str = "none"         # none | minor | major
    service_history: str = "partial"  # full | partial | none
    owners: int = 2                 # 1, 2, 3, 4+
    trim: Optional[str] = None      # خيار، يستخدم الافتراضي لو None


@dataclass
class PriceEstimate:
    """نتيجة التقييم."""
    price: int                      # أفضل تقدير (نقطة)
    low: int                        # الحد الأدنى المعقول
    high: int                       # الحد الأعلى المعقول
    currency: str = "AED"
    model: str = ""
    age: int = 0
    breakdown: dict = field(default_factory=dict)

    def as_dict(self) -> dict:
        return {
            "price": self.price,
            "low": self.low,
            "high": self.high,
            "currency": self.currency,
            "model": self.model,
            "age": self.age,
            "breakdown": self.breakdown,
        }


# ---------------------------------------------------------------------------
# Core calculation
# ---------------------------------------------------------------------------
def estimate_price(car: CarInput, market: Optional[dict] = None) -> PriceEstimate:
    """يقدّر سعر سيارة مستعملة بناءً على بيانات السوق المعايرة."""
    market = market or load_market()

    key = car.model.strip().lower()
    if key not in market["models"]:
        raise ValueError(
            f"الموديل '{car.model}' غير مدعوم. المتاح: {', '.join(market['models'])}"
        )

    spec = market["models"][key]
    factors = market["factors"]

    age = max(0, _current_year() - int(car.year))

    # 1) القيمة الأساسية حسب العمر (منحنى الإهلاك)
    msrp = spec["msrp"]
    if age <= 0:
        base = msrp                      # موديل السنة الحالية ~ شبه جديد
    else:
        base = msrp * spec["year1_retention"] * (spec["annual_retention"] ** (age - 1))

    # 2) معامل الفئة (Trim)
    trim = car.trim or spec["default_trim"]
    trim_mult = spec["trims"].get(trim, 1.0)
    base *= trim_mult

    # 3) تعديل الكيلومترات مقابل المتوقع لهذا العمر
    # (pct_per_10k قد يكون معايراً لكل موديل من داتا حقيقية، وإلا يُستخدم الافتراضي العام)
    expected_km = spec["expected_km_per_year"] * age
    km_delta = car.km - expected_km
    mlg = factors["mileage"]
    pct_per_10k = spec.get("pct_per_10k", mlg["pct_per_10k_km"])
    km_adjust = -pct_per_10k * (km_delta / 10_000.0)
    km_adjust = _clamp(km_adjust, -mlg["max_down"], mlg["max_up"])
    mileage_mult = 1.0 + km_adjust

    # 4) معاملات الحالة / المواصفات / الحوادث / الصيانة / المُلّاك
    # (spec_factors قد تكون معايرة لكل موديل، وإلا الافتراضي العام)
    spec_factors = spec.get("spec_factors", factors["spec"])
    spec_mult = spec_factors.get(car.spec, spec_factors.get("other", 1.0))
    cond_mult = factors["condition"].get(car.condition, 1.0)
    acc_mult = factors["accidents"].get(car.accidents, 1.0)
    svc_mult = factors["service_history"].get(car.service_history, 1.0)
    owners_key = "4+" if car.owners >= 4 else str(max(1, int(car.owners)))
    own_mult = factors["owners"].get(owners_key, 1.0)

    value = (
        base
        * mileage_mult
        * spec_mult
        * cond_mult
        * acc_mult
        * svc_mult
        * own_mult
    )

    # 5) أرضية السعر — لا ينزل عن حد معقول للسوق
    value = max(value, spec["floor"])

    # 6) المدى السعري
    spread = factors["range_spread"]
    low = value * (1.0 - spread)
    high = value * (1.0 + spread)

    # تقريب لأقرب 500 درهم
    price_r = _round_to(value, 500)
    low_r = _round_to(low, 500)
    high_r = _round_to(high, 500)

    return PriceEstimate(
        price=price_r,
        low=low_r,
        high=high_r,
        currency=market["meta"]["currency"],
        model=spec["name_ar"],
        age=age,
        breakdown={
            "msrp": msrp,
            "base_after_age": round(msrp * spec["year1_retention"] * (spec["annual_retention"] ** max(0, age - 1))) if age > 0 else msrp,
            "trim": trim,
            "trim_mult": trim_mult,
            "expected_km": expected_km,
            "mileage_mult": round(mileage_mult, 4),
            "spec_mult": spec_mult,
            "condition_mult": cond_mult,
            "accidents_mult": acc_mult,
            "service_mult": svc_mult,
            "owners_mult": own_mult,
            "raw_value": round(value),
            "floored": value <= spec["floor"] + 1,
        },
    )


def _round_to(x: float, base: int) -> int:
    return int(base * round(x / base))


if __name__ == "__main__":
    car = CarInput(model="patrol", year=2019, km=90000, spec="gcc", condition="good")
    est = estimate_price(car)
    print(json.dumps(est.as_dict(), ensure_ascii=False, indent=2))
