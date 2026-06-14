import 'package:flutter/material.dart';

import '../config.dart';
import '../data/catalog_repository.dart';
import '../data/pricing_service.dart';
import '../logic/price_calculator.dart';
import '../models/car_models.dart';
import '../widgets/labeled_dropdown.dart';
import 'result_screen.dart';

/// الشاشة الرئيسية: فورم اختيار بيانات السيارة لحساب السعر.
class HomeScreen extends StatefulWidget {
  final CatalogRepository repository;

  const HomeScreen({super.key, required this.repository});

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  final _formKey = GlobalKey<FormState>();
  final _kmController = TextEditingController();

  Brand? _brand;
  CarModel? _model;
  Trim? _trim;
  int? _year;
  CarCondition _condition = CarCondition.veryGood;
  RegionSpec _region = RegionSpec.gcc;

  late final List<int> _years;
  late final PricingService _pricingService;
  bool _loading = false;

  @override
  void initState() {
    super.initState();
    final current = widget.repository.config.currentYear;
    _years = [for (int y = current; y >= 2015; y--) y];
    _pricingService = PricingService(
      apiBaseUrl: AppConfig.apiBaseUrl,
      localConfig: widget.repository.config,
    );
  }

  @override
  void dispose() {
    _kmController.dispose();
    super.dispose();
  }

  void _onBrandChanged(Brand? b) {
    setState(() {
      _brand = b;
      _model = null;
      _trim = null;
    });
  }

  void _onModelChanged(CarModel? m) {
    setState(() {
      _model = m;
      _trim = null;
    });
  }

  Future<void> _calculate() async {
    if (!_formKey.currentState!.validate()) return;
    if (_brand == null ||
        _model == null ||
        _trim == null ||
        _year == null) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('من فضلك أكمل كل الاختيارات')),
      );
      return;
    }

    final input = PriceInput(
      brand: _brand!,
      model: _model!,
      trim: _trim!,
      modelYear: _year!,
      km: int.parse(_kmController.text.trim()),
      condition: _condition,
      region: _region,
    );

    setState(() => _loading = true);
    final outcome = await _pricingService.estimate(input);
    if (!mounted) return;
    setState(() => _loading = false);

    Navigator.of(context).push(
      MaterialPageRoute(
        builder: (_) => ResultScreen(input: input, outcome: outcome),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final brands = widget.repository.brands;

    return Scaffold(
      appBar: AppBar(title: const Text('تقدير سعر السيارة المستعملة')),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(20),
        child: Form(
          key: _formKey,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              LabeledDropdown<Brand>(
                label: 'البراند',
                value: _brand,
                items: brands,
                itemLabel: (b) => b.nameAr,
                onChanged: _onBrandChanged,
              ),
              LabeledDropdown<CarModel>(
                label: 'الموديل',
                value: _model,
                items: _brand?.models ?? const [],
                itemLabel: (m) => m.nameAr,
                onChanged: _onModelChanged,
                enabled: _brand != null,
              ),
              LabeledDropdown<Trim>(
                label: 'الفئة',
                value: _trim,
                items: _model?.trims ?? const [],
                itemLabel: (t) => t.nameAr,
                onChanged: (t) => setState(() => _trim = t),
                enabled: _model != null,
              ),
              LabeledDropdown<int>(
                label: 'سنة الصنع',
                value: _year,
                items: _years,
                itemLabel: (y) => '$y',
                onChanged: (y) => setState(() => _year = y),
              ),
              const Padding(
                padding: EdgeInsets.only(bottom: 6, right: 4),
                child: Text(
                  'المسافة المقطوعة (كم)',
                  style: TextStyle(fontWeight: FontWeight.w600, fontSize: 15),
                ),
              ),
              TextFormField(
                controller: _kmController,
                keyboardType: TextInputType.number,
                decoration: const InputDecoration(hintText: 'مثال: 80000'),
                validator: (v) {
                  final n = int.tryParse((v ?? '').trim());
                  if (n == null || n < 0) return 'أدخل مسافة صحيحة';
                  return null;
                },
              ),
              const SizedBox(height: 16),
              LabeledDropdown<CarCondition>(
                label: 'حالة السيارة',
                value: _condition,
                items: CarCondition.values,
                itemLabel: (c) => c.labelAr,
                onChanged: (c) => setState(() => _condition = c!),
              ),
              LabeledDropdown<RegionSpec>(
                label: 'المواصفات الإقليمية',
                value: _region,
                items: RegionSpec.values,
                itemLabel: (r) => r.labelAr,
                onChanged: (r) => setState(() => _region = r!),
              ),
              const SizedBox(height: 8),
              FilledButton(
                onPressed: _loading ? null : _calculate,
                child: _loading
                    ? const SizedBox(
                        height: 22,
                        width: 22,
                        child: CircularProgressIndicator(
                          strokeWidth: 2,
                          color: Colors.white,
                        ),
                      )
                    : const Text('احسب السعر'),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
