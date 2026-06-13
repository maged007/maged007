/// إعدادات التسعير المحمّلة من assets/data/pricing_config.json.
/// كل القيم قابلة للتعديل من الملف بدون لمس الكود.
class PricingConfig {
  final int currentYear;
  final double firstYearDrop;
  final double defaultYearlyRetention;
  final double expectedKmPerYear;
  final double defaultKmPenaltyPerKm;
  final double rangeSpread;
  final double minRatio;
  final double maxRatio;
  final Map<String, double> conditionFactors;
  final Map<String, double> regionFactors;
  final Map<String, double> brandRetention;

  const PricingConfig({
    required this.currentYear,
    required this.firstYearDrop,
    required this.defaultYearlyRetention,
    required this.expectedKmPerYear,
    required this.defaultKmPenaltyPerKm,
    required this.rangeSpread,
    required this.minRatio,
    required this.maxRatio,
    required this.conditionFactors,
    required this.regionFactors,
    required this.brandRetention,
  });

  factory PricingConfig.fromJson(Map<String, dynamic> json) {
    Map<String, double> toDoubleMap(dynamic raw) {
      final map = (raw as Map<String, dynamic>?) ?? const {};
      return map.map((k, v) => MapEntry(k, (v as num).toDouble()));
    }

    return PricingConfig(
      currentYear: (json['currentYear'] as num).toInt(),
      firstYearDrop: (json['firstYearDrop'] as num).toDouble(),
      defaultYearlyRetention: (json['defaultYearlyRetention'] as num).toDouble(),
      expectedKmPerYear: (json['expectedKmPerYear'] as num).toDouble(),
      defaultKmPenaltyPerKm: (json['defaultKmPenaltyPerKm'] as num).toDouble(),
      rangeSpread: (json['rangeSpread'] as num).toDouble(),
      minRatio: (json['minRatio'] as num).toDouble(),
      maxRatio: (json['maxRatio'] as num).toDouble(),
      conditionFactors: toDoubleMap(json['conditionFactors']),
      regionFactors: toDoubleMap(json['regionFactors']),
      brandRetention: toDoubleMap(json['brandRetention']),
    );
  }
}
