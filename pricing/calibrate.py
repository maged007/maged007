#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
سكربت المعايرة:
  1) يقرأ العيّنات اليدوية (samples/market_samples.json).
  2) السعر المستهدف لكل عيّنة = سعر الإعلان × 0.88 (الأساس الموحّد لكل البراندات).
  3) يطبع نسبة الخطأ الحالية (MdAPE) قبل أي تعديل.
  4) يقترح:
       (أ) منحنى احتفاظ كل براند  → من السيدانات/المتوسطات لكل عمر.
       (ب) عامل الطلب لكل موديل   = وسيط(السعر المستهدف ÷ المتوقّع من منحنى البراند).
  5) يطبع MdAPE المتوقّع لو طُبّقت العوامل المقترحة.

الاستخدام:
  python3 calibrate.py
  python3 calibrate.py --write   # يكتب عامل الطلب المقترح إلى ملف البيانات
"""

import argparse
import json
import os
import statistics

from engine import (
    load_data, estimate, brand_retention, km_factor,
    spec_factor, condition_factor, DATA_PATH,
)

SAMPLES = os.path.join(os.path.dirname(__file__), "samples", "market_samples.json")


def load_samples(path=SAMPLES):
    with open(path, encoding="utf-8") as f:
        blob = json.load(f)
    return blob["current_year"], blob["samples"]


def mdape(estimates, targets):
    """الوسيط المطلق لنسبة الخطأ (Median Absolute Percentage Error)."""
    errs = [abs(e - t) / t for e, t in zip(estimates, targets) if t]
    return statistics.median(errs) if errs else float("nan")


def target_price(data, sample):
    return sample["ad_price"] * data["_meta"]["ad_to_sale_ratio"]


def expected_without_demand(data, sample, cur_year):
    """المتوقّع من كل المعاملات ما عدا عامل الطلب (= القاعدة لاشتقاق الطلب)."""
    m = data["brands"][sample["brand"]]["models"][sample["model"]]
    age = cur_year - sample["year"]
    return (
        m["dealer_price"]
        * brand_retention(data, sample["brand"], age)
        * km_factor(data, age, sample["km"])
        * spec_factor(data, sample["spec"])
        * condition_factor(data, sample["condition"])
    )


def suggest_demand(data, samples, cur_year):
    """عامل الطلب المقترح لكل موديل = وسيط(المستهدف ÷ المتوقّع بدون الطلب)."""
    buckets = {}
    for s in samples:
        key = (s["brand"], s["model"])
        base = expected_without_demand(data, s, cur_year)
        if base > 0:
            buckets.setdefault(key, []).append(target_price(data, s) / base)
    return {k: round(statistics.median(v), 3) for k, v in buckets.items()}


def suggest_retention(data, samples, cur_year):
    """
    معايرة منحنى الاحتفاظ لكل براند: لكل عمر نحسب وسيط
    (المستهدف ÷ سعر_الوكيل ÷ باقي المعاملات) كنسبة احتفاظ ملحوظة.
    تُطبع للمراجعة اليدوية (لا تُكتب آلياً حفاظاً على المنحنى الأملس).
    """
    out = {}
    for s in samples:
        brand = s["brand"]
        age = cur_year - s["year"]
        m = data["brands"][brand]["models"][s["model"]]
        denom = (
            m["dealer_price"] * m["demand_factor"]
            * km_factor(data, age, s["km"])
            * spec_factor(data, s["spec"])
            * condition_factor(data, s["condition"])
        )
        if denom > 0:
            out.setdefault(brand, {}).setdefault(age, []).append(
                target_price(data, s) / denom)
    return {
        b: {age: round(statistics.median(v), 3) for age, v in sorted(ages.items())}
        for b, ages in out.items()
    }


def evaluate(data, samples, cur_year, demand_override=None):
    est, tgt = [], []
    for s in samples:
        age = cur_year - s["year"]
        if demand_override and (s["brand"], s["model"]) in demand_override:
            data["brands"][s["brand"]]["models"][s["model"]]["demand_factor"] = \
                demand_override[(s["brand"], s["model"])]
        est.append(estimate(data, s["brand"], s["model"], age, s["km"],
                            s["spec"], s["condition"]))
        tgt.append(target_price(data, s))
    return mdape(est, tgt), est, tgt


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true",
                    help="اكتب عامل الطلب المقترح إلى ملف البيانات")
    args = ap.parse_args()

    data = load_data()
    cur_year, samples = load_samples()
    print(f"عدد العيّنات: {len(samples)}\n")

    before, _, _ = evaluate(load_data(), samples, cur_year)
    print(f"MdAPE قبل المعايرة: {before*100:.1f}%\n")

    print("— منحنى الاحتفاظ الملحوظ لكل براند/عمر (للمراجعة اليدوية) —")
    ret = suggest_retention(load_data(), samples, cur_year)
    for b, ages in ret.items():
        pairs = "  ".join(f"{a}س={v}" for a, v in ages.items())
        print(f"  {b:11s}: {pairs}")

    print("\n— عامل الطلب المقترح لكل موديل —")
    demand = suggest_demand(load_data(), samples, cur_year)
    for (b, mdl), v in sorted(demand.items()):
        cur = data["brands"][b]["models"][mdl]["demand_factor"]
        print(f"  {b:11s} {mdl:14s}: حالي {cur:.2f}  →  مقترح {v:.3f}")

    after, _, _ = evaluate(load_data(), samples, cur_year, demand_override=demand)
    print(f"\nMdAPE المتوقّع بعد تطبيق عامل الطلب المقترح: {after*100:.1f}%")

    if args.write:
        for (b, mdl), v in demand.items():
            data["brands"][b]["models"][mdl]["demand_factor"] = v
        with open(DATA_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"\n✔ كُتب عامل الطلب المقترح إلى {DATA_PATH}")


if __name__ == "__main__":
    main()
