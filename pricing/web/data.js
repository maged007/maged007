// مولّد آلياً من data/pricing_data.json — لا تعدّله يدوياً.
window.PRICING_DATA = {
  "_meta": {
    "currency": "AED",
    "market": "UAE",
    "description": "محرّك تسعير السيارات المستعملة — مرساة على سعر الوكيل. كل القيم نِسب مئوية قابلة للتعديل.",
    "equation": "price = dealer_price[trim] * brand_retention(age) * demand_factor[model] * km_factor * spec_factor * condition_factor",
    "unified_base": "ناتج (ممتازة) ≈ سعر الإعلان × 0.88",
    "ad_to_sale_ratio": 0.88
  },
  "retention_tiers": {
    "_doc": "احتفاظ البراند = الإهلاك العام. first_year_drop = خصم السنة الأولى، annual_drop = خصم كل سنة بعدها. retention(age) = (1-first_year_drop) * (1-annual_drop)^(age-1), age>=1 ; retention(0)=1",
    "high": {
      "first_year_drop": 0.15,
      "annual_drop": 0.075,
      "floor": 0.18
    },
    "medium": {
      "first_year_drop": 0.2,
      "annual_drop": 0.11,
      "floor": 0.12
    },
    "low": {
      "first_year_drop": 0.25,
      "annual_drop": 0.14,
      "floor": 0.08
    },
    "german": {
      "first_year_drop": 0.28,
      "annual_drop": 0.165,
      "floor": 0.06
    }
  },
  "brand_tier": {
    "toyota": "high",
    "lexus": "high",
    "honda": "medium",
    "mitsubishi": "medium",
    "hyundai": "medium",
    "kia": "medium",
    "nissan": "low",
    "ford": "low",
    "mercedes": "german",
    "bmw": "german"
  },
  "km_factor": {
    "_doc": "كم أكتر = أرخص. expected_km = age * baseline_km_per_year. كل 10,000 كم فوق المتوقع تخصم step_per_10k، وتحت المتوقع تزيد بنفس النسبة. القيمة محصورة بين min/max.",
    "baseline_km_per_year": 20000,
    "step_per_10k": 0.02,
    "min": 0.8,
    "max": 1.12
  },
  "spec_factor": {
    "_doc": "خليجي (GCC) كامل القيمة. وارد (أمريكي/كندي) ينخفض ~35%.",
    "gcc": 1.0,
    "imported": 0.65
  },
  "condition_factor": {
    "_doc": "5 شرائح. ممتازة = القيمة الأساسية قبل خصم الحالة.",
    "excellent": 1.0,
    "very_good": 0.93,
    "good": 0.86,
    "fair": 0.75,
    "needs_work": 0.62
  },
  "brands": {
    "toyota": {
      "label": "تويوتا",
      "models": {
        "corolla": {
          "label": "كورولا",
          "dealer_price": 95000,
          "demand_factor": 1.0,
          "type": "sedan"
        },
        "camry": {
          "label": "كامري",
          "dealer_price": 130000,
          "demand_factor": 1.02,
          "type": "sedan"
        },
        "land_cruiser": {
          "label": "لاندكروزر",
          "dealer_price": 320000,
          "demand_factor": 1.15,
          "type": "suv"
        },
        "prado": {
          "label": "برادو",
          "dealer_price": 230000,
          "demand_factor": 1.18,
          "type": "suv"
        },
        "rav4": {
          "label": "RAV4",
          "dealer_price": 130000,
          "demand_factor": 1.08,
          "type": "suv"
        }
      }
    },
    "nissan": {
      "label": "نيسان",
      "models": {
        "altima": {
          "label": "التيما",
          "dealer_price": 105000,
          "demand_factor": 0.97,
          "type": "sedan"
        },
        "sunny": {
          "label": "صني",
          "dealer_price": 70000,
          "demand_factor": 1.0,
          "type": "sedan"
        },
        "patrol": {
          "label": "باترول",
          "dealer_price": 290000,
          "demand_factor": 1.16,
          "type": "suv"
        },
        "x_trail": {
          "label": "إكس-تريل",
          "dealer_price": 115000,
          "demand_factor": 1.0,
          "type": "suv"
        },
        "kicks": {
          "label": "كيكس",
          "dealer_price": 78000,
          "demand_factor": 0.95,
          "type": "suv"
        }
      }
    },
    "honda": {
      "label": "هوندا",
      "models": {
        "civic": {
          "label": "سيفيك",
          "dealer_price": 100000,
          "demand_factor": 1.02,
          "type": "sedan"
        },
        "accord": {
          "label": "أكورد",
          "dealer_price": 135000,
          "demand_factor": 1.0,
          "type": "sedan"
        },
        "crv": {
          "label": "CR-V",
          "dealer_price": 130000,
          "demand_factor": 1.06,
          "type": "suv"
        },
        "pilot": {
          "label": "بايلوت",
          "dealer_price": 200000,
          "demand_factor": 0.98,
          "type": "suv"
        },
        "city": {
          "label": "سيتي",
          "dealer_price": 80000,
          "demand_factor": 1.0,
          "type": "sedan"
        }
      }
    },
    "mitsubishi": {
      "label": "ميتسوبيشي",
      "models": {
        "pajero": {
          "label": "باجيرو",
          "dealer_price": 175000,
          "demand_factor": 1.06,
          "type": "suv"
        },
        "lancer": {
          "label": "لانسر",
          "dealer_price": 75000,
          "demand_factor": 0.97,
          "type": "sedan"
        },
        "attrage": {
          "label": "أتراج",
          "dealer_price": 60000,
          "demand_factor": 1.0,
          "type": "sedan"
        },
        "montero_sport": {
          "label": "مونتيرو سبورت",
          "dealer_price": 150000,
          "demand_factor": 1.04,
          "type": "suv"
        },
        "l200": {
          "label": "L200",
          "dealer_price": 110000,
          "demand_factor": 1.05,
          "type": "pickup"
        }
      }
    },
    "hyundai": {
      "label": "هيونداي",
      "models": {
        "elantra": {
          "label": "إلنترا",
          "dealer_price": 90000,
          "demand_factor": 1.0,
          "type": "sedan"
        },
        "tucson": {
          "label": "توسان",
          "dealer_price": 120000,
          "demand_factor": 1.05,
          "type": "suv"
        },
        "sonata": {
          "label": "سوناتا",
          "dealer_price": 115000,
          "demand_factor": 0.97,
          "type": "sedan"
        },
        "santafe": {
          "label": "سنتافي",
          "dealer_price": 150000,
          "demand_factor": 1.01,
          "type": "suv"
        },
        "creta": {
          "label": "كريتا",
          "dealer_price": 85000,
          "demand_factor": 1.03,
          "type": "suv"
        }
      }
    },
    "kia": {
      "label": "كيا",
      "models": {
        "sportage": {
          "label": "سبورتاج",
          "dealer_price": 115000,
          "demand_factor": 1.04,
          "type": "suv"
        },
        "k5": {
          "label": "K5",
          "dealer_price": 110000,
          "demand_factor": 0.98,
          "type": "sedan"
        },
        "cerato": {
          "label": "سيراتو",
          "dealer_price": 85000,
          "demand_factor": 1.0,
          "type": "sedan"
        },
        "sorento": {
          "label": "سورينتو",
          "dealer_price": 150000,
          "demand_factor": 1.01,
          "type": "suv"
        },
        "picanto": {
          "label": "بيكانتو",
          "dealer_price": 60000,
          "demand_factor": 1.0,
          "type": "sedan"
        }
      }
    },
    "lexus": {
      "label": "لكزس",
      "models": {
        "es": {
          "label": "ES",
          "dealer_price": 200000,
          "demand_factor": 1.0,
          "type": "sedan"
        },
        "rx": {
          "label": "RX",
          "dealer_price": 280000,
          "demand_factor": 1.08,
          "type": "suv"
        },
        "lx": {
          "label": "LX",
          "dealer_price": 550000,
          "demand_factor": 1.15,
          "type": "suv"
        },
        "gx": {
          "label": "GX",
          "dealer_price": 350000,
          "demand_factor": 1.1,
          "type": "suv"
        },
        "nx": {
          "label": "NX",
          "dealer_price": 230000,
          "demand_factor": 1.03,
          "type": "suv"
        }
      }
    },
    "mercedes": {
      "label": "مرسيدس",
      "models": {
        "c_class": {
          "label": "C-Class",
          "dealer_price": 230000,
          "demand_factor": 0.97,
          "type": "sedan"
        },
        "e_class": {
          "label": "E-Class",
          "dealer_price": 320000,
          "demand_factor": 0.97,
          "type": "sedan"
        },
        "s_class": {
          "label": "S-Class",
          "dealer_price": 600000,
          "demand_factor": 0.92,
          "type": "sedan"
        },
        "glc": {
          "label": "GLC",
          "dealer_price": 280000,
          "demand_factor": 1.02,
          "type": "suv"
        },
        "g_class": {
          "label": "G-Class",
          "dealer_price": 850000,
          "demand_factor": 1.22,
          "type": "suv"
        }
      }
    },
    "bmw": {
      "label": "BMW",
      "models": {
        "series3": {
          "label": "الفئة الثالثة",
          "dealer_price": 230000,
          "demand_factor": 0.97,
          "type": "sedan"
        },
        "series5": {
          "label": "الفئة الخامسة",
          "dealer_price": 320000,
          "demand_factor": 0.96,
          "type": "sedan"
        },
        "x5": {
          "label": "X5",
          "dealer_price": 400000,
          "demand_factor": 1.03,
          "type": "suv"
        },
        "series7": {
          "label": "الفئة السابعة",
          "dealer_price": 600000,
          "demand_factor": 0.9,
          "type": "sedan"
        },
        "x6": {
          "label": "X6",
          "dealer_price": 450000,
          "demand_factor": 1.01,
          "type": "suv"
        }
      }
    },
    "ford": {
      "label": "فورد",
      "models": {
        "explorer": {
          "label": "إكسبلورر",
          "dealer_price": 180000,
          "demand_factor": 1.0,
          "type": "suv"
        },
        "mustang": {
          "label": "موستانج",
          "dealer_price": 200000,
          "demand_factor": 1.03,
          "type": "coupe"
        },
        "edge": {
          "label": "إيدج",
          "dealer_price": 150000,
          "demand_factor": 0.95,
          "type": "suv"
        },
        "f150": {
          "label": "F-150",
          "dealer_price": 220000,
          "demand_factor": 1.05,
          "type": "pickup"
        },
        "expedition": {
          "label": "إكسبيديشن",
          "dealer_price": 280000,
          "demand_factor": 1.01,
          "type": "suv"
        }
      }
    }
  }
};
