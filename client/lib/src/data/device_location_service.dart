import 'package:geolocator/geolocator.dart';

/// What happened when we tried to read the device's GPS position.
enum LocationPermissionOutcome {
  /// Permission was granted and a fix was obtained.
  granted,

  /// The user declined the OS permission prompt (or it is permanently
  /// denied). The caller should fall back to manual location entry.
  denied,

  /// Location services are turned off device-wide, so no fix is possible.
  serviceDisabled,
}

/// The result of a device-location capture: the outcome plus coordinates
/// when [LocationPermissionOutcome.granted].
class DeviceLocationResult {
  const DeviceLocationResult.granted(this.latitude, this.longitude)
      : outcome = LocationPermissionOutcome.granted;

  const DeviceLocationResult.denied()
      : outcome = LocationPermissionOutcome.denied,
        latitude = null,
        longitude = null;

  const DeviceLocationResult.serviceDisabled()
      : outcome = LocationPermissionOutcome.serviceDisabled,
        latitude = null,
        longitude = null;

  final LocationPermissionOutcome outcome;
  final double? latitude;
  final double? longitude;
}

/// Stateless wrapper around the platform geolocation plugin.
///
/// Isolates the `geolocator` dependency so the rest of the app deals only in
/// [DeviceLocationResult]. Subclass and override [currentPosition] to fake
/// the device in tests.
class DeviceLocationService {
  const DeviceLocationService();

  /// Request location permission (if not already granted) and read the
  /// device's current GPS coordinates.
  ///
  /// Returns [LocationPermissionOutcome.serviceDisabled] if location is off
  /// device-wide, [LocationPermissionOutcome.denied] if the user declines,
  /// and [LocationPermissionOutcome.granted] with coordinates otherwise.
  Future<DeviceLocationResult> currentPosition() async {
    if (!await Geolocator.isLocationServiceEnabled()) {
      return const DeviceLocationResult.serviceDisabled();
    }

    var permission = await Geolocator.checkPermission();
    if (permission == LocationPermission.denied) {
      // First search: show the OS permission prompt.
      permission = await Geolocator.requestPermission();
    }

    if (permission == LocationPermission.denied ||
        permission == LocationPermission.deniedForever) {
      return const DeviceLocationResult.denied();
    }

    final position = await Geolocator.getCurrentPosition();
    return DeviceLocationResult.granted(
      position.latitude,
      position.longitude,
    );
  }
}
