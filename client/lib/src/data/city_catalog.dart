import 'dart:convert';

import 'package:flutter/services.dart' show rootBundle;

import '../models/resolved_location.dart';

/// One US city the user can pick as their search location.
class City {
  const City({
    required this.name,
    required this.state,
    required this.latitude,
    required this.longitude,
  });

  final String name;
  final String state; // two-letter abbreviation, e.g. "CA"
  final double latitude;
  final double longitude;

  /// "Austin, TX" — what the type-ahead shows and what the location is
  /// labelled as once chosen.
  String get label => '$name, $state';

  /// The picked location passed to the rest of the app.
  ResolvedLocation toLocation() => ResolvedLocation(
        latitude: latitude,
        longitude: longitude,
        displayName: label,
      );
}

/// An offline catalog of the ~1,000 most-populous US cities, used to power the
/// location type-ahead entirely on-device — no network, no geocoder latency,
/// and instant matches as the user types.
///
/// The bundled asset is pre-sorted by population (largest first), so simply
/// preserving its order surfaces the city people most likely mean first.
class CityCatalog {
  CityCatalog({this.assetPath = 'assets/us_cities.json'});

  final String assetPath;

  List<City> _cities = const [];
  bool _loaded = false;

  bool get isLoaded => _loaded;

  /// Load the bundled city list once. Safe to call repeatedly.
  Future<void> load() async {
    if (_loaded) return;
    final raw = await rootBundle.loadString(assetPath);
    _cities = parse(raw);
    _loaded = true;
  }

  /// Parse the asset JSON into cities. Exposed for tests.
  static List<City> parse(String rawJson) {
    final list = jsonDecode(rawJson) as List<dynamic>;
    return [
      for (final e in list.cast<Map<String, dynamic>>())
        City(
          name: e['n'] as String,
          state: e['s'] as String,
          latitude: (e['lat'] as num).toDouble(),
          longitude: (e['lng'] as num).toDouble(),
        ),
    ];
  }

  /// Cities matching [query], best first, capped at [limit]. Matches the city
  /// name (or "City, ST") case-insensitively; names that *start with* the
  /// query rank above ones that merely contain it, and within each group the
  /// catalog's population order is preserved.
  List<City> search(String query, {int limit = 8}) {
    return searchIn(_cities, query, limit: limit);
  }

  /// Pure search over an explicit list — exposed for tests.
  static List<City> searchIn(
    List<City> cities,
    String query, {
    int limit = 8,
  }) {
    final q = query.trim().toLowerCase();
    if (q.isEmpty) return const [];
    final prefix = <City>[];
    final contains = <City>[];
    for (final c in cities) {
      final name = c.name.toLowerCase();
      if (name.startsWith(q) || c.label.toLowerCase().startsWith(q)) {
        prefix.add(c);
      } else if (name.contains(q)) {
        contains.add(c);
      }
      if (prefix.length >= limit) break;
    }
    return [...prefix, ...contains].take(limit).toList();
  }
}
