"""
يقيس دقة المحرّك مقابل نقاط السوق الحقيقية (anchors) المخزّنة في ملف البيانات.
يطبع لكل نقطة: المتوقع مقابل الحقيقي ونسبة الخطأ، ثم MAPE الإجمالي.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from pricing_engine import CarInput, estimate_price, load_market  # noqa: E402


def main() -> int:
    market = load_market()
    errors = []
    print(f"{'الموديل':<16}{'سنة':>6}{'كم':>9}{'حقيقي':>10}{'متوقع':>10}{'خطأ%':>8}  ملاحظة")
    print("-" * 70)
    for key, spec in market["models"].items():
        for a in spec.get("anchors", []):
            car = CarInput(model=key, year=a["year"], km=a["km"], spec="gcc",
                           condition="good", service_history="partial", owners=2)
            est = estimate_price(car, market)
            actual = a["price"]
            err = (est.price - actual) / actual * 100.0
            in_scope = a.get("calibration", True)
            if in_scope:
                errors.append(abs(err))
            flag = "" if in_scope else "(خارج النطاق)"
            print(f"{spec['name_en']:<16}{a['year']:>6}{a['km']:>9}"
                  f"{actual:>10}{est.price:>10}{err:>7.1f}%  {flag}")
    mape = sum(errors) / len(errors)
    print("-" * 70)
    print(f"MAPE (متوسط نسبة الخطأ المطلق) = {mape:.2f}%  على {len(errors)} نقطة معايرة")
    print("الهدف: < 15%")
    return 0 if mape < 15 else 1


if __name__ == "__main__":
    raise SystemExit(main())
