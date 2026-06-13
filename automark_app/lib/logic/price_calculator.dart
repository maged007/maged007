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

/// حاسبة السعر: تبدأ من سعر الجديد ثم تطبّق منحنى استهلاك معاير + تعديلات.
/// كل الثوابت تأتي من [PricingConfig] (المحمّل من JSON) أو من بيانات الموديل.
class PriceCalculator {
  final PricingConfig config;

  const PriceCalculator(this.config);

  /// نسبة الاحتفاظ السنوية بالأولوية: قيمة الموديل ← قيمة البراند ← الافتراضي العام.
  double retentionFor(Brand brand, CarModel model) {
    return model.yearlyRetention ??
        config.brandRetention[brand.id] ??
        config.defaultYearlyRetention;
  }

  double kmPenaltyFor(CarModel model) {
    return model.kmPenaltyPerKm ?? config.defaultKmPenaltyPerKm;
  }

  PriceResult estimate(PriceInput input) {
    final newPrice = input.trim.newPrice;
    final age = config.currentYear - input.modelYear;

    // منحنى الاستهلاك: نزولة أكبر في السنة الأولى ثم احتفاظ سنوي.
    double priceForAge;
    if (age <= 0) {
      priceForAge = newPrice;
    } else {
      final retention = retentionFor(input.brand, input.model);
      priceForAge = newPrice * config.firstYearDrop * pow(retention, age - 1);
    }

    // تعديل المسافة: فرق الكيلومترات عن المتوقع لسنة السيارة.
    final expectedKm = config.expectedKmPerYear * max(age, 0);
    final kmDiff = input.km - expectedKm;
    final priceAfterKm = priceForAge - (kmDiff * kmPenaltyFor(input.model));

    // معاملات الحالة والمواصفات الإقليمية.
    final conditionFactor = config.conditionFactors[input.condition.key] ?? 1.0;
    final regionFactor = config.regionFactors[input.region.key] ?? 1.0;

    double estimated = priceAfterKm * conditionFactor * regionFactor;

    // حدود منطقية حتى لا يخرج السعر عن المعقول.
    final minPrice = newPrice * config.minRatio;
    final maxPrice = newPrice * config.maxRatio;
    estimated = estimated.clamp(minPrice, maxPrice);

    final low = estimated * (1 - config.rangeSpread);
    final high = estimated * (1 + config.rangeSpread);

    return PriceResult(estimated: estimated, low: low, high: high);
  }
}
