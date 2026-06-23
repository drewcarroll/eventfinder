import 'event.dart';

/// One past session in full: its filters, when it ran, and the compiled yes
/// list (the cards swiped right), parsed back into [Event]s for display.
class SessionDetail {
  const SessionDetail({
    required this.id,
    required this.swipeCount,
    required this.liked,
    this.createdAt,
    this.location,
    this.timeRange,
    this.distance,
  });

  final String id;
  final DateTime? createdAt;
  final String? location;
  final String? timeRange;
  final double? distance;

  /// Total decisions made this run.
  final int swipeCount;

  /// The events swiped right, in the order they were liked.
  final List<Event> liked;

  factory SessionDetail.fromJson(Map<String, dynamic> json) {
    final yes = json['yes'] as List<dynamic>? ?? <dynamic>[];
    return SessionDetail(
      id: json['session_id'] as String,
      createdAt: switch (json['created_at']) {
        final String s when s.isNotEmpty => DateTime.tryParse(s),
        _ => null,
      },
      location: json['location'] as String?,
      timeRange: json['time_range'] as String?,
      distance: (json['distance'] as num?)?.toDouble(),
      swipeCount: (json['swipe_count'] as num?)?.toInt() ?? 0,
      liked: yes
          .map((e) => Event.fromJson(e as Map<String, dynamic>))
          .toList(),
    );
  }
}
