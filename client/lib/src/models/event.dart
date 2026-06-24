/// One window during which an idea is available — a real start and end time
/// pulled from the source, shown on the card as a range (e.g. "8:00–11:00 PM").
class EventWindow {
  const EventWindow({required this.start, required this.end});

  final DateTime start;
  final DateTime end;

  /// Parse a `{starts_at, ends_at}` object, or `null` when either bound is
  /// missing or unparseable (so a half-formed window is dropped, not shown).
  static EventWindow? tryParse(Object? json) {
    if (json is! Map<String, dynamic>) return null;
    final start = _parseTime(json['starts_at']);
    final end = _parseTime(json['ends_at']);
    if (start == null || end == null) return null;
    return EventWindow(start: start, end: end);
  }

  Map<String, dynamic> toJson() => {
        'starts_at': start.toIso8601String(),
        'ends_at': end.toIso8601String(),
      };

  static DateTime? _parseTime(Object? value) {
    if (value is String && value.isNotEmpty) return DateTime.tryParse(value);
    return null;
  }
}

class Event {
  const Event({
    required this.id,
    required this.title,
    required this.description,
    required this.category,
    required this.sourceUrl,
    this.imageUrl,
    this.distanceKm,
    this.startsAt,
    this.availabilityTimes = const [],
  });

  final String id;
  final String title;
  final String description;
  final String category;
  final String sourceUrl;
  final String? imageUrl;

  /// Distance from the user's search origin, in kilometers. `null` when the
  /// card's location or the search origin is unknown. Derived per request by
  /// the backend, so it is read-only here.
  final double? distanceKm;

  /// Primary occurrence time. Naive UTC in the payload; parsed as-is for
  /// display (the wall-clock components are what we show). `null` if absent.
  final DateTime? startsAt;

  /// The concrete time ranges the idea is available today. Preferred over
  /// [startsAt] for display — a card shows its first window as a start–end
  /// range. Empty when the source gave no real times (we then show no time
  /// rather than a misleading one).
  final List<EventWindow> availabilityTimes;

  factory Event.fromJson(Map<String, dynamic> json) {
    return Event(
      id: json['id'] as String,
      title: json['title'] as String,
      description: json['description'] as String? ?? '',
      category: json['category'] as String? ?? 'general',
      sourceUrl: json['source_url'] as String? ?? '',
      imageUrl: json['image_url'] as String?,
      distanceKm: (json['distance_km'] as num?)?.toDouble(),
      startsAt: switch (json['starts_at']) {
        final String s when s.isNotEmpty => DateTime.tryParse(s),
        _ => null,
      },
      availabilityTimes: switch (json['availability_times']) {
        final List<dynamic> list => list
            .map(EventWindow.tryParse)
            .whereType<EventWindow>()
            .toList(),
        _ => const [],
      },
    );
  }

  /// Serialize back to the backend's card shape. Used as the `card_data`
  /// snapshot stored with each swipe; the keys mirror [Event.fromJson] so a
  /// card round-trips when the backend echoes the saved yes list back.
  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'title': title,
      'description': description,
      'category': category,
      'source_url': sourceUrl,
      'image_url': imageUrl,
      'distance_km': distanceKm,
      'starts_at': startsAt?.toIso8601String(),
      'availability_times':
          availabilityTimes.map((w) => w.toJson()).toList(),
    };
  }
}
