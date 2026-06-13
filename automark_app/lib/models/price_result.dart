/// نتيجة حساب السعر: قيمة مركزية تقديرية + نطاق (أدنى/أعلى).
class PriceResult {
  final double estimated;
  final double low;
  final double high;

  const PriceResult({
    required this.estimated,
    required this.low,
    required this.high,
  });
}
