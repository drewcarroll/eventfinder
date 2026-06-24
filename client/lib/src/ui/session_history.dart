import 'package:flutter/material.dart';

import '../data/event_api.dart';
import '../models/session_summary.dart';
import 'event_format.dart';
import 'session_detail_screen.dart';

/// The signed-in user's swipe history, rendered as an embeddable section
/// (no Scaffold/app bar) so it can live inside the Profile tab beneath the
/// profile area. Handles its own loading, error, and empty states; tapping a
/// session opens its compiled yes list.
///
/// Designed to sit inside an outer scroll view: the list itself does not
/// scroll, so the host page owns scrolling.
class SessionHistorySection extends StatefulWidget {
  const SessionHistorySection({super.key, required this.api});

  final EventApi api;

  @override
  State<SessionHistorySection> createState() => _SessionHistorySectionState();
}

class _SessionHistorySectionState extends State<SessionHistorySection> {
  List<SessionSummary> _sessions = [];
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
      final sessions = await widget.api.fetchSessions();
      if (!mounted) return;
      setState(() {
        _sessions = sessions;
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

  void _open(SessionSummary session) {
    Navigator.of(context).push(
      MaterialPageRoute<void>(
        builder: (_) => SessionDetailScreen(api: widget.api, summary: session),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      mainAxisSize: MainAxisSize.min,
      children: [
        Text('Session history', style: Theme.of(context).textTheme.titleMedium),
        const SizedBox(height: 8),
        _buildBody(),
      ],
    );
  }

  Widget _buildBody() {
    if (_loading) {
      return const Padding(
        padding: EdgeInsets.symmetric(vertical: 24),
        // A Row (rather than Center) so it sizes its own height inside the
        // host's unbounded scroll view.
        child: Row(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [CircularProgressIndicator()],
        ),
      );
    }
    if (_error != null) {
      return Padding(
        padding: const EdgeInsets.symmetric(vertical: 16),
        child: Column(
          children: [
            Text("Couldn't load your history.",
                style: Theme.of(context).textTheme.titleSmall),
            const SizedBox(height: 8),
            Text(_error!, textAlign: TextAlign.center),
            const SizedBox(height: 12),
            FilledButton.icon(
              onPressed: _load,
              icon: const Icon(Icons.refresh),
              label: const Text('Try again'),
            ),
          ],
        ),
      );
    }
    return HistoryListView(sessions: _sessions, onTap: _open);
  }
}

/// Pure presentation of the history list: an empty state when there are no
/// sessions, otherwise a tappable list of session summaries. Does not scroll
/// on its own — it expects to be embedded in a scrolling parent.
class HistoryListView extends StatelessWidget {
  const HistoryListView({
    super.key,
    required this.sessions,
    required this.onTap,
  });

  final List<SessionSummary> sessions;
  final void Function(SessionSummary session) onTap;

  @override
  Widget build(BuildContext context) {
    if (sessions.isEmpty) {
      return Padding(
        padding: const EdgeInsets.symmetric(vertical: 24),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Icon(Icons.history, size: 48),
            const SizedBox(height: 12),
            Text(
              'No sessions yet.',
              style: Theme.of(context).textTheme.titleMedium,
            ),
            const SizedBox(height: 8),
            const Text(
              'Your past swipe sessions will show up here once you finish '
              'one.',
              textAlign: TextAlign.center,
            ),
          ],
        ),
      );
    }
    return ListView.separated(
      // Embedded inside another scroll view: shrink to content and let the
      // host handle scrolling.
      shrinkWrap: true,
      physics: const NeverScrollableScrollPhysics(),
      padding: EdgeInsets.zero,
      itemCount: sessions.length,
      separatorBuilder: (_, __) => const SizedBox(height: 8),
      itemBuilder: (context, index) {
        return _SessionTile(session: sessions[index], onTap: onTap);
      },
    );
  }
}

/// A compact summary of one past session: when it ran, where, and how many
/// events were liked out of those swiped.
class _SessionTile extends StatelessWidget {
  const _SessionTile({required this.session, required this.onTap});

  final SessionSummary session;
  final void Function(SessionSummary session) onTap;

  @override
  Widget build(BuildContext context) {
    final title = session.createdAt != null
        ? formatEventTime(session.createdAt!)
        : 'Session';
    final facts = <String>[
      if (session.location != null && session.location!.isNotEmpty)
        session.location!,
      '${session.yesCount} liked',
      '${session.swipeCount} swiped',
    ];
    return Card(
      margin: EdgeInsets.zero,
      child: ListTile(
        leading: const Icon(Icons.event_note),
        title: Text(title),
        subtitle: Text(facts.join(' · ')),
        trailing: const Icon(Icons.chevron_right),
        onTap: () => onTap(session),
      ),
    );
  }
}
