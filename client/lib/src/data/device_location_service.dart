import 'dart:async';

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

  /// Permission was granted but no fix arrived in time (e.g. an emulator
  /// with no location set, or a slow/indoor GPS). The caller should fall
  /// back to manual location entry rather than wait indefinitely.
  unavailable,
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

  const DeviceLocationResult.unavailable()
      : outcome = LocationPermissionOutcome.unavailable,
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
  /// [LocationPermissionOutcome.unavailable] if no fix arrives in time, and
  /// [LocationPermissionOutcome.granted] with coordinates otherwise.
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

    // Use a cached fix if one is already available — instant, and avoids
    // waiting on the GPS at all.
    final lastKnown = await Geolocator.getLastKnownPosition();
    if (lastKnown != null) {
      return DeviceLocationResult.granted(
        lastKnown.latitude,
        lastKnown.longitude,
      );
    }

    // Otherwise request a fresh fix, but cap how long we wait. On an emulator
    // (or indoors) a fix can take a very long time or never arrive; without a
    // limit the feed spins forever and Android raises an ANR. On timeout,
    // fall back to manual location entry.
    try {
      final position = await Geolocator.getCurrentPosition(
        locationSettings: const LocationSettings(
          accuracy: LocationAccuracy.medium,
          timeLimit: Duration(seconds: 10),
        ),
      );
      return DeviceLocationResult.granted(
        position.latitude,
        position.longitude,
      );
    } on TimeoutException {
      return const DeviceLocationResult.unavailable();
    } on LocationServiceDisabledException {
      return const DeviceLocationResult.serviceDisabled();
    }
  }
}
