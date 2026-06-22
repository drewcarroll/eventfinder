class Event {
  const Event({
    required this.id,
    required this.title,
    required this.description,
    required this.category,
    required this.sourceUrl,
    this.imageUrl,
  });

  final String id;
  final String title;
  final String description;
  final String category;
  final String sourceUrl;
  final String? imageUrl;

  factory Event.fromJson(Map<String, dynamic> json) {
    return Event(
      id: json['id'] as String,
      title: json['title'] as String,
      description: json['description'] as String? ?? '',
      category: json['category'] as String? ?? 'general',
      sourceUrl: json['source_url'] as String? ?? '',
      imageUrl: json['image_url'] as String?,
    );
  }
}
