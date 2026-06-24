import 'package:flutter/material.dart';

import '../models/search_filters.dart';
import 'widgets/brand_widgets.dart';

/// Show the filter sheet seeded with [initial]. Resolves to the edited
/// [SearchFilters] when the user taps "Apply", or `null` if they dismiss it.
Future<SearchFilters?> showFilterSheet(
  BuildContext context,
  SearchFilters initial,
) {
  return showModalBottomSheet<SearchFilters>(
    context: context,
    isScrollControlled: true,
    showDragHandle: true,
    builder: (context) => _FilterSheet(initial: initial),
  );
}

class _FilterSheet extends StatefulWidget {
  const _FilterSheet({required this.initial});

  final SearchFilters initial;

  @override
  State<_FilterSheet> createState() => _FilterSheetState();
}

class _FilterSheetState extends State<_FilterSheet> {
  late double _distanceKm = widget.initial.maxDistanceKm;

  void _apply() {
    Navigator.of(context).pop(
      SearchFilters(maxDistanceKm: _distanceKm),
    );
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Padding(
      padding: EdgeInsets.only(
        left: 24,
        right: 24,
        top: 8,
        bottom: 24 + MediaQuery.of(context).viewInsets.bottom,
      ),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text('Filters', style: theme.textTheme.headlineSmall),
          const SizedBox(height: 8),
          Text(
            "Showing what you can do today, from now until the early hours.",
            style: theme.textTheme.bodyMedium
                ?.copyWith(color: theme.colorScheme.onSurfaceVariant),
          ),
          const SizedBox(height: 24),

          // --- Max distance (the only remaining filter) ---
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text('Max distance', style: theme.textTheme.titleMedium),
              Text(
                '${_distanceKm.round()} km',
                style: theme.textTheme.titleMedium?.copyWith(
                  color: theme.colorScheme.primary,
                ),
              ),
            ],
          ),
          Slider(
            value: _distanceKm,
            min: SearchFilters.minDistanceKm,
            max: SearchFilters.maxAllowedDistanceKm,
            divisions: (SearchFilters.maxAllowedDistanceKm -
                    SearchFilters.minDistanceKm)
                .round(),
            label: '${_distanceKm.round()} km',
            onChanged: (value) => setState(() => _distanceKm = value),
          ),
          const SizedBox(height: 28),

          PrimaryButton(
            onPressed: _apply,
            label: 'Apply filters',
            icon: Icons.check_rounded,
            expand: true,
          ),
        ],
      ),
    );
  }
}
