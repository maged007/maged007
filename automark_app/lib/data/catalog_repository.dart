import 'dart:convert';

import 'package:flutter/services.dart' show rootBundle;

import '../models/car_models.dart';
import '../models/pricing_config.dart';

/// يحمّل الكتالوج وإعدادات التسعير من ملفات JSON في assets.
class CatalogRepository {
  List<Brand>? _brands;
  PricingConfig? _config;

  List<Brand> get brands => _brands ?? const [];
  PricingConfig get config => _config!;

  bool get isLoaded => _brands != null && _config != null;

  Future<void> load() async {
    final catalogRaw = await rootBundle.loadString('assets/data/catalog.json');
    final configRaw =
        await rootBundle.loadString('assets/data/pricing_config.json');

    final catalogJson = jsonDecode(catalogRaw) as Map<String, dynamic>;
    final configJson = jsonDecode(configRaw) as Map<String, dynamic>;

    _brands = (catalogJson['brands'] as List<dynamic>)
        .map((e) => Brand.fromJson(e as Map<String, dynamic>))
        .toList();
    _config = PricingConfig.fromJson(configJson);
  }
}
