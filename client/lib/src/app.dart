import 'package:firebase_auth/firebase_auth.dart';
import 'package:flutter/material.dart';

import 'config/api_config.dart';
import 'data/auth_service.dart';
import 'data/event_api.dart';
import 'ui/feed_screen.dart';
import 'ui/sign_in_screen.dart';

class EventSwiperApp extends StatelessWidget {
  const EventSwiperApp({super.key});

  @override
  Widget build(BuildContext context) {
    final authService = AuthService();
    final eventApi = EventApi(baseUrl: ApiConfig.baseUrl, auth: authService);

    return MaterialApp(
      title: 'Event Swiper',
      theme: ThemeData(
        colorSchemeSeed: Colors.deepPurple,
        useMaterial3: true,
      ),
      home: StreamBuilder<User?>(
        stream: authService.authStateChanges,
        builder: (context, snapshot) {
          if (snapshot.connectionState == ConnectionState.waiting) {
            return const Scaffold(
              body: Center(child: CircularProgressIndicator()),
            );
          }
          if (snapshot.hasData) {
            return FeedScreen(api: eventApi, authService: authService);
          }
          return SignInScreen(authService: authService);
        },
      ),
    );
  }
}
