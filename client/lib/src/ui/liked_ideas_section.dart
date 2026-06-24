import 'package:flutter/material.dart';

import '../data/event_api.dart';
import '../models/event.dart';
import 'event_format.dart';
import 'theme/app_theme.dart';

/// The signed-in user's liked ideas — the ones they swiped yes on — rendered
/// as an embeddable section (no Scaffold/app bar) so it can live inside the
/// Profile tab beneath the profile area. Handles its own loading, error, and
/// empty states.
///
/// Designed to sit inside an outer scroll view: the list itself does not
/// scroll, so the host page owns scrolling.
class LikedIdeasSection extends StatefulWidget {
  const LikedIdeasSection({super.key, required this.api});

  final EventApi api;

  @override
  State<LikedIdeasSection> createState() => _LikedIdeasSectionState();
}

class _LikedIdeasSectionState extends State<LikedIdeasSection> {
  List<Event> _ideas = [];
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
      final ideas = await widget.api.fetchLikedIdeas();
      if (!mounted) return;
      setState(() {
        _ideas = ideas;
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

  /// Confirm, then delete a liked idea and drop it from the list. The idea is
  /// only removed from the UI once the backend acknowledges the delete, so a
  /// failed request leaves the list untouched.
  Future<void> _confirmAndDelete(Event idea) async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Remove this idea?'),
        content: Text(
          '"${idea.title}" will be removed from the ideas you said yes to.',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(false),
            child: const Text('Cancel'),
          ),
          FilledButton(
            onPressed: () => Navigator.of(context).pop(true),
            child: const Text('Remove'),
          ),
        ],
      ),
    );
    if (confirmed != true) return;

    try {
      await widget.api.deleteLikedIdea(idea);
      if (!mounted) return;
      setState(() {
        _ideas = _ideas.where((e) => e.id != idea.id).toList();
      });
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text("Couldn't remove the idea: $e")),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      mainAxisSize: MainAxisSize.min,
      children: [
        Row(
          children: [
            const Icon(Icons.favorite_rounded, color: AppColors.like, size: 20),
            const SizedBox(width: 8),
            Text(
              'Ideas you said yes to',
              style: Theme.of(context)
                  .textTheme
                  .titleMedium
                  ?.copyWith(fontWeight: FontWeight.w700),
            ),
          ],
        ),
        const SizedBox(height: 12),
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
            Text("Couldn't load your ideas.",
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
    return LikedIdeasListView(ideas: _ideas, onDelete: _confirmAndDelete);
  }
}

/// Pure presentation of the liked-ideas list: an empty state when there are
/// none, otherwise a list of liked ideas. Does not scroll on its own — it
/// expects to be embedded in a scrolling parent.
class LikedIdeasListView extends StatelessWidget {
  const LikedIdeasListView({
    super.key,
    required this.ideas,
    this.onDelete,
  });

  final List<Event> ideas;

  /// Called when the user asks to remove an idea. When null, tiles render
  /// without a delete affordance (e.g. in pure-presentation tests).
  final ValueChanged<Event>? onDelete;

  @override
  Widget build(BuildContext context) {
    if (ideas.isEmpty) {
      return Padding(
        padding: const EdgeInsets.symmetric(vertical: 24),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Icon(Icons.favorite_border, size: 48),
            const SizedBox(height: 12),
            Text(
              'No liked ideas yet.',
              style: Theme.of(context).textTheme.titleMedium,
            ),
            const SizedBox(height: 8),
            const Text(
              'Swipe right on ideas you like and they\'ll show up here.',
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
      itemCount: ideas.length,
      separatorBuilder: (_, __) => const SizedBox(height: 8),
      itemBuilder: (context, index) => _IdeaTile(
        idea: ideas[index],
        onDelete: onDelete,
      ),
    );
  }
}

/// A compact summary of one liked idea: title, category, distance, time.
class _IdeaTile extends StatelessWidget {
  const _IdeaTile({required this.idea, this.onDelete});

  final Event idea;
  final ValueChanged<Event>? onDelete;

  @override
  Widget build(BuildContext context) {
    final facts = <String>[
      idea.category,
      if (idea.distanceKm != null) formatDistance(idea.distanceKm!),
      if (idea.startsAt != null) formatEventTime(idea.startsAt!),
    ];
    final theme = Theme.of(context);
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: theme.colorScheme.surface,
        borderRadius: BorderRadius.circular(AppRadii.sm),
        border: Border.all(color: theme.dividerColor),
      ),
      child: Row(
        children: [
          Container(
            height: 44,
            width: 44,
            decoration: BoxDecoration(
              color: AppColors.like,
              borderRadius: BorderRadius.circular(12),
            ),
            child: const Icon(Icons.favorite_rounded,
                color: Colors.white, size: 22),
          ),
          const SizedBox(width: 14),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  idea.title,
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: theme.textTheme.titleMedium,
                ),
                const SizedBox(height: 2),
                Text(
                  facts.join(' · '),
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: theme.textTheme.bodyMedium
                      ?.copyWith(color: theme.colorScheme.onSurfaceVariant),
                ),
              ],
            ),
          ),
          if (onDelete != null) ...[
            const SizedBox(width: 8),
            IconButton(
              onPressed: () => onDelete!(idea),
              icon: const Icon(Icons.delete_outline_rounded),
              color: theme.colorScheme.onSurfaceVariant,
              tooltip: 'Remove idea',
              visualDensity: VisualDensity.compact,
            ),
          ],
        ],
      ),
    );
  }
}
