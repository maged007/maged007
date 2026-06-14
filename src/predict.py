#!/usr/bin/env python3
"""
أداة سطر أوامر لتقدير سعر سيارة مستعملة في السوق الإماراتي (النسخة 2 — التيما).

أمثلة:
    python3 src/predict.py --list
    python3 src/predict.py --model altima --year 2021 --km 70000 --trim SV
    python3 src/predict.py --model altima --year 2019 --km 120000 --spec american --condition fair
    python3 src/predict.py --model altima --year 2026 --km 0 --trim SL --condition excellent --json
"""
import argparse
import json
import sys

from pricing_engine import CONDITIONS, CarInput, estimate_price, find_model, list_models, load_market

COND_AR = {"excellent": "ممتازة", "very_good": "جيدة جداً", "good": "جيدة",
           "fair": "مقبولة", "weak": "ضعيفة"}


def _fmt(n: int) -> str:
    return f"{n:,}"


def main(argv=None) -> int:
    market = load_market()
    p = argparse.ArgumentParser(description="مقدّر سعر السيارات المستعملة - السوق الإماراتي")
    p.add_argument("--model", help="اسم الموديل (altima)")
    p.add_argument("--year", type=int, help="سنة الصنع")
    p.add_argument("--km", type=int, help="عدد الكيلومترات")
    p.add_argument("--trim", default=None, help="الفئة (S, SR, SV, SL, Platinum)")
    p.add_argument("--spec", default="gcc",
                   help="المواصفات: gcc | american | canadian | european | japanese | other")
    p.add_argument("--condition", default="good", choices=CONDITIONS,
                   help="الحالة: excellent | very_good | good | fair | weak")
    p.add_argument("--list", action="store_true", help="عرض الموديلات المدعومة")
    p.add_argument("--json", action="store_true", help="إخراج JSON")
    args = p.parse_args(argv)

    if args.list:
        print("الموديلات المدعومة:")
        for key in list_models(market):
            _, _, m = find_model(market, key)
            trims = "، ".join(m["new_prices_gcc"].keys())
            print(f"  - {key:<10} {m['name_ar']} ({m['name_en']})  | الفئات: {trims}")
        return 0

    if not (args.model and args.year and args.km is not None):
        p.error("لازم تحدد --model و --year و --km (أو استخدم --list)")

    try:
        est = estimate_price(CarInput(
            model=args.model, year=args.year, km=args.km, trim=args.trim,
            spec=args.spec, condition=args.condition), market)
    except ValueError as e:
        print(f"خطأ: {e}", file=sys.stderr)
        return 2

    if args.json:
        print(json.dumps(est.as_dict(), ensure_ascii=False, indent=2))
        return 0

    print()
    print(f"  {est.model}  موديل {args.year}  ({est.age} سنوات)  |  سعر الوكيل: {_fmt(est.new_price)}")
    print(f"  {_fmt(args.km)} كم  |  فئة: {est.breakdown['trim']}  |  "
          f"مواصفات: {args.spec}  |  الحالة: {COND_AR.get(args.condition, args.condition)}")
    print("  " + "─" * 42)
    print(f"  السعر التقديري:  {_fmt(est.price)} {est.currency}")
    print(f"  المدى المتوقع:   {_fmt(est.low)} – {_fmt(est.high)} {est.currency}")
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
