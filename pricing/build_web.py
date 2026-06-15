#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
يحقن data/pricing_data.json داخل web/template.html ويُنتج web/index.html
كملف HTML واحد *مستقل* — البيانات مدمجة، يفتح بنقرة مزدوجة بأي مكان بلا سيرفر
وبلا ملفات مجاورة. الـJSON يبقى المصدر الوحيد.
شغّله بعد أي تعديل على ملف البيانات:  python3 build_web.py
"""

import json
import os

HERE = os.path.dirname(__file__)
SRC = os.path.join(HERE, "data", "pricing_data.json")
TPL = os.path.join(HERE, "web", "template.html")
OUT = os.path.join(HERE, "web", "index.html")
PLACEHOLDER = "/*__PRICING_DATA__*/"


def main():
    with open(SRC, encoding="utf-8") as f:
        data = json.load(f)
    with open(TPL, encoding="utf-8") as f:
        html = f.read()

    if PLACEHOLDER not in html:
        raise SystemExit(f"لم يُعثر على العلامة {PLACEHOLDER} في {TPL}")

    inline = "window.PRICING_DATA = " + json.dumps(data, ensure_ascii=False) + ";"
    html = html.replace(PLACEHOLDER, inline)

    with open(OUT, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"كُتب ملف مستقل: {OUT}")


if __name__ == "__main__":
    main()
