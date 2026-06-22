import 'package:flutter/material.dart';

import '../data/auth_service.dart';
import '../data/event_api.dart';
import '../models/event.dart';

class FeedScreen extends StatefulWidget {
  const FeedScreen({
    super.key,
    required this.api,
    required this.authService,
  });

  final EventApi api;
  final AuthService authService;

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
      final events = await widget.api.fetchFeed('live music near me');
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

  Future<void> _swipe(Event event, String direction) async {
    await widget.api.recordSwipe(event.id, direction);
    setState(() {
      _events = _events.where((e) => e.id != event.id).toList();
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Event Swiper'),
        actions: [
          IconButton(
            icon: const Icon(Icons.logout),
            onPressed: widget.authService.signOut,
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
