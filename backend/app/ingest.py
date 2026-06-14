"""توصيل المصدر الحي (Scraper / API) وتحديث market_stats.json تلقائياً.

⚠️ مهم: مواقع الإعلانات (Dubizzle / DubiCars ...) تحمي صفحاتها ضد البوتات
(Cloudflare ...). لتشغيل السحب فعلياً على سيرفرك تحتاج أحد الخيارات:
  1) بروكسي/متصفّح آلي يتجاوز الحماية (ScraperAPI / Bright Data / Playwright).
  2) API بيانات سيارات للإمارات (أنظف وأقل صيانة).

هذا الملف يوفّر:
  - واجهة موحّدة Listing + ProviderالبياناتBase يسهل عليك توصيل أي مصدر.
  - دالة recompute_stats() تحوّل الإعلانات الخام إلى إحصاءات (median/low/high).
  - مزوّد مثال HttpListingProvider يوضّح الشكل المطلوب (يحتاج مفتاح بروكسي).

شغّل التحديث:
    python -m app.ingest
"""

from __future__ import annotations

import json
import statistics
from dataclasses import dataclass, asdict
from datetime import date
from pathlib import Path
from typing import Iterable, Protocol

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


@dataclass
class Listing:
    brand_id: str
    model_id: str
    trim_id: str
    year: int
    km: int
    price: float
    region: str = "gcc"
    source: str = "unknown"


class ListingProvider(Protocol):
    """أي مصدر بيانات لازم يطبّق الدالة دي."""

    def fetch(self, brand_id: str, model_id: str) -> Iterable[Listing]:
        ...


class HttpListingProvider:
    """مثال هيكلي لمزوّد عبر HTTP/بروكسي.

    استبدل _fetch_raw بنداء البروكسي/الـ API الفعلي على سيرفرك، ثم حوّل
    النتيجة إلى كائنات Listing. التحليل (parsing) يعتمد على شكل المصدر.
    """

    def __init__(self, proxy_url: str | None = None, api_key: str | None = None):
        self.proxy_url = proxy_url
        self.api_key = api_key

    def _fetch_raw(self, brand_id: str, model_id: str) -> list[dict]:
        # TODO على سيرفرك: نفّذ النداء الفعلي.
        #   مثال مع بروكسي:
        #   import requests
        #   url = f"https://www.dubicars.com/uae/used/{brand_id}/{model_id}"
        #   r = requests.get(self.proxy_url, params={"key": self.api_key, "url": url})
        #   ثم استخرج الإعلانات من r.text أو r.json()
        raise NotImplementedError(
            "وصّل المصدر الحي هنا (بروكسي/API). انظر تعليقات الملف."
        )

    def fetch(self, brand_id: str, model_id: str) -> Iterable[Listing]:
        for row in self._fetch_raw(brand_id, model_id):
            yield Listing(
                brand_id=brand_id,
                model_id=model_id,
                trim_id=row.get("trim_id", "unknown"),
                year=int(row["year"]),
                km=int(row["km"]),
                price=float(row["price"]),
                region=row.get("region", "gcc"),
                source=row.get("source", "live"),
            )


def recompute_stats(listings: list[Listing], reference_trims: dict, trim_new_prices: dict) -> dict:
    """يحوّل إعلانات خام إلى إحصاءات per (model, year) للفئة المرجعية.

    يُطبّع كل إعلان لسعر الفئة المرجعية بقسمته على نسبة فئته، ثم يحسب
    median/low/high لكل سنة. كده الإحصاء متّسق مهما اختلفت فئات الإعلانات.
    """
    grouped: dict[str, dict[int, list[float]]] = {}
    for lst in listings:
        key = f"{lst.brand_id}:{lst.model_id}"
        ref = reference_trims.get(key)
        prices = trim_new_prices.get(key, {})
        ref_new = float(prices.get(ref, 0) or 0)
        trim_new = float(prices.get(lst.trim_id, ref_new) or ref_new)
        mult = (trim_new / ref_new) if ref_new > 0 else 1.0
        norm_price = lst.price / mult if mult > 0 else lst.price
        grouped.setdefault(key, {}).setdefault(lst.year, []).append(norm_price)

    out: dict = {}
    for key, years in grouped.items():
        by_year = {}
        for year, vals in years.items():
            vals_sorted = sorted(vals)
            by_year[str(year)] = {
                "median": round(statistics.median(vals_sorted)),
                "low": round(vals_sorted[0]),
                "high": round(vals_sorted[-1]),
                "samples": len(vals_sorted),
            }
        out[key] = {
            "reference_trim": reference_trims.get(key),
            "trim_new_prices": trim_new_prices.get(key, {}),
            "by_year": by_year,
        }
    return out


def update_market_file(provider: ListingProvider, model_keys: list[tuple[str, str]]) -> None:
    """يسحب من المزوّد، يعيد حساب الإحصاءات، ويحدّث market_stats.json."""
    current = json.loads((DATA_DIR / "market_stats.json").read_text(encoding="utf-8"))
    reference_trims = {k: v.get("reference_trim") for k, v in current["models"].items()}
    trim_new_prices = {k: v.get("trim_new_prices", {}) for k, v in current["models"].items()}

    listings: list[Listing] = []
    for brand_id, model_id in model_keys:
        listings.extend(provider.fetch(brand_id, model_id))

    new_models = recompute_stats(listings, reference_trims, trim_new_prices)
    # ندمج: نحدّث الموديلات اللي رجع لها بيانات فقط.
    current["models"].update(new_models)
    current["updated_at"] = date.today().isoformat()
    (DATA_DIR / "market_stats.json").write_text(
        json.dumps(current, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"تم تحديث {len(new_models)} موديل من {len(listings)} إعلان.")


if __name__ == "__main__":
    # على سيرفرك: استبدل المزوّد بواحد موصول فعلاً، وفعّل عبر cron يومياً.
    provider = HttpListingProvider(proxy_url=None, api_key=None)
    keys = [
        ("toyota", "land_cruiser"),
        ("nissan", "patrol"),
        ("lexus", "es"),
        ("mitsubishi", "pajero"),
        ("hyundai", "elantra"),
    ]
    update_market_file(provider, keys)
