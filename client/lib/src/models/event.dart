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
}
