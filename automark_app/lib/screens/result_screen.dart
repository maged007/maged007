import 'package:flutter/material.dart';
import 'package:intl/intl.dart';

import '../logic/price_calculator.dart';
import '../models/price_result.dart';
import '../theme/app_theme.dart';

/// شاشة عرض نتيجة التقدير: السعر المركزي + النطاق + ملخص المدخلات.
class ResultScreen extends StatelessWidget {
  final PriceInput input;
  final PriceResult result;

  const ResultScreen({super.key, required this.input, required this.result});

  String _money(double v) {
    final f = NumberFormat('#,##0', 'en');
    return '${f.format(v.round())} درهم';
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('السعر التقديري')),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(20),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Card(
              color: AppTheme.primary,
              shape: RoundedRectangleBorder(
                borderRadius: BorderRadius.circular(16),
              ),
              child: Padding(
                padding: const EdgeInsets.symmetric(vertical: 28, horizontal: 16),
                child: Column(
                  children: [
                    const Text(
                      'السعر التقديري',
                      style: TextStyle(color: Colors.white70, fontSize: 16),
                    ),
                    const SizedBox(height: 8),
                    Text(
                      _money(result.estimated),
                      style: const TextStyle(
                        color: Colors.white,
                        fontSize: 30,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                    const SizedBox(height: 12),
                    Text(
                      'النطاق: ${_money(result.low)}  -  ${_money(result.high)}',
                      style: const TextStyle(color: Colors.white, fontSize: 15),
                    ),
                  ],
                ),
              ),
            ),
            const SizedBox(height: 20),
            const Text(
              'ملخص السيارة',
              style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 8),
            _row('البراند', input.brand.nameAr),
            _row('الموديل', input.model.nameAr),
            _row('الفئة', input.trim.nameAr),
            _row('سنة الصنع', '${input.modelYear}'),
            _row('المسافة', '${NumberFormat('#,##0', 'en').format(input.km)} كم'),
            _row('الحالة', input.condition.labelAr),
            _row('المواصفات', input.region.labelAr),
            const SizedBox(height: 24),
            FilledButton(
              onPressed: () => Navigator.of(context).pop(),
              child: const Text('حساب سيارة أخرى'),
            ),
            const SizedBox(height: 12),
            const Text(
              'التقدير استرشادي مبني على بيانات السوق وقد يختلف حسب حالة السيارة الفعلية.',
              textAlign: TextAlign.center,
              style: TextStyle(color: Colors.black54, fontSize: 12),
            ),
          ],
        ),
      ),
    );
  }

  Widget _row(String label, String value) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 6),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Text(label, style: const TextStyle(color: Colors.black54)),
          Text(value, style: const TextStyle(fontWeight: FontWeight.w600)),
        ],
      ),
    );
  }
}
