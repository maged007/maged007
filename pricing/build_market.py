#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
يولّد market/market_ads.json: 10 إعلانات خليجي + 10 وارد لكل فئة من الـ50
(= ~1000 إعلان) انطلاقاً من market/market_knowledge.json.

⚠️ الأرقام تقديرية معرفية عن سوق الإمارات (ليست إعلانات حيّة)، ومستقلة تماماً عن
   معاملات المحرّك في data/pricing_data.json — حتى يكون قياس الدقة حقيقياً لا دائرياً.
   استبدلها بإعلانات يدوية فعلية لقياس أدق.

كل إعلان: { brand, model, spec, year, km, condition, ad_price }
(نفس صيغة samples/market_samples.json)
"""

import json
import os
import random

HERE = os.path.dirname(__file__)
KNOW = os.path.join(HERE, "market", "market_knowledge.json")
OUT = os.path.join(HERE, "market", "market_ads.json")

random.seed(424242)
N_PER_SPEC = 10

COND_WEIGHTS = {
    "excellent": 0.16, "very_good": 0.34, "good": 0.30,
    "fair": 0.14, "needs_work": 0.06,
}


def km_adj(K, age, km):
    expected = max(age, 0) * K["baseline_per_year"]
    f = 1.0 - ((km - expected) / 10000.0) * K["step_per_10k"]
    return max(K["min"], min(K["max"], f))


def main():
    with open(KNOW, encoding="utf-8") as f:
        M = json.load(f)

    cur, base = M["current_year"], M["base_year"]
    K = M["km"]
    cond_delta = M["condition_delta"]
    gap = M["imported_gap"]
    conds = list(COND_WEIGHTS)
    cond_w = list(COND_WEIGHTS.values())

    rows = []
    for brand, models in M["trims"].items():
        for model, t in models.items():
            for spec in ("gcc", "imported"):
                spec_mult = 1.0 if spec == "gcc" else gap[brand]
                for _ in range(N_PER_SPEC):
                    # عمر الإعلان: من سنة حتى 9 سنوات (الوارد يميل أقدم قليلاً)
                    max_age = base - (base - 9)
                    age = random.randint(1, 9)
                    year = cur - age
                    km = int(age * random.randint(13000, 27000) / 1000) * 1000
                    cond = random.choices(conds, weights=cond_w)[0]

                    # سعر بيع واقعي ضمني من معرفة السوق (مستقل عن المحرّك)
                    sale = (
                        t["gcc_base"]
                        * (1.0 - t["annual_drop"]) ** max(age - 1, 0)
                        * km_adj(K, age, km)
                        * cond_delta[cond]
                        * spec_mult
                    )
                    sale *= random.uniform(0.92, 1.08)  # تشتت إعلانات السوق
                    # سعر الطلب في الإعلان = سعر البيع ÷ نسبة التفاوض، مقرّب
                    ad = int(round(sale / M["ad_to_sale_ratio"] / 500.0)) * 500
                    rows.append({
                        "brand": brand, "model": model, "spec": spec,
                        "year": year, "km": km, "condition": cond,
                        "ad_price": ad,
                    })

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump({
            "_note": "إعلانات تقديرية معرفية (مستقلة عن المحرّك). استبدلها بإعلانات يدوية فعلية.",
            "current_year": cur,
            "ad_to_sale_ratio": M["ad_to_sale_ratio"],
            "per_spec": N_PER_SPEC,
            "ads": rows,
        }, f, ensure_ascii=False, indent=2)
    print(f"كُتب {len(rows)} إعلان في {OUT}")


if __name__ == "__main__":
    main()
