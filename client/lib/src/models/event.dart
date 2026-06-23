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
    };
  }
}
