import 'package:firebase_auth/firebase_auth.dart';
import 'package:flutter/material.dart';

import 'config/api_config.dart';
import 'data/auth_service.dart';
import 'data/event_api.dart';
import 'data/filter_service.dart';
import 'data/location_service.dart';
import 'ui/feed_screen.dart';
import 'ui/sign_in_screen.dart';

class EventSwiperApp extends StatefulWidget {
  const EventSwiperApp({super.key});

  @override
  State<EventSwiperApp> createState() => _EventSwiperAppState();
}

class _EventSwiperAppState extends State<EventSwiperApp> {
  late final AuthService _authService = AuthService();
  late final EventApi _eventApi =
      EventApi(baseUrl: ApiConfig.baseUrl, auth: _authService);
  // Session-scoped: the manual location override lives for the whole app
  // session, surviving feed reloads and sign-in state rebuilds.
  final LocationService _locationService = LocationService();
  // Session-scoped filters (max distance + time range). Starts with sensible
  // defaults so a swipe session can begin without opening the filter sheet.
  final FilterService _filterService = FilterService();

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Event Swiper',
      theme: ThemeData(
        colorSchemeSeed: Colors.deepPurple,
        useMaterial3: true,
      ),
      home: StreamBuilder<User?>(
        stream: _authService.authStateChanges,
        builder: (context, snapshot) {
          if (snapshot.connectionState == ConnectionState.waiting) {
            return const Scaffold(
              body: Center(child: CircularProgressIndicator()),
            );
          }
          if (snapshot.hasData) {
            return FeedScreen(
              api: _eventApi,
              authService: _authService,
              locationService: _locationService,
              filterService: _filterService,
            );
          }
          return SignInScreen(authService: _authService);
        },
      ),
    );
  }
}
