import 'package:event_swiper/src/models/day_window.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  group('DayWindow.today', () {
    test('starts at now', () {
      final now = DateTime(2026, 6, 24, 20, 0);
      expect(DayWindow.today(now).start, now);
    });

    test('evening (8 PM) ends at 4 AM the next morning', () {
      final w = DayWindow.today(DateTime(2026, 6, 24, 20, 0));
      expect(w.end, DateTime(2026, 6, 25, 4, 0));
    });

    test('afternoon (2 PM) ends at 4 AM the next morning', () {
      final w = DayWindow.today(DateTime(2026, 6, 24, 14, 0));
      expect(w.end, DateTime(2026, 6, 25, 4, 0));
    });

    test('early morning (5 AM) ends at 4 AM the next morning', () {
      final w = DayWindow.today(DateTime(2026, 6, 24, 5, 0));
      expect(w.end, DateTime(2026, 6, 25, 4, 0));
    });

    test('before 4 AM (1 AM) ends at 4 AM the same morning', () {
      final w = DayWindow.today(DateTime(2026, 6, 24, 1, 0));
      expect(w.end, DateTime(2026, 6, 24, 4, 0));
    });

    test('exactly 4 AM rolls over to the next morning', () {
      final w = DayWindow.today(DateTime(2026, 6, 24, 4, 0));
      expect(w.end, DateTime(2026, 6, 25, 4, 0));
    });
  });
}
