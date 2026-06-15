#!/usr/bin/env python3
"""
يشتق **عامل الطلب** (demand_factor_pct) لكل موديل من إعلانات حقيقية، على أساس موحّد:

    ناتج "ممتازة" المستهدف = سعر الإعلان × haircut (0.88)   ← سعر سوق واقعي
    المتوقّع من منحنى البراند = سعر_الوكيل × احتفاظ_البراند(العمر) × معامل_الكم
    عامل الطلب = المستهدف ÷ المتوقّع

بكده **احتفاظ البراند** يمسك الإهلاك العام (تويوتا>هوندا>نيسان)، و**عامل الطلب** يمسك
عرض/طلب الموديل تحديداً (RAV4/لاندكروزر فوق 100%، السيدانات حواليها).

يقرأ منحنى البراند من data/market.json (default_retention_pct) ونقاط السوق من
data/raw/market_refs.json. لا يكتب أي حاجة — يطبع القيم المقترحة بس.

تشغيل:  python3 scripts/calibrate_brand.py
"""
import json
import os

ROOT = os.path.join(os.path.dirname(__file__), "..")
MARKET = os.path.join(ROOT, "data", "market.json")
REFS = os.path.join(ROOT, "data", "raw", "market_refs.json")


def find_model(market, key):
    for bk, brand in market["brands"].items():
        if key in brand["models"]:
            return bk, brand, brand["models"][key]
    raise KeyError(key)


def excellent_predicted(market, brand, m, year, km):
    """قيمة 'ممتازة' المتوقّعة من منحنى البراند (demand=1, gcc) — نفس حساب المحرّك بدون تقريب."""
    new_year = m.get("new_year", market["meta"]["base_year"])
    age = max(0, new_year - year)
    trim = m["default_trim"]
    new_price = m["new_prices_gcc"].get(trim, m["new_prices_gcc"][m["default_trim"]])
    ret = m.get("retention_pct", brand["default_retention_pct"])
    if age <= 0:
        excellent = float(new_price)
    else:
        excellent = new_price * (ret["year1"] / 100.0) * (ret["annual"] / 100.0) ** (age - 1)
    km_cfg = m["km"]
    km_delta = km - km_cfg["expected_km_per_year"] * age
    adj = -(km_cfg["pct_per_10k"] / 100.0) * (km_delta / 10_000.0)
    adj = max(-km_cfg["max_down_pct"] / 100.0, min(km_cfg["max_up_pct"] / 100.0, adj))
    return excellent * (1.0 + adj), age, ret


def main() -> int:
    market = json.load(open(MARKET, encoding="utf-8"))
    refs = json.load(open(REFS, encoding="utf-8"))
    haircut = refs["haircut_asking_to_excellent"]

    print(f"الأساس الموحّد: ناتج 'ممتازة' = سعر الإعلان × {haircut}\n")
    print(f"{'الموديل':<16}{'براند':<8}{'عمر':>4}{'إعلان':>9}{'مستهدف':>9}{'متوقّع':>9}{'عامل الطلب':>12}")
    print("-" * 70)
    by_model = {}
    for r in refs["listings"]:
        bk, brand, m = find_model(market, r["model"])
        pred, age, ret = excellent_predicted(market, brand, m, r["year"], r["km"])
        target = r["asking"] * haircut
        demand = target / pred * 100.0
        by_model.setdefault(r["model"], []).append(demand)
        print(f"{r['model']:<16}{bk:<8}{age:>4}{r['asking']:>9}{target:>9.0f}{pred:>9.0f}{demand:>11.0f}%"
              f"   (احتفاظ {ret['year1']}/{ret['annual']})")

    print("\n=== عامل الطلب المقترح لكل موديل (متوسط) ===")
    for model, vals in by_model.items():
        avg = sum(vals) / len(vals)
        note = "" if abs(avg - 100) < 4 else ("  ← طلب عالٍ" if avg > 100 else "  ← طلب ضعيف")
        print(f'  "{model}": demand_factor_pct = {round(avg)}{note}')
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
