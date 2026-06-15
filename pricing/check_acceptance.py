#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""يتحقق من معايير القبول الأربعة ويطبع نجاح/فشل لكل معيار."""

import statistics
from engine import load_data, estimate, brand_retention
from calibrate import load_samples, target_price


def main():
    data = load_data()
    ok = True

    # 1) فرق خليجي/وارد كبير (~35%)
    gcc = estimate(data, "toyota", "camry", 3, 60000, "gcc", "excellent")
    imp = estimate(data, "toyota", "camry", 3, 60000, "imported", "excellent")
    drop = (gcc - imp) / gcc * 100
    p1 = 30 <= drop <= 40
    ok &= p1
    print(f"[{'✔' if p1 else '✗'}] فرق خليجي/وارد = {drop:.0f}% (المطلوب ~35%)")

    # 2) تويوتا/لكزس تحتفظ أعلى من نيسان/فورد عند نفس العمر
    age = 5
    hi = min(brand_retention(data, "toyota", age), brand_retention(data, "lexus", age))
    lo = max(brand_retention(data, "nissan", age), brand_retention(data, "ford", age))
    p2 = hi > lo
    ok &= p2
    print(f"[{'✔' if p2 else '✗'}] احتفاظ تويوتا/لكزس@{age}س ({hi:.2f}) > نيسان/فورد ({lo:.2f})")

    # 3) SUV المطلوبة أغلى من سيدان نفس البراند (عامل طلب >100%)
    suv = data["brands"]["toyota"]["models"]["prado"]["demand_factor"]
    sedan = data["brands"]["toyota"]["models"]["corolla"]["demand_factor"]
    p3 = suv > 1.0 and suv > sedan
    ok &= p3
    print(f"[{'✔' if p3 else '✗'}] عامل طلب برادو(SUV)={suv} > كورولا(سيدان)={sedan}")

    # 4) متوسط الخطأ < 15%
    cur_year, samples = load_samples()
    apes = []
    for s in samples:
        a = cur_year - s["year"]
        est = estimate(data, s["brand"], s["model"], a, s["km"], s["spec"], s["condition"])
        apes.append(abs(est - target_price(data, s)) / target_price(data, s))
    md = statistics.median(apes)
    p4 = md < 0.15
    ok &= p4
    print(f"[{'✔' if p4 else '✗'}] MdAPE = {md*100:.1f}% (المطلوب <15%)")

    print("\n" + ("جميع المعايير ✔ نجحت" if ok else "بعض المعايير ✗ فشلت"))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
