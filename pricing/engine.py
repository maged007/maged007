#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
محرّك تسعير السيارات المستعملة في السوق الإماراتي.
يطبّق المعادلة بالترتيب:

  السعر = سعر_الوكيل[الفئة]
        × احتفاظ_البراند(العمر)
        × عامل_الطلب[الموديل]
        × معامل_الكيلومترات
        × معامل_المواصفات
        × معامل_الحالة

كل المعدلات تُقرأ من data/pricing_data.json — ملف بيانات واحد قابل للتعديل.
"""

import json
import os

DATA_PATH = os.path.join(os.path.dirname(__file__), "data", "pricing_data.json")

CONDITIONS = ["excellent", "very_good", "good", "fair", "needs_work"]
SPECS = ["gcc", "imported"]


def load_data(path=DATA_PATH):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def tier_retention(data, tier_name, age):
    """منحنى احتفاظ لطبقة معيّنة حسب العمر."""
    tier = data["retention_tiers"][tier_name]
    if age <= 0:
        return 1.0
    r = (1.0 - tier["first_year_drop"]) * (1.0 - tier["annual_drop"]) ** (age - 1)
    return max(r, tier["floor"])


def model_tier(data, brand, model):
    """طبقة الاحتفاظ الفعلية للموديل: تجاوز على مستوى الموديل إن وُجد، وإلا طبقة البراند."""
    m = data["brands"][brand]["models"][model]
    return m.get("retention_tier") or data["brand_tier"][brand]


def brand_retention(data, brand, age):
    """احتفاظ على مستوى البراند (للتقارير العامة)."""
    return tier_retention(data, data["brand_tier"][brand], age)


def model_retention(data, brand, model, age):
    """احتفاظ الموديل (يحترم تجاوز الطبقة لكل موديل)."""
    return tier_retention(data, model_tier(data, brand, model), age)


def km_factor(data, age, km):
    """كم أكتر = أرخص / أقل = أغلى، مقارنة بالمتوقع للعمر."""
    cfg = data["km_factor"]
    expected = max(age, 0) * cfg["baseline_km_per_year"]
    delta = km - expected  # موجب = كم أعلى من المتوقع
    factor = 1.0 - (delta / 10000.0) * cfg["step_per_10k"]
    return max(cfg["min"], min(cfg["max"], factor))


def spec_factor(data, spec, brand=None):
    """معامل المواصفات. يدعم تجاوزاً لكل براند (spec_factor_by_brand) وإلا القيمة العامة."""
    by_brand = data.get("spec_factor_by_brand", {})
    if brand and spec in by_brand.get(brand, {}):
        return by_brand[brand][spec]
    return data["spec_factor"][spec]


def condition_factor(data, condition):
    return data["condition_factor"][condition]


def _resolve_model(data, brand, model):
    try:
        return data["brands"][brand]["models"][model]
    except KeyError:
        raise KeyError(f"غير موجود: brand={brand} model={model}")


def base_without_demand(data, brand, model, age, km, spec, condition):
    """ناتج كل المعاملات ما عدا عامل الطلب — تُستخدم في المعايرة لاشتقاق الطلب."""
    m = _resolve_model(data, brand, model)
    return (
        m["dealer_price"]
        * model_retention(data, brand, model, age)
        * km_factor(data, age, km)
        * spec_factor(data, spec, brand)
        * condition_factor(data, condition)
    )


def estimate(data, brand, model, age, km,
             spec="gcc", condition="excellent", return_breakdown=False):
    """يرجّع سعر إعادة البيع المقدّر (AED). اختيارياً مع تفصيل كل معامل."""
    m = _resolve_model(data, brand, model)

    f_dealer = m["dealer_price"]
    f_ret = model_retention(data, brand, model, age)
    f_dem = m["demand_factor"]
    f_km = km_factor(data, age, km)
    f_spec = spec_factor(data, spec, brand)
    f_cond = condition_factor(data, condition)

    price = f_dealer * f_ret * f_dem * f_km * f_spec * f_cond

    if not return_breakdown:
        return round(price)

    return {
        "price": round(price),
        "breakdown": {
            "dealer_price": f_dealer,
            "brand_retention": round(f_ret, 4),
            "demand_factor": f_dem,
            "km_factor": round(f_km, 4),
            "spec_factor": f_spec,
            "condition_factor": f_cond,
        },
    }


def _cli():
    import argparse
    p = argparse.ArgumentParser(description="تقدير سعر سيارة مستعملة")
    p.add_argument("brand")
    p.add_argument("model")
    p.add_argument("--age", type=int, required=True, help="العمر بالسنوات")
    p.add_argument("--km", type=int, required=True, help="عدد الكيلومترات")
    p.add_argument("--spec", choices=SPECS, default="gcc")
    p.add_argument("--condition", choices=CONDITIONS, default="excellent")
    args = p.parse_args()

    data = load_data()
    res = estimate(data, args.brand, args.model, args.age, args.km,
                   args.spec, args.condition, return_breakdown=True)
    print(json.dumps(res, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    _cli()
