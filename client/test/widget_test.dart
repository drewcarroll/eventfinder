import 'package:event_swiper/src/models/event.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  test('Event.fromJson parses backend payload', () {
    final event = Event.fromJson({
      'id': 'e1',
      'title': 'Jazz Night',
      'description': 'Live jazz downtown',
      'category': 'music',
      'source_url': 'https://example.com',
      'image_url': null,
    });

    expect(event.id, 'e1');
    expect(event.title, 'Jazz Night');
    expect(event.category, 'music');
  });

  test('Event.fromJson parses distance and start time', () {
    final event = Event.fromJson({
      'id': 'e2',
      'title': 'Gallery Opening',
      'description': '',
      'category': 'art',
      'source_url': '',
      'distance_km': 3.4,
      'starts_at': '2030-06-15T20:00:00',
    });

    expect(event.distanceKm, 3.4);
    expect(event.startsAt, DateTime(2030, 6, 15, 20));
  });

  test('Event.fromJson tolerates missing distance and start time', () {
    final event = Event.fromJson({
      'id': 'e3',
      'title': 'Open Mic',
      'description': '',
      'category': 'general',
      'source_url': '',
    });

    expect(event.distanceKm, isNull);
    expect(event.startsAt, isNull);
  });

  test('Event.fromJson parses availability windows', () {
    final event = Event.fromJson({
      'id': 'e5',
      'title': 'Show',
      'description': '',
      'category': 'music',
      'source_url': '',
      'availability_times': [
        {'starts_at': '2030-06-15T20:00:00', 'ends_at': '2030-06-15T23:00:00'},
        {'starts_at': 'bad', 'ends_at': '2030-06-15T23:00:00'}, // dropped
      ],
    });

    expect(event.availabilityTimes.length, 1);
    expect(event.availabilityTimes.first.start, DateTime(2030, 6, 15, 20));
    expect(event.availabilityTimes.first.end, DateTime(2030, 6, 15, 23));
  });

  test('Event survives a toJson/fromJson round-trip', () {
    // card_data sent with each swipe is the event serialized via toJson; the
    // backend echoes it back in the yes list, where it is parsed again.
    final original = Event(
      id: 'e4',
      title: 'Rooftop Set',
      description: 'sunset DJ',
      category: 'music',
      sourceUrl: 'https://example.com',
      imageUrl: 'https://img.example.com/1.jpg',
      distanceKm: 2.5,
      startsAt: DateTime(2030, 6, 15, 20),
      availabilityTimes: [
        EventWindow(
          start: DateTime(2030, 6, 15, 20),
          end: DateTime(2030, 6, 15, 23),
        ),
      ],
    );

    final restored = Event.fromJson(original.toJson());

    expect(restored.id, original.id);
    expect(restored.title, original.title);
    expect(restored.description, original.description);
    expect(restored.category, original.category);
    expect(restored.sourceUrl, original.sourceUrl);
    expect(restored.imageUrl, original.imageUrl);
    expect(restored.distanceKm, original.distanceKm);
    expect(restored.startsAt, original.startsAt);
    expect(restored.availabilityTimes.length, 1);
    expect(restored.availabilityTimes.first.start, DateTime(2030, 6, 15, 20));
    expect(restored.availabilityTimes.first.end, DateTime(2030, 6, 15, 23));
  });
}
