import 'package:firebase_auth/firebase_auth.dart';
import 'package:flutter/material.dart';

import 'config/api_config.dart';
import 'data/auth_service.dart';
import 'data/event_api.dart';
import 'data/filter_service.dart';
import 'data/location_service.dart';
import 'ui/home_shell.dart';
import 'ui/sign_in_screen.dart';
import 'ui/theme/app_theme.dart';

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
      debugShowCheckedModeBanner: false,
      theme: AppTheme.light,
      darkTheme: AppTheme.dark,
      home: StreamBuilder<User?>(
        stream: _authService.authStateChanges,
        builder: (context, snapshot) {
          if (snapshot.connectionState == ConnectionState.waiting) {
            return const _SplashScreen();
          }
          if (snapshot.hasData) {
            return HomeShell(
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

/// Branded launch screen shown while the auth state resolves: the wordmark on
/// the brand blue with a quiet loading indicator.
class _SplashScreen extends StatelessWidget {
  const _SplashScreen();

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.blue,
      body: Center(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Container(
              height: 84,
              width: 84,
              decoration: BoxDecoration(
                color: Colors.white.withValues(alpha: 0.18),
                borderRadius: BorderRadius.circular(24),
                border: Border.all(color: Colors.white24),
              ),
              child: const Icon(
                Icons.bolt_rounded,
                color: Colors.white,
                size: 44,
              ),
            ),
            const SizedBox(height: 24),
            const Text(
              'Event Swiper',
              style: TextStyle(
                color: Colors.white,
                fontSize: 26,
                fontWeight: FontWeight.w800,
                letterSpacing: -0.5,
              ),
            ),
            const SizedBox(height: 28),
            const SizedBox(
              height: 26,
              width: 26,
              child: CircularProgressIndicator(
                strokeWidth: 2.4,
                valueColor: AlwaysStoppedAnimation(Colors.white),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
