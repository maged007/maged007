# سيرفر تقدير أسعار السيارات (UAE) — طريقة المقارنات

سيرفر FastAPI يقدّر سعر السيارة المستعملة بطريقة **المقارنات (Comparables)**:
يبدأ من **وسيط أسعار السوق الحقيقية** لكل (موديل + سنة)، ثم يعدّل حسب الفئة
والمسافة والحالة والمواصفات، ويرجّع السعر + نطاق + عدد العينات + درجة الثقة.

## التشغيل محلياً
```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```
ثم:
```bash
curl -X POST http://127.0.0.1:8000/estimate -H "Content-Type: application/json" \
  -d '{"brand_id":"toyota","model_id":"land_cruiser","trim_id":"gxr","year":2020,"km":80000,"condition":"very_good","region":"gcc"}'
```
توثيق تفاعلي: `http://127.0.0.1:8000/docs`

## ربط التطبيق (فلاتر)
شغّل التطبيق وهو يعرف عنوان السيرفر:
```bash
flutter run -d chrome --dart-define=API_BASE_URL=http://127.0.0.1:8000
```
لو مفيش `API_BASE_URL`، التطبيق يشتغل أوفلاين من الجدول المحلي تلقائياً.

## البنية
```
backend/
  app/
    main.py        # FastAPI: /health /catalog /estimate
    valuation.py   # محرّك المقارنات (منطق نقي قابل للاختبار)
    ingest.py      # توصيل المصدر الحي + إعادة حساب الإحصاءات
  data/
    market_stats.json   # إحصاءات السوق (median/low/high/samples) — قابلة للتحديث
  tests/
    test_valuation.py   # اختبارات بدون شبكة
```

## الاختبارات
```bash
cd backend && python -m unittest discover -s tests
```

## 🔌 تفعيل البيانات الحية (أهم خطوة للدقة القصوى)
الدقة القصوى تأتي من تغذية `market_stats.json` بإعلانات حقيقية حيّة. في `app/ingest.py`:
1. مواقع الإعلانات تحمي صفحاتها ضد البوتات (Cloudflare)، فتحتاج على سيرفرك أحد:
   - **بروكسي/متصفّح آلي** (ScraperAPI / Bright Data / Playwright)، أو
   - **API بيانات سيارات للإمارات** (أنظف وأقل صيانة).
2. نفّذ `HttpListingProvider._fetch_raw` لينادي مصدرك ويرجّع إعلانات.
3. شغّل التحديث دورياً (cron يومي):
   ```bash
   python -m app.ingest
   ```
   يسحب الإعلانات → يحسب median/low/high لكل سنة → يحدّث `market_stats.json`.

> البيانات الحالية في `market_stats.json` لقطة حقيقية مجمّعة يدوياً كبداية،
> وتُستبدَل تلقائياً بمجرد توصيل المصدر الحي.

## النشر (مختصر)
- استضافة بسيطة: Render / Railway / Fly.io / VPS.
- شغّل: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
- اضبط `API_BASE_URL` في التطبيق على رابط السيرفر العام (https).
