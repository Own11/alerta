import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'main.dart';

class StatusTab extends StatelessWidget {
  const StatusTab({super.key});

  Future<List<Map<String, dynamic>>> _checkServers() async {
    final userId = supabase.auth.currentUser?.id;
    if (userId == null) return [];

    final data = await supabase.from('profiles').select('urls').eq('id', userId).single();
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
      body: FutureBuilder<List<Map<String, dynamic>>>(
        future: _checkServers(),
        builder: (context, snapshot) {
          if (snapshot.connectionState == ConnectionState.waiting) {
            return const Center(child: CircularProgressIndicator());
          }
          if (!snapshot.hasData || snapshot.data!.isEmpty) {
            return const Center(child: Text('Сервера еще не добавлены.'));
          }

          return ListView.builder(
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
    );
  }
}