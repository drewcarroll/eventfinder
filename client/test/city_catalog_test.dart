import 'package:event_swiper/src/data/city_catalog.dart';
import 'package:flutter_test/flutter_test.dart';

List<City> _cities() => const [
      City(name: 'New York', state: 'NY', latitude: 40.7, longitude: -74.0),
      City(name: 'San Antonio', state: 'TX', latitude: 29.4, longitude: -98.5),
      City(name: 'San Diego', state: 'CA', latitude: 32.7, longitude: -117.2),
      City(name: 'San Francisco', state: 'CA', latitude: 37.8, longitude: -122.4),
      City(name: 'Santa Ana', state: 'CA', latitude: 33.7, longitude: -117.9),
      // A name where the query appears only mid-string.
      City(name: 'Mountain View', state: 'CA', latitude: 37.4, longitude: -122.1),
    ];

void main() {
  group('CityCatalog.searchIn', () {
    test('empty query returns nothing', () {
      expect(CityCatalog.searchIn(_cities(), ''), isEmpty);
      expect(CityCatalog.searchIn(_cities(), '   '), isEmpty);
    });

    test('prefix matches come back in catalog (population) order', () {
      final hits = CityCatalog.searchIn(_cities(), 'san');
      expect(
        hits.map((c) => c.name),
        ['San Antonio', 'San Diego', 'San Francisco', 'Santa Ana'],
      );
    });

    test('is case-insensitive and matches "City, ST" too', () {
      final hits = CityCatalog.searchIn(_cities(), 'NEW YORK, NY');
      expect(hits.single.name, 'New York');
    });

    test('prefix matches rank above mid-string contains matches', () {
      // "view" is a prefix of nothing but appears inside "Mountain View".
      final hits = CityCatalog.searchIn(_cities(), 'view');
      expect(hits.single.name, 'Mountain View');
    });

    test('respects the limit', () {
      final hits = CityCatalog.searchIn(_cities(), 'san', limit: 2);
      expect(hits.length, 2);
      expect(hits.first.name, 'San Antonio');
    });

    test('toLocation carries coordinates and a "City, ST" label', () {
      final loc = _cities().first.toLocation();
      expect(loc.displayName, 'New York, NY');
      expect(loc.latitude, 40.7);
      expect(loc.longitude, -74.0);
    });
  });
}
