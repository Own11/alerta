import 'package:flutter/material.dart';
import 'main.dart';

class AddLinksTab extends StatefulWidget {
  const AddLinksTab({super.key});

  @override
  State<AddLinksTab> createState() => _AddLinksTabState();
}

class _AddLinksTabState extends State<AddLinksTab> {
  final _urlController = TextEditingController();
  final _apiController = TextEditingController();

  Future<void> _saveData(String column, String value) async {
    if (value.isEmpty) return;
    final userId = supabase.auth.currentUser?.id;
    if (userId == null) return;

    try {
      // 1. Меняем .single() на .maybeSingle()
      final profile = await supabase.from('profiles').select(column).eq('id', userId).maybeSingle();

      // Если профиля ещё нет, создаем пустой список
      List<dynamic> currentList = [];
      if (profile != null) {
        currentList = profile[column] ?? [];
      }

      // 2. Добавляем в него новое значение
      currentList.add(value);

      // 3. Используем upsert вместо update, чтобы строка создалась автоматически
      await supabase.from('profiles').upsert({
        'id': userId,
        column: currentList,
      });

      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Успешно сохранено!')));
        _urlController.clear();
        _apiController.clear();
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('Ошибка: $e')));
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Добавить ресурсы')),
      body: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          children: [
            TextField(controller: _urlController, decoration: const InputDecoration(labelText: 'Ссылка на сервер (URL)')),
            const SizedBox(height: 10),
            ElevatedButton(onPressed: () => _saveData('urls', _urlController.text.trim()), child: const Text('Добавить Сервер')),
            const Divider(height: 40),
            TextField(controller: _apiController, decoration: const InputDecoration(labelText: 'Ссылка на API')),
            const SizedBox(height: 10),
            ElevatedButton(onPressed: () => _saveData('api', _apiController.text.trim()), child: const Text('Добавить API')),
          ],
        ),
      ),
    );
  }
}