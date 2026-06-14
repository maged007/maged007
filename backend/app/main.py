"""واجهة API لتقدير سعر السيارات المستعملة في الإمارات (FastAPI).

تشغيل:
    cd backend
    pip install -r requirements.txt
    uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

نقاط النهاية:
    GET  /health                  فحص الصحة
    GET  /catalog                 الموديلات والفئات والسنوات المتاحة
    POST /estimate                تقدير السعر
"""

from __future__ import annotations

import json
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from .valuation import ValuationEngine

DATA_DIR = Path(__file__).resolve().parent.parent / "data"

app = FastAPI(title="UAE Used Car Valuation API", version="1.0.0")

# السماح للتطبيق (فلاتر ويب/موبايل) بالنداء.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def load_market_stats() -> dict:
    with open(DATA_DIR / "market_stats.json", encoding="utf-8") as f:
        return json.load(f)


_market = load_market_stats()
engine = ValuationEngine(_market)


class EstimateRequest(BaseModel):
    brand_id: str = Field(..., examples=["toyota"])
    model_id: str = Field(..., examples=["land_cruiser"])
    trim_id: str = Field(..., examples=["gxr"])
    year: int = Field(..., ge=1990, le=2026, examples=[2020])
    km: int = Field(..., ge=0, examples=[80000])
    condition: str = Field("very_good", examples=["very_good"])
    region: str = Field("gcc", examples=["gcc"])


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "updated_at": _market.get("updated_at")}


@app.get("/catalog")
def catalog() -> dict:
    """يرجّع الموديلات المتاحة والسنوات لكل موديل (لمزامنة التطبيق)."""
    out = {}
    for key, m in _market.get("models", {}).items():
        years = sorted(int(y) for y in m["by_year"])
        out[key] = {
            "reference_trim": m.get("reference_trim"),
            "trims": list(m.get("trim_new_prices", {}).keys()),
            "year_min": years[0] if years else None,
            "year_max": years[-1] if years else None,
        }
    return {"models": out}


@app.post("/estimate")
def estimate(req: EstimateRequest) -> dict:
    try:
        r = engine.estimate(
            brand_id=req.brand_id,
            model_id=req.model_id,
            trim_id=req.trim_id,
            year=req.year,
            km=req.km,
            condition=req.condition,
            region=req.region,
        )
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))

    return {
        "estimated": r.estimated,
        "low": r.low,
        "high": r.high,
        "market_low": r.market_low,
        "market_high": r.market_high,
        "samples": r.samples,
        "confidence": r.confidence,
        "based_on_year_price": r.based_on_year_price,
        "currency": "AED",
    }


def reload_market() -> None:
    """يعيد تحميل البيانات بعد تحديثها (تُستدعى من ingest)."""
    global _market, engine
    _market = load_market_stats()
    engine = ValuationEngine(_market)
