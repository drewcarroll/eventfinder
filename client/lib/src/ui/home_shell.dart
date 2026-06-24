import 'package:flutter/material.dart';

import '../data/auth_service.dart';
import '../data/event_api.dart';
import '../data/filter_service.dart';
import '../data/location_service.dart';
import 'feed_screen.dart';
import 'profile_screen.dart';

/// The signed-in app shell: a two-tab bottom navigation between Home (the
/// swipe feed) and Profile (account + liked ideas). Home is the default tab.
///
/// Both tabs live in an [IndexedStack], so each keeps its state — scroll
/// position, the in-progress deck, loaded liked ideas — while the user
/// switches between them.
class HomeShell extends StatefulWidget {
  const HomeShell({
    super.key,
    required this.api,
    required this.authService,
    required this.locationService,
    required this.filterService,
  });

  final EventApi api;
  final AuthService authService;
  final LocationService locationService;
  final FilterService filterService;

  @override
  State<HomeShell> createState() => _HomeShellState();
}

class _HomeShellState extends State<HomeShell> {
  // Home is the default tab on launch.
  int _index = 0;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: IndexedStack(
        index: _index,
        children: [
          FeedScreen(
            api: widget.api,
            locationService: widget.locationService,
            filterService: widget.filterService,
          ),
          ProfileScreen(
            api: widget.api,
            authService: widget.authService,
          ),
        ],
      ),
      bottomNavigationBar: NavigationBar(
        selectedIndex: _index,
        onDestinationSelected: (index) => setState(() => _index = index),
        destinations: const [
          NavigationDestination(
            icon: Icon(Icons.home_outlined),
            selectedIcon: Icon(Icons.home),
            label: 'Home',
          ),
          NavigationDestination(
            icon: Icon(Icons.person_outline),
            selectedIcon: Icon(Icons.person),
            label: 'Profile',
          ),
        ],
      ),
    );
  }
}
