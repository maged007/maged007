import 'dart:math';

import '../models/car_models.dart';
import '../models/price_result.dart';
import '../models/pricing_config.dart';

/// مدخلات الحساب التي يجمعها المستخدم من الفورم.
class PriceInput {
  final Brand brand;
  final CarModel model;
  final Trim trim;
  final int modelYear;
  final int km;
  final CarCondition condition;
  final RegionSpec region;

  const PriceInput({
    required this.brand,
    required this.model,
    required this.trim,
    required this.modelYear,
    required this.km,
    required this.condition,
    required this.region,
  });
}

/// حاسبة السعر بالاعتماد على أسعار السوق الحقيقية لكل سنة (priceByYear)،
/// مع استيفاء خطي بين السنين، ثم تعديل حسب الفئة والمسافة والحالة والمواصفات.
/// كل الثوابت تأتي من [PricingConfig] (المحمّل من JSON) أو من بيانات الموديل.
class PriceCalculator {
  final PricingConfig config;

  const PriceCalculator(this.config);

  /// السعر الأساسي للفئة المرجعية في سنة معيّنة، باستيفاء خطي بين النقاط الحقيقية.
  /// خارج المدى المتاح نثبّت على أقرب طرف.
  double basePriceForYear(CarModel model, int year) {
    final prices = model.priceByYear;
    if (prices.isEmpty) return 0;

    final years = prices.keys.toList()..sort();
    final minYear = years.first;
    final maxYear = years.last;

    if (prices.containsKey(year)) return prices[year]!;
    if (year <= minYear) return prices[minYear]!;
    if (year >= maxYear) return prices[maxYear]!;

    // أقرب سنة أقل وأقرب سنة أعلى لها بيانات.
    int lower = minYear;
    int upper = maxYear;
    for (final y in years) {
      if (y <= year && y > lower) lower = y;
      if (y >= year && y < upper) upper = y;
    }
    final pLower = prices[lower]!;
    final pUpper = prices[upper]!;
    final t = (year - lower) / (upper - lower);
    return pLower + (pUpper - pLower) * t;
  }

  double kmPenaltyFor(CarModel model) {
    return model.kmPenaltyPerKm ?? config.defaultKmPenaltyPerKm;
  }

  PriceResult estimate(PriceInput input) {
    final model = input.model;
    final age = config.currentYear - input.modelYear;

    // 1) السعر الأساسي الحقيقي للفئة المرجعية في سنة السيارة.
    final base = basePriceForYear(model, input.modelYear);

    // 2) تعديل الفئة: نسبة سعر الفئة المختارة إلى الفئة المرجعية (من أسعار الجديد).
    final refNew = model.referenceTrim.newPrice;
    final trimMultiplier = refNew > 0 ? input.trim.newPrice / refNew : 1.0;
    final priceForCar = base * trimMultiplier;

    // 3) تعديل المسافة: الفرق عن الكيلومترات المتوقعة لعمر السيارة.
    final expectedKm = config.expectedKmPerYear * max(age, 0);
    final kmDiff = input.km - expectedKm;
    final priceAfterKm = priceForCar - (kmDiff * kmPenaltyFor(model));

    // 4) معاملات الحالة والمواصفات الإقليمية.
    final conditionFactor = config.conditionFactors[input.condition.key] ?? 1.0;
    final regionFactor = config.regionFactors[input.region.key] ?? 1.0;

    double estimated = priceAfterKm * conditionFactor * regionFactor;

    // 5) حدود منطقية نسبةً إلى سعر الفئة لتجنّب القيم الشاذة.
    final minPrice = priceForCar * config.minRatio;
    final maxPrice = priceForCar * config.maxRatio;
    estimated = estimated.clamp(minPrice, maxPrice);

    final low = estimated * (1 - config.rangeSpread);
    final high = estimated * (1 + config.rangeSpread);

    return PriceResult(estimated: estimated, low: low, high: high);
  }
}
