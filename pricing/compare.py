#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
يقارن تقدير المحرّك بسوق الإمارات (market/market_ads.json):
  - يقدّر كل إعلان على حدة ببياناته (سنة/كم/مواصفة/حالة).
  - السعر المستهدف لكل إعلان = ad_price × 0.88 (قاعدة المشروع الموحّدة).
  - لكل فئة (براند، موديل، مواصفة): تقدير المحرّك التمثيلي = وسيط تقديرات إعلاناتها،
    الرنج = ±نسبة الفئة حول التقدير، وسيط السوق، والدقة (MdAPE، %±15، %داخل الرنج).
  - يطبع 10 جداول (براند لكل جدول) + ملخّص، ويكتب reports/comparison_report.md و .json
"""

import json
import os
import statistics

from engine import load_data, estimate

HERE = os.path.dirname(__file__)
ADS = os.path.join(HERE, "market", "market_ads.json")
REPORT_MD = os.path.join(HERE, "reports", "comparison_report.md")
REPORT_JSON = os.path.join(HERE, "reports", "comparison.json")

AD_TO_SALE = 0.88
SPEC_LABEL = {"gcc": "خليجي", "imported": "وارد"}

# فئات عالية القيمة تأخذ رنجاً أوسع
WIDE_TRIMS = {("mercedes", "s_class"), ("mercedes", "g_class"),
              ("bmw", "series7"), ("lexus", "lx")}


def segment_range_pct(brand, model, mtype):
    """نصف عرض الرنج كنسبة، حسب الفئة (قرار خبرة)."""
    if (brand, model) in WIDE_TRIMS:
        return 0.13
    if brand in ("mercedes", "bmw", "lexus") or mtype == "coupe":
        return 0.12
    if mtype in ("suv", "pickup"):
        return 0.10
    return 0.08  # سيدان/اقتصادي


def fmt(n):
    return f"{int(round(n)):,}"


def main():
    data = load_data()
    with open(ADS, encoding="utf-8") as f:
        blob = json.load(f)
    cur_year, ads = blob["current_year"], blob["ads"]

    # تجميع حسب الفئة (براند، موديل، مواصفة)
    cats = {}
    for a in ads:
        cats.setdefault((a["brand"], a["model"], a["spec"]), []).append(a)

    report = {"categories": [], "by_brand": {}, "overall": {}}
    all_ape = []
    cat_in_range = []  # هل وسيط السوق داخل رنج الفئة؟

    brand_order = list(data["brands"].keys())
    md = ["# تقرير مقارنة المحرّك مقابل السوق (الإمارات)\n",
          "> أرقام السوق تقديرية معرفية مستقلة عن المحرّك (بديلة عن إعلانات حيّة). "
          "كل فئة = 10 إعلانات خليجي + 10 وارد. التقدير لكل إعلان على حدة، "
          "والرنج حسب الفئة.\n"]

    for brand in brand_order:
        bobj = data["brands"][brand]
        md.append(f"\n## {bobj['label']}\n")
        md.append("| الموديل | المواصفة | تقدير المحرّك | الرنج (من–إلى) | "
                  "وسيط السوق | الخطأ (MdAPE) | داخل ±15% | داخل الرنج |")
        md.append("|---|---|--:|--:|--:|--:|--:|:--:|")

        brand_ape = []
        for model, mobj in bobj["models"].items():
            mtype = mobj.get("type", "sedan")
            rpct = segment_range_pct(brand, model, mtype)
            for spec in ("gcc", "imported"):
                group = cats.get((brand, model, spec), [])
                if not group:
                    continue
                eng_list, tgt_list, ape_list = [], [], []
                for a in group:
                    age = cur_year - a["year"]
                    e = estimate(data, brand, model, age, a["km"],
                                 a["spec"], a["condition"])
                    t = a["ad_price"] * AD_TO_SALE
                    eng_list.append(e)
                    tgt_list.append(t)
                    ape_list.append(abs(e - t) / t)

                eng_ref = statistics.median(eng_list)
                mkt_med = statistics.median(tgt_list)
                lo, hi = eng_ref * (1 - rpct), eng_ref * (1 + rpct)
                mdape = statistics.median(ape_list)
                within15 = sum(x <= 0.15 for x in ape_list) / len(ape_list)
                market_in_range = lo <= mkt_med <= hi

                brand_ape.extend(ape_list)
                all_ape.extend(ape_list)
                cat_in_range.append(market_in_range)

                flag = "✅" if market_in_range else "⚠️"
                md.append(
                    f"| {mobj['label']} | {SPEC_LABEL[spec]} | {fmt(eng_ref)} | "
                    f"{fmt(lo)}–{fmt(hi)} | {fmt(mkt_med)} | {mdape*100:.1f}% | "
                    f"{within15*100:.0f}% | {flag} |")

                report["categories"].append({
                    "brand": brand, "model": model, "spec": spec,
                    "engine_estimate": round(eng_ref),
                    "range_low": round(lo), "range_high": round(hi),
                    "range_pct": rpct, "market_median": round(mkt_med),
                    "mdape": round(mdape, 4),
                    "within_15pct": round(within15, 3),
                    "market_in_range": market_in_range,
                    "n_ads": len(group),
                })

        bmd = statistics.median(brand_ape)
        report["by_brand"][brand] = {
            "mdape": round(bmd, 4),
            "within_15pct": round(sum(x <= 0.15 for x in brand_ape)/len(brand_ape), 3),
        }
        md.append(f"\n**ملخّص {bobj['label']}**: MdAPE = {bmd*100:.1f}% · "
                  f"داخل ±15% = {sum(x<=0.15 for x in brand_ape)/len(brand_ape)*100:.0f}%")

    overall = {
        "n_ads": len(all_ape),
        "mdape": round(statistics.median(all_ape), 4),
        "mape": round(statistics.mean(all_ape), 4),
        "within_15pct": round(sum(x <= 0.15 for x in all_ape)/len(all_ape), 3),
        "within_20pct": round(sum(x <= 0.20 for x in all_ape)/len(all_ape), 3),
        "n_categories": len(cat_in_range),
        "categories_market_in_range": round(sum(cat_in_range)/len(cat_in_range), 3),
    }
    report["overall"] = overall

    summary = (
        f"\n---\n## الملخّص العام\n"
        f"- عدد الإعلانات: **{overall['n_ads']}**\n"
        f"- MdAPE (وسيط الخطأ): **{overall['mdape']*100:.1f}%**\n"
        f"- MAPE (متوسط الخطأ): **{overall['mape']*100:.1f}%**\n"
        f"- داخل ±15%: **{overall['within_15pct']*100:.0f}%** · "
        f"داخل ±20%: **{overall['within_20pct']*100:.0f}%**\n"
        f"- الفئات التي يقع وسيط سوقها داخل الرنج: "
        f"**{overall['categories_market_in_range']*100:.0f}%** "
        f"من {overall['n_categories']} فئة\n"
    )
    md.append(summary)

    os.makedirs(os.path.dirname(REPORT_MD), exist_ok=True)
    with open(REPORT_MD, "w", encoding="utf-8") as f:
        f.write("\n".join(md) + "\n")
    with open(REPORT_JSON, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print("\n".join(md))
    print(f"\n📄 كُتب التقرير: {REPORT_MD}")


if __name__ == "__main__":
    main()
