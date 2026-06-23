import 'package:flutter/foundation.dart';

import '../models/resolved_location.dart';
import 'device_location_service.dart';

/// Holds the location the feed should search around for the current session.
///
/// By default the app uses the device's GPS position ("near me"), captured on
/// the first search via [captureDeviceLocation]. When the user manually picks
/// a different spot, that override takes precedence for the rest of the
/// session (until cleared or the app restarts).
class LocationService extends ChangeNotifier {
  LocationService({DeviceLocationService? deviceLocation})
      : _deviceLocation = deviceLocation ?? const DeviceLocationService();

  final DeviceLocationService _deviceLocation;

  ResolvedLocation? _manualOverride;
  ResolvedLocation? _devicePosition;

  /// The manually chosen location, or `null` when falling back to GPS.
  ResolvedLocation? get manualOverride => _manualOverride;

  /// Whether a manual override is currently in effect.
  bool get hasOverride => _manualOverride != null;

  /// The location the feed should search around: the manual override if set,
  /// otherwise the captured device GPS position. `null` until one is known
  /// (e.g. before permission is granted).
  ResolvedLocation? get activeLocation => _manualOverride ?? _devicePosition;

  /// Whether we have any location to search around yet.
  bool get hasLocation => activeLocation != null;

  /// A short label for the location the feed is searching around, used to
  /// build the search query: the override's name, or the device coordinates.
  /// Falls back to "me" when nothing has been captured.
  String get searchLabel => activeLocation?.displayName ?? 'me';

  /// Request location permission (if needed) and adopt the device's GPS
  /// position as the default search location. Any manual override is left
  /// untouched. Returns the outcome so the UI can fall back to manual entry
  /// when permission is denied or location services are off.
  Future<LocationPermissionOutcome> captureDeviceLocation() async {
    final result = await _deviceLocation.currentPosition();
    if (result.outcome == LocationPermissionOutcome.granted) {
      _devicePosition = ResolvedLocation(
        latitude: result.latitude!,
        longitude: result.longitude!,
        displayName: _formatCoords(result.latitude!, result.longitude!),
      );
      notifyListeners();
    }
    return result.outcome;
  }

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

  /// Format raw coordinates into a compact `"lat, lng"` query fragment.
  static String _formatCoords(double lat, double lng) =>
      '${lat.toStringAsFixed(4)}, ${lng.toStringAsFixed(4)}';
}
