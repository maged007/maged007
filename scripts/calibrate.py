"""
معايرة موديل من داتا حقيقية مصدّرة من تطبيق Automark.

الخطوات:
  1) قراءة جدول الـ markdown المصدّر.
  2) تنظيف قوي: استخراج السنة/الفئة/المواصفات/الكيلومترات + إزالة الأسعار والكيلومترات الشاذة.
  3) انحدار log-linear (حل OLS يدوي بدون مكتبات) للسعر على:
       العمر + الكيلومترات + (وارد مقابل خليجي) + الفئة.
  4) ترجمة معاملات الانحدار إلى باراميترات محرّك التسعير.
  5) تقرير قابل للقراءة + إرجاع الباراميترات المعايرة.

تشغيل:
    python3 scripts/calibrate.py altima data/raw/export_nissan_altima.md
"""
from __future__ import annotations

import math
import re
import statistics
import sys
from dataclasses import dataclass
from datetime import date
from typing import Optional

# إعدادات كل موديل (سعر الجديد التقريبي + حدود سعر منطقية للتنظيف)
MODEL_CONFIG = {
    "altima": {"msrp": 100000, "default_trim": "SV",
               "price_min": 5000, "price_max": 130000,
               "trim_tokens": ["Platinum", "SR", "SL", "SV", "S"]},
}

CURRENT_YEAR = date.today().year


# ---------------------------------------------------------------------------
# 1) قراءة الجدول
# ---------------------------------------------------------------------------
def parse_export(path: str) -> list[dict]:
    rows = []
    with open(path, "r", encoding="utf-8") as f:
        lines = f.readlines()
    for ln in lines:
        if "|" not in ln:
            continue
        cells = [c.strip() for c in ln.strip().strip("|").split("|")]
        # نتعرف على صفوف البيانات: العمود الأول رقم، وفيه "Nissan" في الاسم
        if len(cells) < 6:
            continue
        if not cells[0].isdigit():
            continue
        name = cells[1]
        if "Nissan" not in name and "نيسان" not in name:
            continue
        rows.append({
            "name": name,
            "price_raw": cells[3],
            "km_raw": cells[4],
            "spec_raw": cells[5],
        })
    return rows


# ---------------------------------------------------------------------------
# 2) التنظيف والاستخراج
# ---------------------------------------------------------------------------
@dataclass
class Listing:
    year: int
    age: int
    price: float
    km: Optional[int]
    spec: str          # gcc | import
    trim: str          # S | SV | SL | SR | Platinum | unknown


def _extract_year(name: str) -> Optional[int]:
    cands = [int(y) for y in re.findall(r"(?:19[5-9]\d|20[0-2]\d)", name)]
    cands = [y for y in cands if 2003 <= y <= CURRENT_YEAR + 1]
    if not cands:
        return None
    # الأكثر تكراراً ثم الأصغر (عشان التكرارات زي "2017 2017")
    return statistics.mode(cands) if len(set(cands)) == 1 else min(cands, key=lambda y: (-cands.count(y), y))


def _extract_trim(name: str, tokens: list[str]) -> str:
    low = " " + name.lower() + " "
    if "platinum" in low:
        return "Platinum"
    for t in ["sr", "sl", "sv"]:
        if re.search(r"(?<![a-z])" + t + r"(?![a-z])", low):
            return t.upper()
    if re.search(r"(?<![a-z])s(?![a-z])", low) or "basic" in low:
        return "S"
    return "unknown"


def _extract_km(raw: str) -> Optional[int]:
    digits = re.sub(r"[^\d]", "", raw)
    if not digits:
        return None
    km = int(digits)
    if km <= 0 or km > 400_000:   # 0 أو مبالغ فيه = مجهول
        return None
    return km


def clean(rows: list[dict], cfg: dict) -> tuple[list[Listing], dict]:
    out, stats = [], {"raw": len(rows), "no_year": 0, "bad_price": 0}
    for r in rows:
        year = _extract_year(r["name"])
        if year is None:
            stats["no_year"] += 1
            continue
        try:
            price = float(re.sub(r"[^\d.]", "", r["price_raw"]))
        except ValueError:
            stats["bad_price"] += 1
            continue
        if not (cfg["price_min"] <= price <= cfg["price_max"]):
            stats["bad_price"] += 1
            continue
        spec = "gcc" if "خليج" in r["spec_raw"] else "import"
        trim = _extract_trim(r["name"], cfg["trim_tokens"])
        km = _extract_km(r["km_raw"])
        age = max(0, CURRENT_YEAR - year)
        out.append(Listing(year, age, price, km, spec, trim))
    stats["after_basic_clean"] = len(out)
    return out, stats


# ---------------------------------------------------------------------------
# 3) انحدار خطّي (OLS) بحل يدوي
# ---------------------------------------------------------------------------
def ols(X: list[list[float]], y: list[float]) -> list[float]:
    """يحل beta = (X'X)^-1 X'y عبر حذف غاوس-جوردان."""
    n, p = len(X), len(X[0])
    # X'X و X'y
    XtX = [[sum(X[r][i] * X[r][j] for r in range(n)) for j in range(p)] for i in range(p)]
    Xty = [sum(X[r][i] * y[r] for r in range(n)) for i in range(p)]
    # مصفوفة موسّعة
    M = [XtX[i] + [Xty[i]] for i in range(p)]
    for col in range(p):
        piv = max(range(col, p), key=lambda r: abs(M[r][col]))
        M[col], M[piv] = M[piv], M[col]
        d = M[col][col]
        if abs(d) < 1e-12:
            d = 1e-12
        M[col] = [v / d for v in M[col]]
        for r in range(p):
            if r != col:
                f = M[r][col]
                M[r] = [M[r][k] - f * M[col][k] for k in range(p + 1)]
    return [M[i][p] for i in range(p)]


def build_design(data: list[Listing], trims: list[str]):
    """يبني مصفوفة الخصائص: ثابت + عمر + كم/10000 + وارد + dummies للفئات (الأساس SV)."""
    base_trim = "SV"
    dummy_trims = [t for t in trims if t != base_trim] + ["unknown"]
    X, y = [], []
    for d in data:
        row = [1.0, float(d.age), d.km / 10000.0, 1.0 if d.spec == "import" else 0.0]
        for t in dummy_trims:
            row.append(1.0 if d.trim == t else 0.0)
        X.append(row)
        y.append(math.log(d.price))
    cols = ["const", "age", "km10k", "import"] + [f"trim_{t}" for t in dummy_trims]
    return X, y, cols


def robust_fit(data: list[Listing], trims: list[str], passes: int = 2):
    """يحذف الشواذ في فضاء اللوغاريتم عبر تكرارات ثم يعيد التوفيق."""
    work = [d for d in data if d.km is not None]
    coefs = cols = None
    for _ in range(passes + 1):
        X, y, cols = build_design(work, trims)
        coefs = ols(X, y)
        resid = [y[i] - sum(coefs[j] * X[i][j] for j in range(len(coefs))) for i in range(len(y))]
        sd = statistics.pstdev(resid) or 1e-9
        keep = [work[i] for i in range(len(work)) if abs(resid[i]) <= 2.5 * sd]
        if len(keep) == len(work):
            break
        work = keep
    return coefs, cols, work


# ---------------------------------------------------------------------------
# 4) ترجمة المعاملات إلى باراميترات المحرّك
# ---------------------------------------------------------------------------
def calibrate(model_key: str, path: str, verbose: bool = True) -> dict:
    cfg = MODEL_CONFIG[model_key]
    rows = parse_export(path)
    data, stats = clean(rows, cfg)
    coefs, cols, used = robust_fit(data, cfg["trim_tokens"])
    cmap = dict(zip(cols, coefs))

    # متوسط كم سنوي فعلي من الداتا
    kms = [d.km / d.age for d in used if d.age >= 1 and d.km]
    kpy = int(round(statistics.median(kms) / 1000) * 1000) if kms else 20000

    age_coef = cmap["age"]
    km_coef = cmap["km10k"]                     # سالب
    R = math.exp(age_coef + km_coef * (kpy / 10000.0))   # الاحتفاظ السنوي (عند الكم المتوقع)
    pct_per_10k = round(-km_coef, 4)            # نسبة التغيّر لكل 10 آلاف كم
    import_factor = round(math.exp(cmap["import"]), 3)

    # القيمة عند العمر صفر/واحد (خليجي، فئة SV، كم متوقع) لاشتقاق احتفاظ السنة الأولى
    intercept = cmap["const"]
    base_age0 = math.exp(intercept)             # السعر المتوقع عند عمر 0، كم 0، SV، خليجي
    msrp = cfg["msrp"]
    year1_ret = round(R * base_age0 / msrp, 4)

    # معاملات الفئات (نسبةً إلى SV) — بما فيها "unknown" للإعلانات بدون فئة
    trim_mults = {"SV": 1.0}
    for t in cfg["trim_tokens"] + ["unknown"]:
        if t == "SV":
            continue
        trim_mults[t] = round(math.exp(cmap.get(f"trim_{t}", 0.0)), 3)

    floor = int(round(sorted(d.price for d in used)[max(0, len(used) // 20)] / 500) * 500)

    params = {
        "msrp": msrp,
        "year1_retention": year1_ret,
        "annual_retention": round(R, 4),
        "floor": floor,
        "expected_km_per_year": kpy,
        "default_trim": "SV",
        "trims": trim_mults,
        "import_factor": import_factor,
        "pct_per_10k": pct_per_10k,
    }

    if verbose:
        _report(model_key, stats, data, used, params, cmap)
    return {"params": params, "used": used, "all_clean": data, "coefs": cmap, "stats": stats}


# ---------------------------------------------------------------------------
# تقرير
# ---------------------------------------------------------------------------
def _report(model_key, stats, data, used, params, cmap):
    print("=" * 64)
    print(f"  معايرة موديل: {model_key.upper()}  من داتا Automark الحقيقية")
    print("=" * 64)
    print(f"  صفوف خام: {stats['raw']}  |  بدون سنة: {stats['no_year']}  |  "
          f"سعر غير صالح: {stats['bad_price']}")
    print(f"  بعد التنظيف الأساسي: {stats['after_basic_clean']}  |  "
          f"المستخدَم في الانحدار (بعد حذف الشواذ): {len(used)}")
    print("-" * 64)

    # متوسط السعر (median) لكل سنة
    by_year = {}
    for d in data:
        by_year.setdefault(d.year, []).append(d.price)
    print("  وسيط السعر الفعلي حسب السنة (كل المواصفات):")
    for yr in sorted(by_year, reverse=True):
        ps = by_year[yr]
        print(f"    {yr}:  {int(statistics.median(ps)):>7,} درهم   (عدد: {len(ps)})")
    print("-" * 64)

    print("  النتائج المستخلصة من الداتا:")
    print(f"    • الإهلاك السنوي  (الاحتفاظ): {params['annual_retention']*100:.1f}%  "
          f"→ تفقد ~{(1-params['annual_retention'])*100:.1f}% كل سنة")
    print(f"    • سقطة السنة الأولى (احتفاظ): {params['year1_retention']*100:.1f}%")
    print(f"    • أثر الكيلومترات: ~{params['pct_per_10k']*100:.2f}% لكل 10,000 كم")
    print(f"    • وارد مقابل خليجي: {params['import_factor']:.0%}  "
          f"(الوارد أرخص بـ ~{(1-params['import_factor'])*100:.0f}%)")
    print(f"    • متوسط كم سنوي في الداتا: {params['expected_km_per_year']:,} كم")
    print(f"    • أرضية السعر (5%): {params['floor']:,} درهم")
    print("    • علاوة الفئات (نسبةً إلى SV):")
    for t, m in params["trims"].items():
        print(f"         {t:<10} ×{m}")
    print("=" * 64)


def predict(params: dict, d: Listing) -> float:
    if d.age <= 0:
        base = params["msrp"]
    else:
        base = params["msrp"] * params["year1_retention"] * params["annual_retention"] ** (d.age - 1)
    base *= params["trims"].get(d.trim, 1.0)
    if d.km is not None:
        exp_km = params["expected_km_per_year"] * d.age
        adj = -params["pct_per_10k"] * ((d.km - exp_km) / 10000.0)
        adj = max(-0.30, min(0.12, adj))
        base *= (1 + adj)
    if d.spec == "import":
        base *= params["import_factor"]
    return max(base, params["floor"])


def evaluate(params: dict, data: list[Listing]) -> dict:
    """يقيس خطأ المحرّك المعاير مقابل الإعلانات النظيفة (MAPE + MdAPE)."""
    errs = sorted(abs(predict(params, d) - d.price) / d.price for d in data)
    mape = sum(errs) / len(errs)
    mdape = statistics.median(errs)
    within15 = sum(1 for e in errs if e <= 0.15) / len(errs)
    return {"mape": mape, "mdape": mdape, "within15": within15, "n": len(errs)}


if __name__ == "__main__":
    model_key = sys.argv[1] if len(sys.argv) > 1 else "altima"
    path = sys.argv[2] if len(sys.argv) > 2 else "data/raw/export_nissan_altima.md"
    res = calibrate(model_key, path)
    m = evaluate(res["params"], res["used"])
    print(f"\n  دقة المحرّك المعاير مقابل {m['n']} إعلان (المجموعة النظيفة):")
    print(f"  MdAPE (الخطأ الوسيط) = {m['mdape']*100:.2f}%   ← الأدل على السيارة النموذجية")
    print(f"  MAPE  (متوسط الخطأ)  = {m['mape']*100:.2f}%")
    print(f"  نسبة التقديرات ضمن ±15% من السعر الحقيقي = {m['within15']*100:.0f}%")
