import 'package:flutter/material.dart';

import '../models/event.dart';
import 'event_format.dart';

/// Shown when a swipe session ends (the feed is exhausted). It compiles the
/// events the user liked during the session and offers to start a new search.
class ResultsScreen extends StatelessWidget {
  const ResultsScreen({
    super.key,
    required this.liked,
    required this.onNewSearch,
    required this.onSignOut,
  });

  /// The events the user swiped right on, in the order they were liked.
  final List<Event> liked;

  /// Start a fresh search (reloads the feed for a new session).
  final VoidCallback onNewSearch;
  final VoidCallback onSignOut;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Your picks'),
        actions: [
          IconButton(
            icon: const Icon(Icons.logout),
            tooltip: 'Sign out',
            onPressed: onSignOut,
          ),
        ],
      ),
      body: liked.isEmpty ? _buildEmpty(context) : _buildList(context),
      bottomNavigationBar: SafeArea(
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: FilledButton.icon(
            onPressed: onNewSearch,
            icon: const Icon(Icons.search),
            label: const Text('New search'),
          ),
        ),
      ),
    );
  }

  Widget _buildEmpty(BuildContext context) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Icon(Icons.favorite_border, size: 48),
            const SizedBox(height: 12),
            Text(
              "That's everything for now.",
              style: Theme.of(context).textTheme.titleMedium,
            ),
            const SizedBox(height: 8),
            const Text(
              "You didn't save any events this round. "
              'Start a new search to keep looking.',
              textAlign: TextAlign.center,
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildList(BuildContext context) {
    final count = liked.length;
    return ListView.separated(
      padding: const EdgeInsets.all(16),
      itemCount: count + 1,
      separatorBuilder: (_, __) => const SizedBox(height: 8),
      itemBuilder: (context, index) {
        if (index == 0) {
          return Padding(
            padding: const EdgeInsets.only(bottom: 4),
            child: Text(
              count == 1 ? '1 event saved' : '$count events saved',
              style: Theme.of(context).textTheme.titleMedium,
            ),
          );
        }
        return _ResultTile(event: liked[index - 1]);
      },
    );
  }
}

/// A compact summary of one liked event: title, category, distance, time.
class _ResultTile extends StatelessWidget {
  const _ResultTile({required this.event});

  final Event event;

  @override
  Widget build(BuildContext context) {
    final facts = <String>[
      event.category,
      if (event.distanceKm != null) formatDistance(event.distanceKm!),
      if (event.startsAt != null) formatEventTime(event.startsAt!),
    ];
    return Card(
      margin: EdgeInsets.zero,
      child: ListTile(
        leading: const Icon(Icons.favorite, color: Colors.green),
        title: Text(event.title),
        subtitle: Text(facts.join(' · ')),
        isThreeLine: false,
      ),
    );
  }
}
