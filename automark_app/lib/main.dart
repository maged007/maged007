import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';

import 'data/catalog_repository.dart';
import 'screens/home_screen.dart';
import 'theme/app_theme.dart';

void main() {
  runApp(const AutomarkApp());
}

class AutomarkApp extends StatefulWidget {
  const AutomarkApp({super.key});

  @override
  State<AutomarkApp> createState() => _AutomarkAppState();
}

class _AutomarkAppState extends State<AutomarkApp> {
  final _repository = CatalogRepository();
  late final Future<void> _loadFuture;

  @override
  void initState() {
    super.initState();
    _loadFuture = _repository.load();
  }

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'تقدير سعر السيارات',
      debugShowCheckedModeBanner: false,
      theme: AppTheme.light,
      locale: const Locale('ar'),
      supportedLocales: const [Locale('ar')],
      localizationsDelegates: const [
        GlobalMaterialLocalizations.delegate,
        GlobalWidgetsLocalizations.delegate,
        GlobalCupertinoLocalizations.delegate,
      ],
      builder: (context, child) => Directionality(
        textDirection: TextDirection.rtl,
        child: child!,
      ),
      home: FutureBuilder<void>(
        future: _loadFuture,
        builder: (context, snapshot) {
          if (snapshot.connectionState != ConnectionState.done) {
            return const Scaffold(
              body: Center(child: CircularProgressIndicator()),
            );
          }
          if (snapshot.hasError) {
            return Scaffold(
              body: Center(child: Text('خطأ في تحميل البيانات: ${snapshot.error}')),
            );
          }
          return HomeScreen(repository: _repository);
        },
      ),
    );
  }
}
