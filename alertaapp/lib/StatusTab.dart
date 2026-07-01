import 'dart:async'; // Добавляем импорт для работы с таймером
import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'main.dart';

class StatusTab extends StatefulWidget {
  const StatusTab({super.key});

  @override
  State<StatusTab> createState() => _StatusTabState();
}

class _StatusTabState extends State<StatusTab> {
  late Future<List<Map<String, dynamic>>> _serversFuture;
  Timer? _refreshTimer; // Переменная для хранения таймера

  @override
  void initState() {
    super.initState();
    _serversFuture = _checkServers();

    // Запускаем таймер на каждые 5 минут
    _refreshTimer = Timer.periodic(const Duration(minutes: 1), (timer) {
      _handleRefresh();
    });
  }

  @override
  void dispose() {
    _refreshTimer?.cancel(); // Обязательно уничтожаем таймер при закрытии экрана
    super.dispose();
  }

  Future<void> _handleRefresh() async {
    if (!mounted) return;
    setState(() {
      _serversFuture = _checkServers();
    });
  }

  Future<List<Map<String, dynamic>>> _checkServers() async {
    final userId = supabase.auth.currentUser?.id;
    if (userId == null) return [];

    final data = await supabase.from('profiles').select('urls').eq('id', userId).maybeSingle();
    if (data == null) return [];

    final List<dynamic> urls = data['urls'] ?? [];
    List<Map<String, dynamic>> results = [];

    for (var url in urls) {
      try {
        final response = await http.get(Uri.parse(url.toString())).timeout(const Duration(seconds: 5));
        results.add({
          'url': url,
          'isOnline': response.statusCode == 200,
          'status': response.statusCode.toString()
        });
      } catch (_) {
        results.add({'url': url, 'isOnline': false, 'status': 'Error/Timeout'});
      }
    }
    return results;
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Состояние серверов')),
      body: RefreshIndicator(
        onRefresh: _handleRefresh,
        child: FutureBuilder<List<Map<String, dynamic>>>(
          future: _serversFuture,
          builder: (context, snapshot) {
            if (snapshot.connectionState == ConnectionState.waiting) {
              return const Center(child: CircularProgressIndicator());
            }
            if (!snapshot.hasData || snapshot.data!.isEmpty) {
              return const Center(
                child: SingleChildScrollView(
                  physics: AlwaysScrollableScrollPhysics(),
                  child: Text('Сервера еще не добавлены.'),
                ),
              );
            }

            return ListView.builder(
              physics: const AlwaysScrollableScrollPhysics(),
              itemCount: snapshot.data!.length,
              itemBuilder: (context, index) {
                final server = snapshot.data![index];
                return ListTile(
                  title: Text(server['url']),
                  subtitle: Text('Статус: ${server['status']}'),
                  leading: CircleAvatar(
                    backgroundColor: server['isOnline'] ? Colors.green : Colors.red,
                  ),
                );
              },
            );
          },
        ),
      ),
    );
  }
}