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
}
