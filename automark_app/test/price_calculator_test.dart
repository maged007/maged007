import 'package:automark_app/logic/price_calculator.dart';
import 'package:automark_app/models/car_models.dart';
import 'package:automark_app/models/pricing_config.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  const config = PricingConfig(
    currentYear: 2025,
    expectedKmPerYear: 18000,
    defaultKmPenaltyPerKm: 0.4,
    rangeSpread: 0.07,
    minRatio: 0.45,
    maxRatio: 1.3,
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
  );

  const exr = Trim(id: 'exr', nameAr: 'EXR', newPrice: 238900);
  const gxr = Trim(id: 'gxr', nameAr: 'GXR', newPrice: 274900);
  const vxr = Trim(id: 'vxr', nameAr: 'VXR', newPrice: 320000);
  const model = CarModel(
    id: 'land_cruiser',
    nameAr: 'لاند كروزر',
    nameEn: 'Land Cruiser',
    referenceTrimId: 'gxr',
    priceByYear: {
      2018: 175000,
      2019: 188000,
      2020: 198000,
      2021: 212000,
      2022: 230000,
    },
    kmPenaltyPerKm: 0.7,
    trims: [exr, gxr, vxr],
  );
  const brand = Brand(
    id: 'toyota',
    nameAr: 'تويوتا',
    nameEn: 'Toyota',
    models: [model],
  );

  PriceInput buildInput({
    Trim trim = gxr,
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

  test('السعر الأساسي يطابق بيانات السوق للسنة', () {
    // GXR 2020 بمسافة متوقعة (90,000 = 18,000×5) وحالة جيد جداً وخليجي → ≈ سعر السوق 198,000.
    final r = calc.estimate(buildInput(year: 2020, km: 90000)).estimated;
    expect(r, closeTo(198000, 1000));
  });

  test('الاستيفاء بين السنين يعمل', () {
    // لا توجد بيانات 2020.5، لكن 2019=188k و2020=198k.
    final base = calc.basePriceForYear(model, 2019);
    expect(base, 188000);
  });

  test('مسافة أعلى → سعر أقل', () {
    final low = calc.estimate(buildInput(km: 50000)).estimated;
    final high = calc.estimate(buildInput(km: 200000)).estimated;
    expect(high, lessThan(low));
  });

  test('فئة أعلى → سعر أعلى', () {
    final vxrPrice = calc.estimate(buildInput(trim: vxr)).estimated;
    final exrPrice = calc.estimate(buildInput(trim: exr)).estimated;
    expect(vxrPrice, greaterThan(exrPrice));
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
    final newer = calc.estimate(buildInput(year: 2022)).estimated;
    final older = calc.estimate(buildInput(year: 2018)).estimated;
    expect(newer, greaterThan(older));
  });
}
