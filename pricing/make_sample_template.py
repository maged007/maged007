#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
مولّد عيّنات توضيحية (placeholder) لاختبار خط المعايرة من طرف لطرف.

⚠️ هذه أرقام تجريبية مُولّدة حول قيم المحرّك مع ضوضاء واقعية، لإثبات أن
   سكربتات المعايرة والدقة تعمل. استبدلها بأرقامك اليدوية الحقيقية:
   3–6 إعلانات لكل موديل (سنة، كم، فئة، خليجي/وارد، سعر الطلب) من
   دوبيزل/دوبيكارز/كارسويتش/ياللاموتور — مرجعية فقط، بلا سحب آلي.

صيغة كل عيّنة في samples/market_samples.json:
  brand, model, year, km, spec, condition, ad_price
  (ad_price = سعر الطلب في الإعلان ؛ المحرّك يقارَن مع ad_price × 0.88)
"""

import json
import os
import random

from engine import load_data, estimate

random.seed(20260615)
CURRENT_YEAR = 2026

OUT = os.path.join(os.path.dirname(__file__), "samples", "market_samples.json")


def main():
    data = load_data()
    ratio = data["_meta"]["ad_to_sale_ratio"]
    rows = []

    for brand, bobj in data["brands"].items():
        for model in bobj["models"]:
            for _ in range(random.randint(3, 5)):
                age = random.randint(1, 9)
                year = CURRENT_YEAR - age
                km = int(age * random.randint(14000, 26000) / 1000) * 1000
                spec = random.choices(["gcc", "imported"], weights=[0.8, 0.2])[0]
                condition = random.choices(
                    ["excellent", "very_good", "good", "fair", "needs_work"],
                    weights=[0.18, 0.34, 0.30, 0.13, 0.05],
                )[0]
                # السعر الواقعي للبيع = تقدير المحرّك مع ضوضاء سوقية ±12%
                sale = estimate(data, brand, model, age, km, spec, condition)
                sale *= random.uniform(0.88, 1.12)
                ad_price = int(round(sale / ratio / 500.0)) * 500
                rows.append({
                    "brand": brand,
                    "model": model,
                    "year": year,
                    "km": km,
                    "spec": spec,
                    "condition": condition,
                    "ad_price": ad_price,
                })

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump({
            "_note": "عيّنات توضيحية مُولّدة — استبدلها بأرقام يدوية حقيقية.",
            "current_year": CURRENT_YEAR,
            "samples": rows,
        }, f, ensure_ascii=False, indent=2)
    print(f"كُتبت {len(rows)} عيّنة في {OUT}")


if __name__ == "__main__":
    main()
