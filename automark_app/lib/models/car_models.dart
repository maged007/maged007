/// نماذج البيانات للكتالوج: البراند، الموديل، الفئة، بالإضافة لحالة السيارة والمواصفات الإقليمية.

class Trim {
  final String id;
  final String nameAr;
  final double newPrice;

  const Trim({required this.id, required this.nameAr, required this.newPrice});

  factory Trim.fromJson(Map<String, dynamic> json) {
    return Trim(
      id: json['id'] as String,
      nameAr: json['nameAr'] as String,
      newPrice: (json['newPrice'] as num).toDouble(),
    );
  }
}

class CarModel {
  final String id;
  final String nameAr;
  final String nameEn;

  /// معرّف الفئة المرجعية التي تخص أسعار priceByYear.
  final String referenceTrimId;

  /// أسعار السوق الحقيقية للفئة المرجعية لكل سنة { سنة: سعر }.
  final Map<int, double> priceByYear;

  /// عقوبة الدرهم لكل كيلومتر زائد عن المتوقع (اختيارية).
  final double? kmPenaltyPerKm;

  final List<Trim> trims;

  const CarModel({
    required this.id,
    required this.nameAr,
    required this.nameEn,
    required this.referenceTrimId,
    required this.priceByYear,
    required this.kmPenaltyPerKm,
    required this.trims,
  });

  /// الفئة المرجعية التي تُنسب إليها أسعار priceByYear.
  Trim get referenceTrim =>
      trims.firstWhere((t) => t.id == referenceTrimId, orElse: () => trims.first);

  factory CarModel.fromJson(Map<String, dynamic> json) {
    final rawPrices = (json['priceByYear'] as Map<String, dynamic>);
    final prices = <int, double>{
      for (final e in rawPrices.entries)
        int.parse(e.key): (e.value as num).toDouble(),
    };

    return CarModel(
      id: json['id'] as String,
      nameAr: json['nameAr'] as String,
      nameEn: json['nameEn'] as String? ?? json['nameAr'] as String,
      referenceTrimId: json['referenceTrimId'] as String,
      priceByYear: prices,
      kmPenaltyPerKm: (json['kmPenaltyPerKm'] as num?)?.toDouble(),
      trims: (json['trims'] as List<dynamic>)
          .map((e) => Trim.fromJson(e as Map<String, dynamic>))
          .toList(),
    );
  }
}

class Brand {
  final String id;
  final String nameAr;
  final String nameEn;
  final List<CarModel> models;

  const Brand({
    required this.id,
    required this.nameAr,
    required this.nameEn,
    required this.models,
  });

  factory Brand.fromJson(Map<String, dynamic> json) {
    return Brand(
      id: json['id'] as String,
      nameAr: json['nameAr'] as String,
      nameEn: json['nameEn'] as String? ?? json['nameAr'] as String,
      models: (json['models'] as List<dynamic>)
          .map((e) => CarModel.fromJson(e as Map<String, dynamic>))
          .toList(),
    );
  }
}

/// حالة السيارة مع معاملها كما يظهر في pricing_config.json.
enum CarCondition {
  excellent('excellent', 'ممتاز'),
  veryGood('very_good', 'جيد جداً'),
  good('good', 'جيد'),
  fair('fair', 'متوسط'),
  needsWork('needs_work', 'يحتاج صيانة');

  final String key;
  final String labelAr;
  const CarCondition(this.key, this.labelAr);
}

/// المواصفات الإقليمية مع مفتاحها في pricing_config.json.
enum RegionSpec {
  gcc('gcc', 'خليجي'),
  japanese('japanese', 'ياباني'),
  european('european', 'أوروبي'),
  american('american', 'أمريكي'),
  canadian('canadian', 'كندي'),
  unknown('unknown', 'غير معروف');

  final String key;
  final String labelAr;
  const RegionSpec(this.key, this.labelAr);
}
