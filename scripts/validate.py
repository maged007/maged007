"""
يقيس دقة المحرّك مقابل نقاط السوق الحقيقية (anchors) في data/market.json.
الإعلانات مجهولة الحالة، فنقارنها بشريحة "جيدة" (الوسطى) لأنها تمثّل متوسط السوق.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from pricing_engine import CarInput, estimate_price, find_model, list_models, load_market  # noqa: E402


def main() -> int:
    market = load_market()
    errors = []
    print(f"{'الموديل':<16}{'سنة':>6}{'كم':>9}{'حقيقي':>10}{'متوقع':>10}{'خطأ%':>8}")
    print("-" * 62)
    for key in list_models(market):
        _, _, m = find_model(market, key)
        for a in m.get("anchors", []):
            est = estimate_price(CarInput(
                model=key, year=a["year"], km=a["km"],
                spec=a.get("spec", "gcc"), trim=a.get("trim"),
                condition="good"), market)
            actual = a["price"]
            err = (est.price - actual) / actual * 100.0
            errors.append(abs(err))
            print(f"{m['name_en']:<16}{a['year']:>6}{a['km']:>9}"
                  f"{actual:>10}{est.price:>10}{err:>7.1f}%")
    mape = sum(errors) / len(errors)
    print("-" * 62)
    print(f"MAPE على نقاط التحقّق = {mape:.2f}%   (الهدف < 15%)")
    return 0 if mape < 15 else 1


if __name__ == "__main__":
    raise SystemExit(main())
