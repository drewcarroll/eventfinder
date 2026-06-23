import 'package:flutter/material.dart';

import '../data/event_api.dart';
import '../models/event.dart';
import '../models/session_summary.dart';
import 'event_format.dart';

/// Opens one past session and shows its compiled yes list — the events the
/// user liked that run. Fetches the detail on open; the [summary] is used to
/// title the screen immediately while the list loads.
class SessionDetailScreen extends StatefulWidget {
  const SessionDetailScreen({
    super.key,
    required this.api,
    required this.summary,
  });

  final EventApi api;
  final SessionSummary summary;

  @override
  State<SessionDetailScreen> createState() => _SessionDetailScreenState();
}

class _SessionDetailScreenState extends State<SessionDetailScreen> {
  List<Event>? _liked;
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
      final detail = await widget.api.fetchSession(widget.summary.id);
      if (!mounted) return;
      setState(() {
        _liked = detail.liked;
        _loading = false;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _error = '$e';
        _loading = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    final created = widget.summary.createdAt;
    final title = created != null ? formatEventTime(created) : 'Session';
    return Scaffold(
      appBar: AppBar(title: Text(title)),
      body: _buildBody(),
    );
  }

  Widget _buildBody() {
    if (_loading) {
      return const Center(child: CircularProgressIndicator());
    }
    if (_error != null) {
      return Center(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              const Icon(Icons.error_outline, size: 48),
              const SizedBox(height: 12),
              Text("Couldn't load this session.",
                  style: Theme.of(context).textTheme.titleMedium),
              const SizedBox(height: 8),
              Text(_error!, textAlign: TextAlign.center),
              const SizedBox(height: 16),
              FilledButton.icon(
                onPressed: _load,
                icon: const Icon(Icons.refresh),
                label: const Text('Try again'),
              ),
            ],
          ),
        ),
      );
    }
    return SessionYesList(liked: _liked ?? const []);
  }
}

/// Pure presentation of a session's yes list: an empty state when nothing was
/// liked, otherwise a counted list of the liked events.
class SessionYesList extends StatelessWidget {
  const SessionYesList({super.key, required this.liked});

  /// The events swiped right, in the order they were liked.
  final List<Event> liked;

  @override
  Widget build(BuildContext context) {
    if (liked.isEmpty) {
      return Center(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              const Icon(Icons.favorite_border, size: 48),
              const SizedBox(height: 12),
              Text(
                'No saved events.',
                style: Theme.of(context).textTheme.titleMedium,
              ),
              const SizedBox(height: 8),
              const Text(
                "You didn't like any events in this session.",
                textAlign: TextAlign.center,
              ),
            ],
          ),
        ),
      );
    }
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
        return _LikedTile(event: liked[index - 1]);
      },
    );
  }
}

/// A compact summary of one liked event: title, category, distance, time.
class _LikedTile extends StatelessWidget {
  const _LikedTile({required this.event});

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
      ),
    );
  }
}
