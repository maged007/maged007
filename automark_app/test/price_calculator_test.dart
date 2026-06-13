import 'package:automark_app/logic/price_calculator.dart';
import 'package:automark_app/models/car_models.dart';
import 'package:automark_app/models/pricing_config.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  const config = PricingConfig(
    currentYear: 2025,
    firstYearDrop: 0.82,
    defaultYearlyRetention: 0.86,
    expectedKmPerYear: 18000,
    defaultKmPenaltyPerKm: 0.4,
    rangeSpread: 0.07,
    minRatio: 0.12,
    maxRatio: 0.97,
    conditionFactors: {
      'excellent': 1.05,
      'very_good': 1.0,
      'good': 0.93,
      'fair': 0.85,
      'needs_work': 0.72,
    },
    regionFactors: {
      'gcc': 1.0,
      'japanese': 0.97,
      'european': 0.95,
      'american': 0.92,
      'canadian': 0.9,
      'unknown': 0.85,
    },
    brandRetention: {'toyota': 0.92},
  );

  const trim = Trim(id: 'gxr', nameAr: 'GXR', newPrice: 275000);
  const model = CarModel(
    id: 'land_cruiser',
    nameAr: 'لاند كروزر',
    nameEn: 'Land Cruiser',
    yearlyRetention: 0.92,
    kmPenaltyPerKm: 0.9,
    trims: [trim],
  );
  const brand = Brand(
    id: 'toyota',
    nameAr: 'تويوتا',
    nameEn: 'Toyota',
    models: [model],
  );

  PriceInput buildInput({
    int year = 2020,
    int km = 90000,
    CarCondition condition = CarCondition.veryGood,
    RegionSpec region = RegionSpec.gcc,
  }) {
    return PriceInput(
      brand: brand,
      model: model,
      trim: trim,
      modelYear: year,
      km: km,
      condition: condition,
      region: region,
    );
  }

  const calc = PriceCalculator(config);

  test('السعر ضمن النطاق ومتسق', () {
    final r = calc.estimate(buildInput());
    expect(r.low, lessThan(r.estimated));
    expect(r.high, greaterThan(r.estimated));
    expect(r.estimated, greaterThan(0));
  });

  test('مسافة أعلى → سعر أقل', () {
    final low = calc.estimate(buildInput(km: 50000)).estimated;
    final high = calc.estimate(buildInput(km: 200000)).estimated;
    expect(high, lessThan(low));
  });

  test('حالة أفضل → سعر أعلى', () {
    final excellent =
        calc.estimate(buildInput(condition: CarCondition.excellent)).estimated;
    final needsWork =
        calc.estimate(buildInput(condition: CarCondition.needsWork)).estimated;
    expect(excellent, greaterThan(needsWork));
  });

  test('خليجي أعلى من أمريكي', () {
    final gcc = calc.estimate(buildInput(region: RegionSpec.gcc)).estimated;
    final american =
        calc.estimate(buildInput(region: RegionSpec.american)).estimated;
    expect(gcc, greaterThan(american));
  });

  test('سيارة أحدث أغلى من أقدم', () {
    final newer = calc.estimate(buildInput(year: 2023)).estimated;
    final older = calc.estimate(buildInput(year: 2016)).estimated;
    expect(newer, greaterThan(older));
  });

  test('لاند كروزر 2020 سعر منطقي', () {
    final r = calc.estimate(buildInput(year: 2020, km: 90000)).estimated;
    expect(r, greaterThan(120000));
    expect(r, lessThan(220000));
  });
}
