import 'dart:convert';

import 'package:http/http.dart' as http;

import '../models/event.dart';
import '../models/resolved_location.dart';
import '../models/user_profile.dart';
import 'auth_service.dart';

/// HTTP client for the Event Swiper backend.
class EventApi {
  EventApi({required this.baseUrl, required this.auth, http.Client? client})
      : _client = client ?? http.Client();

  /// Default number of cards to request for a feed. Matches the backend's
  /// final feed size so the UI renders a full deck.
  static const int defaultFeedLimit = 50;

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
  /// record, returning the resulting profile. Provisions a generated
  /// username on first login. Call after sign-in, before loading the feed or
  /// showing the profile.
  Future<UserProfile> syncUser() async {
    final uri = Uri.parse('$baseUrl/users/sync');
    final res = await _client.post(uri, headers: await _headers());
    if (res.statusCode != 200 && res.statusCode != 201) {
      throw Exception('User sync failed: ${res.statusCode} ${res.body}');
    }
    return UserProfile.fromJson(jsonDecode(res.body) as Map<String, dynamic>);
  }

  /// Persist the user-editable profile fields (chosen handle + free-text
  /// activity preferences) and return the updated profile.
  Future<UserProfile> updateProfile({
    required String username,
    required String preferredActivities,
  }) async {
    final uri = Uri.parse('$baseUrl/users/me');
    final res = await _client.put(
      uri,
      headers: await _headers(),
      body: jsonEncode({
        'username': username,
        'preferred_activities': preferredActivities,
      }),
    );
    if (res.statusCode != 200) {
      throw Exception('Profile update failed: ${res.statusCode} ${res.body}');
    }
    return UserProfile.fromJson(jsonDecode(res.body) as Map<String, dynamic>);
  }

  /// Fetch the feed for [query], optionally constrained by the session
  /// filters: a search radius and a time window. Filters are sent as query
  /// params; datetimes are sent as UTC ISO-8601 so the backend compares them
  /// against event start times unambiguously.
  Future<List<Event>> fetchFeed(
    String query, {
    int limit = defaultFeedLimit,
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

  /// Record one idea the user swiped yes on. Likes are persisted as the user
  /// swipes — there is no session to close. The full card is snapshotted as
  /// `card_data`; re-liking the same idea is idempotent on the backend.
  Future<void> likeIdea(Event event) async {
    final uri = Uri.parse('$baseUrl/api/v1/likes');
    final res = await _client.post(
      uri,
      headers: await _headers(),
      body: jsonEncode({'card_data': event.toJson()}),
    );
    if (res.statusCode != 201) {
      throw Exception('Like failed: ${res.statusCode} ${res.body}');
    }
  }

  /// Fetch the signed-in user's liked ideas — the ones they swiped yes on —
  /// most recently liked first, for the profile.
  Future<List<Event>> fetchLikedIdeas() async {
    final uri = Uri.parse('$baseUrl/api/v1/likes');
    final res = await _client.get(uri, headers: await _headers());
    if (res.statusCode != 200) {
      throw Exception('Liked ideas request failed: '
          '${res.statusCode} ${res.body}');
    }
    final body = jsonDecode(res.body) as Map<String, dynamic>;
    final ideas = body['ideas'] as List<dynamic>;
    return ideas
        .map((e) => Event.fromJson(e as Map<String, dynamic>))
        .toList();
  }
}
