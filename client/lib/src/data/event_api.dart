import 'dart:convert';

import 'package:http/http.dart' as http;

import '../models/event.dart';
import '../models/resolved_location.dart';
import '../models/session_detail.dart';
import '../models/session_summary.dart';
import '../models/swipe_session.dart';
import 'auth_service.dart';

/// HTTP client for the Event Swiper backend.
class EventApi {
  EventApi({required this.baseUrl, required this.auth, http.Client? client})
      : _client = client ?? http.Client();

  final String baseUrl;
  final AuthService auth;
  final http.Client _client;

  Future<Map<String, String>> _headers() async {
    final token = await auth.idToken();
    return {
      'Authorization': 'Bearer $token',
      'Content-Type': 'application/json',
    };
  }

  /// Verifies the Firebase ID token server-side and upserts the user
  /// record. Call once after sign-in, before loading the feed.
  Future<void> syncUser() async {
    final uri = Uri.parse('$baseUrl/users/sync');
    final res = await _client.post(uri, headers: await _headers());
    if (res.statusCode != 200 && res.statusCode != 201) {
      throw Exception('User sync failed: ${res.statusCode} ${res.body}');
    }
  }

  /// Fetch the feed for [query], optionally constrained by the session
  /// filters: a search radius and a time window. Filters are sent as query
  /// params; datetimes are sent as UTC ISO-8601 so the backend compares them
  /// against event start times unambiguously.
  Future<List<Event>> fetchFeed(
    String query, {
    int limit = 20,
    double? radiusKm,
    DateTime? startsAfter,
    DateTime? startsBefore,
  }) async {
    final params = <String, String>{'query': query, 'limit': '$limit'};
    if (radiusKm != null) {
      params['radius_km'] = radiusKm.round().toString();
    }
    if (startsAfter != null) {
      params['starts_after'] = startsAfter.toUtc().toIso8601String();
    }
    if (startsBefore != null) {
      params['starts_before'] = startsBefore.toUtc().toIso8601String();
    }
    final uri = Uri.parse('$baseUrl/api/v1/feed').replace(
      queryParameters: params,
    );
    final res = await _client.get(uri, headers: await _headers());
    if (res.statusCode != 200) {
      throw Exception('Feed request failed: ${res.statusCode} ${res.body}');
    }
    final body = jsonDecode(res.body) as Map<String, dynamic>;
    final events = body['events'] as List<dynamic>;
    return events
        .map((e) => Event.fromJson(e as Map<String, dynamic>))
        .toList();
  }

  /// Resolves a free-text location (e.g. "Austin, TX") to coordinates so it
  /// can override the device's GPS position for the session.
  Future<ResolvedLocation> resolveLocation(String query) async {
    final uri = Uri.parse('$baseUrl/api/v1/locations/resolve').replace(
      queryParameters: {'q': query},
    );
    final res = await _client.get(uri, headers: await _headers());
    if (res.statusCode == 404) {
      throw Exception('Could not find "$query". Try a more specific place.');
    }
    if (res.statusCode != 200) {
      throw Exception(
        'Location lookup failed: ${res.statusCode} ${res.body}',
      );
    }
    final body = jsonDecode(res.body) as Map<String, dynamic>;
    return ResolvedLocation.fromJson(body);
  }

  /// Persist a completed swiping run in one request: the session filters plus
  /// every decision. The backend returns the compiled yes list — the cards the
  /// user liked — which is parsed back into [Event]s for the results screen.
  ///
  /// A right swipe is sent as a `like`, a left swipe as a `pass`; each card is
  /// snapshotted as `card_data` so results survive without a second fetch.
  Future<List<Event>> saveSession({
    required List<SwipeDecision> decisions,
    String? location,
    double? distance,
    String? timeRange,
  }) async {
    final uri = Uri.parse('$baseUrl/api/v1/sessions');
    final res = await _client.post(
      uri,
      headers: await _headers(),
      body: jsonEncode({
        'location': location,
        'distance': distance,
        'time_range': timeRange,
        'swipes': [
          for (final d in decisions)
            {
              'card_data': d.event.toJson(),
              'decision': d.choice == SwipeChoice.yes ? 'like' : 'pass',
            },
        ],
      }),
    );
    if (res.statusCode != 201) {
      throw Exception('Save session failed: ${res.statusCode} ${res.body}');
    }
    final body = jsonDecode(res.body) as Map<String, dynamic>;
    final yes = body['yes'] as List<dynamic>;
    return yes
        .map((e) => Event.fromJson(e as Map<String, dynamic>))
        .toList();
  }

  /// Fetch the signed-in user's past sessions, most recent first, for the
  /// history screen. Each entry carries summary counts; the full yes list is
  /// loaded on demand via [fetchSession].
  Future<List<SessionSummary>> fetchSessions() async {
    final uri = Uri.parse('$baseUrl/api/v1/sessions');
    final res = await _client.get(uri, headers: await _headers());
    if (res.statusCode != 200) {
      throw Exception('History request failed: ${res.statusCode} ${res.body}');
    }
    final body = jsonDecode(res.body) as Map<String, dynamic>;
    final sessions = body['sessions'] as List<dynamic>;
    return sessions
        .map((e) => SessionSummary.fromJson(e as Map<String, dynamic>))
        .toList();
  }

  /// Fetch one past session in full, including its compiled yes list.
  Future<SessionDetail> fetchSession(String id) async {
    final uri = Uri.parse('$baseUrl/api/v1/sessions/$id');
    final res = await _client.get(uri, headers: await _headers());
    if (res.statusCode != 200) {
      throw Exception('Session request failed: ${res.statusCode} ${res.body}');
    }
    final body = jsonDecode(res.body) as Map<String, dynamic>;
    return SessionDetail.fromJson(body);
  }
}
