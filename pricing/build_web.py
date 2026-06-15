#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
يولّد web/data.js من data/pricing_data.json حتى تبقى الـJSON المصدر الوحيد،
وتعمل الواجهة بالنقر المزدوج (file://) بدون سيرفر.
شغّله بعد أي تعديل على ملف البيانات:  python3 build_web.py
"""

import json
import os

HERE = os.path.dirname(__file__)
SRC = os.path.join(HERE, "data", "pricing_data.json")
OUT = os.path.join(HERE, "web", "data.js")


def main():
    with open(SRC, encoding="utf-8") as f:
        data = json.load(f)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        f.write("// مولّد آلياً من data/pricing_data.json — لا تعدّله يدوياً.\n")
        f.write("window.PRICING_DATA = ")
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write(";\n")
    print(f"كُتب {OUT}")


if __name__ == "__main__":
    main()
