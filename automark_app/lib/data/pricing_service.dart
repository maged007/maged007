import 'dart:convert';

import 'package:http/http.dart' as http;

import '../logic/price_calculator.dart';
import '../models/price_result.dart';
import '../models/pricing_config.dart';

/// خدمة التسعير: تحاول السيرفر (بيانات حية) أولاً، وترجع للحساب المحلي
/// (الأوفلاين) لو السيرفر غير موصول. تُرجع النتيجة + مصدرها.
class EstimateOutcome {
  final PriceResult result;
  final bool fromServer;
  final int? samples;
  final String? confidence;

  const EstimateOutcome({
    required this.result,
    required this.fromServer,
    this.samples,
    this.confidence,
  });
}

class PricingService {
  /// عنوان السيرفر. اتركه فارغاً للعمل أوفلاين فقط.
  /// مثال: 'https://api.yourdomain.com' أو 'http://10.0.2.2:8000' للمحاكي.
  final String apiBaseUrl;
  final PricingConfig localConfig;

  PricingService({required this.apiBaseUrl, required this.localConfig});

  bool get hasServer => apiBaseUrl.trim().isNotEmpty;

  Future<EstimateOutcome> estimate(PriceInput input) async {
    if (hasServer) {
      try {
        final remote = await _estimateRemote(input);
        if (remote != null) return remote;
      } catch (_) {
        // أي خطأ شبكة → نكمّل بالحساب المحلي.
      }
    }
    final local = PriceCalculator(localConfig).estimate(input);
    return EstimateOutcome(result: local, fromServer: false);
  }

  Future<EstimateOutcome?> _estimateRemote(PriceInput input) async {
    final uri = Uri.parse('$apiBaseUrl/estimate');
    final resp = await http
        .post(
          uri,
          headers: {'Content-Type': 'application/json'},
          body: jsonEncode({
            'brand_id': input.brand.id,
            'model_id': input.model.id,
            'trim_id': input.trim.id,
            'year': input.modelYear,
            'km': input.km,
            'condition': input.condition.key,
            'region': input.region.key,
          }),
        )
        .timeout(const Duration(seconds: 8));

    if (resp.statusCode != 200) return null;
    final data = jsonDecode(resp.body) as Map<String, dynamic>;
    final result = PriceResult(
      estimated: (data['estimated'] as num).toDouble(),
      low: (data['low'] as num).toDouble(),
      high: (data['high'] as num).toDouble(),
    );
    return EstimateOutcome(
      result: result,
      fromServer: true,
      samples: (data['samples'] as num?)?.toInt(),
      confidence: data['confidence'] as String?,
    );
  }
}
