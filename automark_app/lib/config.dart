/// إعدادات التطبيق.
///
/// [apiBaseUrl]: عنوان سيرفر التسعير (البيانات الحية).
/// - اتركه فارغاً '' → التطبيق يعمل أوفلاين بالكامل من الجدول المحلي.
/// - للتجربة على المتصفّح والسيرفر على نفس الجهاز: 'http://127.0.0.1:8000'
/// - لمحاكي أندرويد: 'http://10.0.2.2:8000'
/// - للإنتاج: 'https://api.yourdomain.com'
class AppConfig {
  static const String apiBaseUrl = String.fromEnvironment(
    'API_BASE_URL',
    defaultValue: '',
  );
}
