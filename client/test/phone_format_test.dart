import 'package:event_swiper/src/ui/sign_in_screen.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  group('normalizePhoneNumber', () {
    test('assumes +1 for a bare 10-digit US number', () {
      expect(normalizePhoneNumber('6504959501'), '+16504959501');
    });

    test('strips formatting punctuation', () {
      expect(normalizePhoneNumber('(650) 495-9501'), '+16504959501');
    });

    test('keeps a leading 1 as the US country code', () {
      expect(normalizePhoneNumber('1 650 495 9501'), '+16504959501');
    });

    test('passes through an explicit + international number', () {
      expect(normalizePhoneNumber('+44 20 7946 0958'), '+442079460958');
    });

    test('rejects too-short input', () {
      expect(normalizePhoneNumber('12345'), isNull);
    });

    test('rejects empty input', () {
      expect(normalizePhoneNumber('   '), isNull);
    });
  });
}
