import 'package:flutter/material.dart';

import '../data/auth_service.dart';
import '../data/event_api.dart';
import '../data/location_service.dart';
import '../models/event.dart';

/// The interest the feed searches for. Combined with the session location to
/// form the backend query, e.g. "live music near Austin, Texas".
const String _interest = 'live music';

class FeedScreen extends StatefulWidget {
  const FeedScreen({
    super.key,
    required this.api,
    required this.authService,
    required this.locationService,
  });

  final EventApi api;
  final AuthService authService;
  final LocationService locationService;

  @override
  State<FeedScreen> createState() => _FeedScreenState();
}

class _FeedScreenState extends State<FeedScreen> {
  List<Event> _events = [];
  bool _loading = true;
  String? _error;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      // Provision/refresh the user record on the backend before fetching.
      await widget.api.syncUser();
      // Search around the session location: the manual override if set,
      // otherwise "near me" (the device's GPS position).
      final query = '$_interest near ${widget.locationService.searchLabel}';
      final events = await widget.api.fetchFeed(query);
      setState(() {
        _events = events;
        _loading = false;
      });
    } catch (e) {
      setState(() {
        _error = '$e';
        _loading = false;
      });
    }
  }

  Future<void> _signOut() async {
    try {
      // On success the auth-state stream emits null and routes back to
      // the sign-in screen automatically.
      await widget.authService.signOut();
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Sign-out failed: $e')),
        );
      }
    }
  }

  Future<void> _swipe(Event event, String direction) async {
    await widget.api.recordSwipe(event.id, direction);
    setState(() {
      _events = _events.where((e) => e.id != event.id).toList();
    });
  }

  /// Prompt the user for a location, resolve it to coordinates on the
  /// backend, and override the session's search location with it.
  Future<void> _changeLocation() async {
    final location = widget.locationService;
    final controller = TextEditingController(
      text: location.manualOverride?.displayName ?? '',
    );

    final query = await showDialog<String>(
      context: context,
      builder: (context) {
        return AlertDialog(
          title: const Text('Search a different spot'),
          content: TextField(
            controller: controller,
            autofocus: true,
            textInputAction: TextInputAction.search,
            decoration: const InputDecoration(
              hintText: 'e.g. Austin, TX',
              labelText: 'Location',
            ),
            onSubmitted: (value) => Navigator.of(context).pop(value),
          ),
          actions: [
            if (location.hasOverride)
              TextButton(
                onPressed: () => Navigator.of(context).pop('__use_gps__'),
                child: const Text('Use my location'),
              ),
            TextButton(
              onPressed: () => Navigator.of(context).pop(),
              child: const Text('Cancel'),
            ),
            FilledButton(
              onPressed: () =>
                  Navigator.of(context).pop(controller.text),
              child: const Text('Search'),
            ),
          ],
        );
      },
    );

    if (query == null) return; // Cancelled.

    if (query == '__use_gps__') {
      location.clearOverride();
      await _load();
      return;
    }

    final trimmed = query.trim();
    if (trimmed.isEmpty) return;

    try {
      final resolved = await widget.api.resolveLocation(trimmed);
      location.setManualOverride(resolved);
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Searching near ${resolved.displayName}')),
      );
      await _load();
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('$e')),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    final location = widget.locationService;
    final label = location.hasOverride
        ? location.manualOverride!.displayName
        : 'My location';
    return Scaffold(
      appBar: AppBar(
        title: const Text('Event Swiper'),
        actions: [
          TextButton.icon(
            onPressed: _changeLocation,
            icon: Icon(
              location.hasOverride ? Icons.place : Icons.my_location,
              color: Colors.white,
            ),
            label: Text(
              label,
              overflow: TextOverflow.ellipsis,
              style: const TextStyle(color: Colors.white),
            ),
            style: TextButton.styleFrom(
              maximumSize: const Size(180, 48),
            ),
          ),
          IconButton(
            icon: const Icon(Icons.logout),
            tooltip: 'Sign out',
            onPressed: _signOut,
          ),
        ],
      ),
      body: _buildBody(),
    );
  }

  Widget _buildBody() {
    if (_loading) {
      return const Center(child: CircularProgressIndicator());
    }
    if (_error != null) {
      return Center(child: Text('Error: $_error'));
    }
    if (_events.isEmpty) {
      return const Center(child: Text('No more events. Check back later!'));
    }

    final event = _events.first;
    return Padding(
      padding: const EdgeInsets.all(16),
      child: Column(
        children: [
          Expanded(
            child: Card(
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      event.title,
                      style: Theme.of(context).textTheme.headlineSmall,
                    ),
                    const SizedBox(height: 8),
                    Chip(label: Text(event.category)),
                    const SizedBox(height: 16),
                    Expanded(child: Text(event.description)),
                  ],
                ),
              ),
            ),
          ),
          const SizedBox(height: 16),
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceEvenly,
            children: [
              FloatingActionButton(
                heroTag: 'pass',
                backgroundColor: Colors.red,
                onPressed: () => _swipe(event, 'pass'),
                child: const Icon(Icons.close),
              ),
              FloatingActionButton(
                heroTag: 'super',
                backgroundColor: Colors.blue,
                onPressed: () => _swipe(event, 'super_like'),
                child: const Icon(Icons.star),
              ),
              FloatingActionButton(
                heroTag: 'like',
                backgroundColor: Colors.green,
                onPressed: () => _swipe(event, 'like'),
                child: const Icon(Icons.favorite),
              ),
            ],
          ),
        ],
      ),
    );
  }
}
