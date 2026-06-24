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
  late TimeRange _timeRange = widget.initial.timeRange;
  late DateTime? _customStart = widget.initial.customStart;
  late DateTime? _customEnd = widget.initial.customEnd;

  void _apply() {
    Navigator.of(context).pop(
      SearchFilters(
        maxDistanceKm: _distanceKm,
        timeRange: _timeRange,
        customStart: _customStart,
        customEnd: _customEnd,
      ),
    );
  }

  Future<void> _pickCustomRange() async {
    final now = DateTime.now();
    final range = await showDateRangePicker(
      context: context,
      firstDate: DateTime(now.year, now.month, now.day),
      lastDate: now.add(const Duration(days: 365)),
      initialDateRange: _customStart != null && _customEnd != null
          ? DateTimeRange(start: _customStart!, end: _customEnd!)
          : null,
    );
    if (range == null) return;
    setState(() {
      // Cover the full days the user picked.
      _customStart = DateTime(
        range.start.year,
        range.start.month,
        range.start.day,
      );
      _customEnd = DateTime(
        range.end.year,
        range.end.month,
        range.end.day,
        23,
        59,
        59,
      );
    });
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
          const SizedBox(height: 24),

          // --- Max distance ---
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
          const SizedBox(height: 16),

          // --- Time range ---
          Text('When', style: theme.textTheme.titleMedium),
          const SizedBox(height: 12),
          Wrap(
            spacing: 8,
            children: [
              for (final range in TimeRange.values)
                ChoiceChip(
                  label: Text(range.label),
                  selected: _timeRange == range,
                  onSelected: (_) {
                    setState(() => _timeRange = range);
                    if (range == TimeRange.custom) _pickCustomRange();
                  },
                ),
            ],
          ),
          if (_timeRange == TimeRange.custom) ...[
            const SizedBox(height: 12),
            OutlinedButton.icon(
              onPressed: _pickCustomRange,
              icon: const Icon(Icons.date_range),
              label: Text(
                _customStart != null && _customEnd != null
                    ? '${_fmt(_customStart!)} – ${_fmt(_customEnd!)}'
                    : 'Pick dates',
              ),
            ),
          ],
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

  static String _fmt(DateTime d) => '${d.month}/${d.day}';
}
