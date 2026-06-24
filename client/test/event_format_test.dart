import 'package:event_swiper/src/ui/event_format.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  group('formatTimeRange', () {
    test('same period shows the period once', () {
      final text = formatTimeRange(
        DateTime(2030, 6, 15, 20),
        DateTime(2030, 6, 15, 23),
      );
      expect(text, '8:00 – 11:00 PM');
    });

    test('across noon keeps both periods', () {
      final text = formatTimeRange(
        DateTime(2030, 6, 15, 11),
        DateTime(2030, 6, 15, 14),
      );
      expect(text, '11:00 AM – 2:00 PM');
    });

    test('across midnight reads as evening into the small hours', () {
      final text = formatTimeRange(
        DateTime(2030, 6, 15, 22),
        DateTime(2030, 6, 16, 2),
      );
      expect(text, '10:00 PM – 2:00 AM');
    });
  });
}
