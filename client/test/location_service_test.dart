import 'package:event_swiper/src/data/device_location_service.dart';
import 'package:event_swiper/src/data/location_service.dart';
import 'package:event_swiper/src/models/resolved_location.dart';
import 'package:flutter_test/flutter_test.dart';

/// A [DeviceLocationService] that returns a canned result instead of touching
/// the platform geolocation plugin.
class _FakeDeviceLocationService extends DeviceLocationService {
  const _FakeDeviceLocationService(this.result);

  final DeviceLocationResult result;

  @override
  Future<DeviceLocationResult> currentPosition() async => result;
}

void main() {
  group('LocationService.captureDeviceLocation', () {
    test('adopts the device position as the active location when granted',
        () async {
      final service = LocationService(
        deviceLocation: const _FakeDeviceLocationService(
          DeviceLocationResult.granted(30.2672, -97.7431),
        ),
      );

      expect(service.hasLocation, isFalse);

      final outcome = await service.captureDeviceLocation();

      expect(outcome, LocationPermissionOutcome.granted);
      expect(service.hasLocation, isTrue);
      expect(service.activeLocation!.latitude, 30.2672);
      expect(service.activeLocation!.longitude, -97.7431);
      // The coordinates become the query label used to build the feed search.
      expect(service.searchLabel, '30.2672, -97.7431');
    });

    test('does not set a location when permission is denied', () async {
      final service = LocationService(
        deviceLocation: const _FakeDeviceLocationService(
          DeviceLocationResult.denied(),
        ),
      );

      final outcome = await service.captureDeviceLocation();

      expect(outcome, LocationPermissionOutcome.denied);
      expect(service.hasLocation, isFalse);
      expect(service.searchLabel, 'me');
    });

    test('reports when location services are disabled', () async {
      final service = LocationService(
        deviceLocation: const _FakeDeviceLocationService(
          DeviceLocationResult.serviceDisabled(),
        ),
      );

      final outcome = await service.captureDeviceLocation();

      expect(outcome, LocationPermissionOutcome.serviceDisabled);
      expect(service.hasLocation, isFalse);
    });

    test('manual override takes precedence over the captured device position',
        () async {
      final service = LocationService(
        deviceLocation: const _FakeDeviceLocationService(
          DeviceLocationResult.granted(30.2672, -97.7431),
        ),
      );
      await service.captureDeviceLocation();

      service.setManualOverride(
        const ResolvedLocation(
          latitude: 40.7128,
          longitude: -74.0060,
          displayName: 'New York, NY',
        ),
      );
      expect(service.searchLabel, 'New York, NY');

      // Clearing the override falls back to the captured device position.
      service.clearOverride();
      expect(service.searchLabel, '30.2672, -97.7431');
    });
  });
}
