#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
تقرير دقة المحرّك مقابل عيّنات السوق:
  - MdAPE (وسيط نسبة الخطأ المطلقة) و MAPE (المتوسط).
  - نسبة التقديرات داخل ±15% و ±20% من السوق.
  - تفصيل حسب البراند.
معيار القبول: متوسط/وسيط الخطأ < 15%.
"""

import os
import statistics

from engine import load_data, estimate
from calibrate import load_samples, target_price


def report():
    data = load_data()
    cur_year, samples = load_samples()

    rows = []
    for s in samples:
        age = cur_year - s["year"]
        est = estimate(data, s["brand"], s["model"], age, s["km"],
                       s["spec"], s["condition"])
        tgt = target_price(data, s)
        ape = abs(est - tgt) / tgt
        rows.append((s["brand"], ape))

    apes = [r[1] for r in rows]
    n = len(apes)
    within15 = sum(a <= 0.15 for a in apes) / n * 100
    within20 = sum(a <= 0.20 for a in apes) / n * 100

    print("=" * 48)
    print("        تقرير الدقة مقابل السوق")
    print("=" * 48)
    print(f"عدد العيّنات        : {n}")
    print(f"MdAPE (وسيط الخطأ)  : {statistics.median(apes)*100:.1f}%")
    print(f"MAPE  (متوسط الخطأ) : {statistics.mean(apes)*100:.1f}%")
    print(f"داخل ±15%           : {within15:.1f}%")
    print(f"داخل ±20%           : {within20:.1f}%")
    passed = statistics.median(apes) < 0.15
    print(f"معيار القبول (<15%) : {'✔ نجح' if passed else '✗ راجع المعايرة'}")

    print("\n— حسب البراند (MdAPE) —")
    by_brand = {}
    for b, a in rows:
        by_brand.setdefault(b, []).append(a)
    for b, a in sorted(by_brand.items(), key=lambda x: statistics.median(x[1])):
        print(f"  {b:11s}: {statistics.median(a)*100:5.1f}%   (ن={len(a)})")


if __name__ == "__main__":
    report()
