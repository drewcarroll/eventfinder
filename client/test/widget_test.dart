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
}
