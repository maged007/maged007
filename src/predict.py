#!/usr/bin/env python3
"""
أداة سطر أوامر لتقدير سعر سيارة نيسان مستعملة في السوق الإماراتي.

أمثلة:
    python3 src/predict.py --model patrol --year 2019 --km 90000
    python3 src/predict.py --model altima --year 2021 --km 60000 --spec american --condition excellent
    python3 src/predict.py --list
    python3 src/predict.py --model kicks --year 2022 --km 45000 --json
"""
import argparse
import json
import sys

from pricing_engine import (
    CarInput,
    estimate_price,
    list_models,
    load_market,
)


def _fmt(n: int) -> str:
    return f"{n:,}"


def main(argv=None) -> int:
    market = load_market()
    p = argparse.ArgumentParser(
        description="مقدّر سعر السيارات المستعملة - السوق الإماراتي (نيسان)"
    )
    p.add_argument("--model", help="اسم الموديل (patrol, altima, sunny, x-trail, kicks)")
    p.add_argument("--year", type=int, help="سنة الصنع")
    p.add_argument("--km", type=int, help="عدد الكيلومترات")
    p.add_argument("--spec", default="gcc",
                   help="المواصفات: gcc | american | canadian | european | japanese | other")
    p.add_argument("--condition", default="good",
                   help="الحالة: excellent | good | fair | poor")
    p.add_argument("--accidents", default="none", help="الحوادث: none | minor | major")
    p.add_argument("--service", dest="service_history", default="partial",
                   help="الصيانة: full | partial | none")
    p.add_argument("--owners", type=int, default=2, help="عدد المُلّاك السابقين")
    p.add_argument("--trim", default=None, help="الفئة (اختياري)")
    p.add_argument("--list", action="store_true", help="عرض الموديلات المدعومة")
    p.add_argument("--json", action="store_true", help="إخراج JSON")
    args = p.parse_args(argv)

    if args.list:
        print("الموديلات المدعومة:")
        for key in list_models(market):
            m = market["models"][key]
            print(f"  - {key:<10} {m['name_ar']}  ({m['name_en']}, {m['body']})")
        return 0

    if not (args.model and args.year and args.km is not None):
        p.error("لازم تحدد --model و --year و --km (أو استخدم --list)")

    try:
        car = CarInput(
            model=args.model, year=args.year, km=args.km, spec=args.spec,
            condition=args.condition, accidents=args.accidents,
            service_history=args.service_history, owners=args.owners, trim=args.trim,
        )
        est = estimate_price(car, market)
    except ValueError as e:
        print(f"خطأ: {e}", file=sys.stderr)
        return 2

    if args.json:
        print(json.dumps(est.as_dict(), ensure_ascii=False, indent=2))
        return 0

    print()
    print(f"  {est.model}  موديل {args.year}  ({est.age} سنوات)")
    print(f"  {_fmt(args.km)} كم  |  مواصفات: {args.spec}  |  الحالة: {args.condition}")
    print("  " + "─" * 38)
    print(f"  السعر التقديري:  {_fmt(est.price)} {est.currency}")
    print(f"  المدى المتوقع:   {_fmt(est.low)} – {_fmt(est.high)} {est.currency}")
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
