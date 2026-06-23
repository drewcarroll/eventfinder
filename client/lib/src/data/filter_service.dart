import 'package:flutter/foundation.dart';

import '../models/search_filters.dart';

/// Holds the [SearchFilters] in effect for the current swipe session.
///
/// Mirrors [LocationService]: a session-scoped [ChangeNotifier] wired in
/// `app.dart` so the chosen distance/time range survive feed reloads. It
/// starts with sensible defaults (tonight, default radius), so a session can
/// begin without the user touching the filter sheet first.
class FilterService extends ChangeNotifier {
  SearchFilters _filters = const SearchFilters();

  /// The filters currently applied to the feed.
  SearchFilters get filters => _filters;

  /// Replace the active filters and notify listeners.
  void update(SearchFilters filters) {
    _filters = filters;
    notifyListeners();
  }
}
