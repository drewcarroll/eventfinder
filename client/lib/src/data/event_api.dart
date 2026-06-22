import 'dart:convert';

import 'package:http/http.dart' as http;

import '../models/event.dart';
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

  Future<List<Event>> fetchFeed(String query, {int limit = 20}) async {
    final uri = Uri.parse('$baseUrl/api/v1/feed').replace(
      queryParameters: {'query': query, 'limit': '$limit'},
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

  Future<void> recordSwipe(String eventId, String direction) async {
    final uri = Uri.parse('$baseUrl/api/v1/swipes');
    final res = await _client.post(
      uri,
      headers: await _headers(),
      body: jsonEncode({'event_id': eventId, 'direction': direction}),
    );
    if (res.statusCode != 201 && res.statusCode != 409) {
      throw Exception('Swipe failed: ${res.statusCode} ${res.body}');
    }
  }
}
