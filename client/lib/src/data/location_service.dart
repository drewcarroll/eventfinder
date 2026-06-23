import 'package:flutter/foundation.dart';

import '../models/resolved_location.dart';

/// Holds the location the feed should search around for the current session.
///
/// By default the app would use the device's GPS position ("near me"). When
/// the user manually picks a different spot, that override takes precedence
/// for the rest of the session (until cleared or the app restarts).
class LocationService extends ChangeNotifier {
  ResolvedLocation? _manualOverride;

  /// The manually chosen location, or `null` when falling back to GPS.
  ResolvedLocation? get manualOverride => _manualOverride;

  /// Whether a manual override is currently in effect.
  bool get hasOverride => _manualOverride != null;

  /// A short label for the location the feed is searching around. Used to
  /// build the search query: the override's name, or "me" for GPS.
  String get searchLabel => _manualOverride?.displayName ?? 'me';

  /// Apply a manually entered location, overriding GPS for the session.
  void setManualOverride(ResolvedLocation location) {
    _manualOverride = location;
    notifyListeners();
  }

  /// Drop the override and fall back to the device's GPS position.
  void clearOverride() {
    if (_manualOverride == null) return;
    _manualOverride = null;
    notifyListeners();
  }
}
