// The filters a user sets for a swipe session. The app's premise is fixed —
// "what can I do today?" — so time is no longer a filter: the feed always
// covers now until the early hours of the next morning (see [DayWindow]).
// Distance is the only thing left to tune, so [SearchFilters] now carries just
// the search radius.

class SearchFilters {
  const SearchFilters({this.maxDistanceKm = defaultMaxDistanceKm});

  /// Sensible defaults and bounds for the distance slider.
  static const double defaultMaxDistanceKm = 25;
  static const double minDistanceKm = 1;
  static const double maxAllowedDistanceKm = 100;

  /// How far out to search, in kilometres.
  final double maxDistanceKm;

  SearchFilters copyWith({double? maxDistanceKm}) {
    return SearchFilters(
      maxDistanceKm: maxDistanceKm ?? this.maxDistanceKm,
    );
  }
}
