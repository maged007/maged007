#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
يحوّل reports/comparison.json إلى صفحة web/report.html مستقلة (RTL، البيانات مدمجة).
شغّله بعد compare.py:  python3 build_report_html.py
"""

import json
import os

HERE = os.path.dirname(__file__)
SRC = os.path.join(HERE, "reports", "comparison.json")
DATA = os.path.join(HERE, "data", "pricing_data.json")
OUT = os.path.join(HERE, "web", "report.html")

SPEC = {"gcc": "خليجي", "imported": "وارد"}


def fmt(n):
    return f"{int(round(n)):,}"


def main():
    with open(SRC, encoding="utf-8") as f:
        rep = json.load(f)
    with open(DATA, encoding="utf-8") as f:
        d = json.load(f)

    blabel = {k: v["label"] for k, v in d["brands"].items()}
    mlabel = {(b, m): mo["label"]
              for b, bo in d["brands"].items()
              for m, mo in bo["models"].items()}

    o = rep["overall"]
    parts = ["""<!DOCTYPE html><html lang="ar" dir="rtl"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>تقرير المحرّك مقابل السوق</title><style>
:root{--bg:#0b1220;--card:#16213a;--line:#26324d;--txt:#e8edf7;--muted:#93a1bf;
--ok:#23c486;--warn:#f4a261}
*{box-sizing:border-box}body{margin:0;font-family:system-ui,Tahoma,Arial,sans-serif;
background:linear-gradient(160deg,#0b1220,#101b30);color:var(--txt);padding:16px}
.wrap{max-width:920px;margin:0 auto}h1{font-size:20px;text-align:center}
.note{color:var(--warn);font-size:12px;text-align:center;margin-bottom:14px}
.kpis{display:flex;gap:10px;flex-wrap:wrap;justify-content:center;margin:14px 0}
.kpi{background:var(--card);border:1px solid var(--line);border-radius:12px;
padding:10px 16px;text-align:center;min-width:120px}
.kpi b{display:block;font-size:22px;color:var(--ok)}.kpi span{color:var(--muted);font-size:12px}
h2{font-size:16px;margin:22px 0 6px;border-right:3px solid var(--ok);padding-right:8px}
table{width:100%;border-collapse:collapse;font-size:13px;background:var(--card);
border-radius:10px;overflow:hidden}th,td{padding:7px 8px;border-bottom:1px solid var(--line);
text-align:center}th{color:var(--muted);font-weight:600;background:#10182c}
td.r{text-align:left;font-variant-numeric:tabular-nums}
.ok{color:var(--ok)}.warn{color:var(--warn)}</style></head><body><div class="wrap">
<h1>تقرير دقة المحرّك مقابل السوق 🇦🇪</h1>
<div class="note">⚠️ أرقام السوق تقديرية معرفية مستقلة عن المحرّك (بديلة عن إعلانات حيّة) — كل فئة 10 خليجي + 10 وارد</div>
<div class="kpis">"""]
    parts.append(f'<div class="kpi"><b>{o["mdape"]*100:.1f}%</b><span>MdAPE</span></div>')
    parts.append(f'<div class="kpi"><b>{o["within_15pct"]*100:.0f}%</b><span>داخل ±15%</span></div>')
    parts.append(f'<div class="kpi"><b>{o["within_20pct"]*100:.0f}%</b><span>داخل ±20%</span></div>')
    parts.append(f'<div class="kpi"><b>{o["categories_market_in_range"]*100:.0f}%</b><span>فئات داخل الرنج</span></div>')
    parts.append(f'<div class="kpi"><b>{o["n_ads"]}</b><span>إعلان</span></div>')
    parts.append("</div>")

    # تجميع الفئات حسب البراند بترتيب ملف البيانات
    by_brand = {}
    for c in rep["categories"]:
        by_brand.setdefault(c["brand"], []).append(c)

    for brand in d["brands"]:
        cats = by_brand.get(brand, [])
        if not cats:
            continue
        bm = rep["by_brand"][brand]
        parts.append(f'<h2>{blabel[brand]} — MdAPE {bm["mdape"]*100:.1f}% · '
                     f'±15% {bm["within_15pct"]*100:.0f}%</h2>')
        parts.append("<table><tr><th>الموديل</th><th>المواصفة</th><th>تقدير المحرّك</th>"
                     "<th>الرنج</th><th>وسيط السوق</th><th>الخطأ</th><th>±15%</th><th>الحالة</th></tr>")
        for c in cats:
            cls = "ok" if c["market_in_range"] else "warn"
            flag = "✅" if c["market_in_range"] else "⚠️"
            parts.append(
                f'<tr><td>{mlabel[(brand,c["model"])]}</td><td>{SPEC[c["spec"]]}</td>'
                f'<td class="r">{fmt(c["engine_estimate"])}</td>'
                f'<td class="r">{fmt(c["range_low"])}–{fmt(c["range_high"])}</td>'
                f'<td class="r">{fmt(c["market_median"])}</td>'
                f'<td class="{cls}">{c["mdape"]*100:.1f}%</td>'
                f'<td>{c["within_15pct"]*100:.0f}%</td><td>{flag}</td></tr>')
        parts.append("</table>")

    parts.append("</div></body></html>")

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        f.write("".join(parts))
    print(f"كُتب {OUT}")


if __name__ == "__main__":
    main()
