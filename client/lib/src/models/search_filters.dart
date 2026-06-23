// The filters a user sets before (and during) a swipe session: how far to
// look and what time window the events should fall in. [SearchFilters] is a
// plain, immutable value object that does not depend on the current time —
// call [SearchFilters.resolveWindow] with "now" to turn a preset like
// [TimeRange.tonight] into a concrete start/end window.

/// A concrete `[start, end]` instant range, resolved from a [TimeRange].
class DateWindow {
  const DateWindow(this.start, this.end);

  final DateTime start;
  final DateTime end;
}

/// The time-range presets offered on the filter sheet.
enum TimeRange {
  tonight('Tonight'),
  thisWeekend('This weekend'),
  custom('Custom');

  const TimeRange(this.label);

  /// Human-readable label shown in the UI.
  final String label;
}

class SearchFilters {
  const SearchFilters({
    this.maxDistanceKm = defaultMaxDistanceKm,
    this.timeRange = TimeRange.tonight,
    this.customStart,
    this.customEnd,
  });

  /// Sensible defaults and bounds for the distance slider.
  static const double defaultMaxDistanceKm = 25;
  static const double minDistanceKm = 1;
  static const double maxAllowedDistanceKm = 100;

  /// How far out to search, in kilometres.
  final double maxDistanceKm;

  /// The selected time-range preset.
  final TimeRange timeRange;

  /// Start/end of the custom window. Only meaningful when
  /// [timeRange] is [TimeRange.custom]; otherwise ignored.
  final DateTime? customStart;
  final DateTime? customEnd;

  /// Resolve [timeRange] into a concrete window relative to [now].
  ///
  /// - [TimeRange.tonight]: from now until the end of today.
  /// - [TimeRange.thisWeekend]: the upcoming (or current) Sat–Sun, never
  ///   reaching into the past.
  /// - [TimeRange.custom]: the user-picked [customStart]/[customEnd],
  ///   falling back to "tonight" if either is unset.
  DateWindow resolveWindow(DateTime now) {
    switch (timeRange) {
      case TimeRange.tonight:
        return DateWindow(now, _endOfDay(now));
      case TimeRange.thisWeekend:
        // Saturday of the current week (may be in the past if it's Sunday).
        final daysToSaturday = DateTime.saturday - now.weekday;
        final saturday = _startOfDay(now).add(Duration(days: daysToSaturday));
        final sunday = saturday.add(const Duration(days: 1));
        final start = saturday.isAfter(now) ? saturday : now;
        return DateWindow(start, _endOfDay(sunday));
      case TimeRange.custom:
        final start = customStart ?? now;
        final end = customEnd ?? _endOfDay(now);
        return DateWindow(start, end);
    }
  }

  /// A short description of the active time range, for the app bar.
  String get timeRangeSummary {
    if (timeRange == TimeRange.custom &&
        customStart != null &&
        customEnd != null) {
      return '${_shortDate(customStart!)} – ${_shortDate(customEnd!)}';
    }
    return timeRange.label;
  }

  SearchFilters copyWith({
    double? maxDistanceKm,
    TimeRange? timeRange,
    DateTime? customStart,
    DateTime? customEnd,
  }) {
    return SearchFilters(
      maxDistanceKm: maxDistanceKm ?? this.maxDistanceKm,
      timeRange: timeRange ?? this.timeRange,
      customStart: customStart ?? this.customStart,
      customEnd: customEnd ?? this.customEnd,
    );
  }

  static DateTime _startOfDay(DateTime d) => DateTime(d.year, d.month, d.day);

  static DateTime _endOfDay(DateTime d) =>
      DateTime(d.year, d.month, d.day, 23, 59, 59);

  static String _shortDate(DateTime d) => '${d.month}/${d.day}';
}
