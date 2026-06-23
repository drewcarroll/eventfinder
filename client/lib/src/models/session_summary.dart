/// A past swiping session as shown in the history list: when it happened and
/// a few headline numbers. The full yes list is fetched separately when a
/// session is opened (see [SessionDetail]).
class SessionSummary {
  const SessionSummary({
    required this.id,
    required this.swipeCount,
    required this.yesCount,
    this.createdAt,
    this.location,
    this.timeRange,
    this.distance,
  });

  final String id;

  /// When the session was run. Naive UTC in the payload; parsed as-is for
  /// display, like [Event.startsAt]. `null` if absent.
  final DateTime? createdAt;

  final String? location;
  final String? timeRange;
  final double? distance;

  /// Total decisions made this run.
  final int swipeCount;

  /// How many of them expressed interest (the size of the yes list).
  final int yesCount;

  factory SessionSummary.fromJson(Map<String, dynamic> json) {
    return SessionSummary(
      id: json['session_id'] as String,
      createdAt: switch (json['created_at']) {
        final String s when s.isNotEmpty => DateTime.tryParse(s),
        _ => null,
      },
      location: json['location'] as String?,
      timeRange: json['time_range'] as String?,
      distance: (json['distance'] as num?)?.toDouble(),
      swipeCount: (json['swipe_count'] as num?)?.toInt() ?? 0,
      yesCount: (json['yes_count'] as num?)?.toInt() ?? 0,
    );
  }
}
