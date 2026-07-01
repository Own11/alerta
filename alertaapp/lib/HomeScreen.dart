import 'package:flutter/material.dart';
import 'StatusTab.dart';
import 'MenuTab.dart';
import 'AddLinksTab.dart';

class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key});

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  int _currentIndex = 0;

  final List<Widget> _tabs = [
    const StatusTab(),
    const MenuTab(),
    const AddLinksTab(),
  ];

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: IndexedStack(
        index: _currentIndex,
        children: _tabs,
      ),
      bottomNavigationBar: BottomNavigationBar(
        currentIndex: _currentIndex,
        onTap: (index) {
          setState(() {
            _currentIndex = index;
          });
        },
        items: const [
          BottomNavigationBarItem(icon: Icon(Icons.dns), label: 'Статус'),
          BottomNavigationBarItem(icon: Icon(Icons.restaurant_menu), label: 'Меню'),
          BottomNavigationBarItem(icon: Icon(Icons.add_link), label: 'Добавить'),
        ],
      ),
    );
  }
}