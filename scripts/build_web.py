#!/usr/bin/env python3
"""
يحقن بيانات السوق المعايرة (data/nissan_market.json) داخل صفحة الويب
بين العلامتين، عشان تفضل البيانات مصدر واحد بين محرّك Python والواجهة.

تشغيل:
    python3 scripts/build_web.py
"""
import json
import os
import re

ROOT = os.path.join(os.path.dirname(__file__), "..")
DATA = os.path.join(ROOT, "data", "market.json")
WEB = os.path.join(ROOT, "web", "index.html")

START = "/* __MARKET_DATA_START__ */"
END = "/* __MARKET_DATA_END__ */"


def main() -> int:
    with open(DATA, "r", encoding="utf-8") as f:
        data = json.load(f)
    payload = json.dumps(data, ensure_ascii=False, indent=2)

    with open(WEB, "r", encoding="utf-8") as f:
        html = f.read()

    block = f"{START}\nconst MARKET = {payload};\n{END}"
    pattern = re.compile(re.escape(START) + r".*?" + re.escape(END), re.DOTALL)
    if not pattern.search(html):
        raise SystemExit("لم يتم العثور على علامات البيانات في web/index.html")
    html = pattern.sub(lambda _m: block, html)

    with open(WEB, "w", encoding="utf-8") as f:
        f.write(html)
    n_models = sum(len(b.get("models", {})) for b in data.get("brands", {}).values())
    print(f"تم حقن بيانات {n_models} موديل في {os.path.relpath(WEB, ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
