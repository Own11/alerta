import 'package:flutter/material.dart';
import 'package:supabase_flutter/supabase_flutter.dart';
import 'AuthScreen.dart';

void main() async {
  WidgetsFlutterBinding.ensureInitialized();

  await Supabase.initialize(
    url: 'https://hzvxqpfxvmadtnypgcyp.supabase.co', // Вставьте ваш URL из Supabase
    anonKey: 'sb_publishable_KWAcCR0DgW1EdhiCOxeC_g_bgCKD53S', // Вставьте ваш Anon Key из Supabase
  );

  runApp(const MyApp());
}

// Глобальная переменная для работы с базой из любого файла
final supabase = Supabase.instance.client;

class MyApp extends StatelessWidget {
  const MyApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Server Monitor',
      theme: ThemeData.dark(), // Красивая тёмная тема
      home: const AuthScreen(),
    );
  }
}