import 'package:firebase_auth/firebase_auth.dart';
import 'package:firebase_core/firebase_core.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';

import 'firebase_options.dart';
import 'src/app.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  await Firebase.initializeApp(
    options: DefaultFirebaseOptions.currentPlatform,
  );
  // Debug builds can optionally route auth through the local Firebase Auth
  // Emulator — opt in with `--dart-define=USE_AUTH_EMULATOR=true`. It is OFF
  // by default so debug builds hit the real Firebase project, where numbers
  // configured under Authentication → "Phone numbers for testing" sign in
  // with their fixed code and no real SMS (e.g. +1 650-555-1234 / 888888).
  // The emulator, by contrast, ignores those console test numbers and mints
  // its own random codes. Never runs in release.
  const useAuthEmulator =
      bool.fromEnvironment('USE_AUTH_EMULATOR', defaultValue: false);
  if (kDebugMode && useAuthEmulator) {
    await FirebaseAuth.instance.useAuthEmulator('localhost', 9099);
  } else if (kDebugMode) {
    // Debug, real Firebase: disable app verification so the fictional phone
    // numbers configured under Authentication → "Phone numbers for testing"
    // sign in without Play Integrity / reCAPTCHA — which means no SHA-1
    // fingerprint is needed for testing. Real numbers still fail under this
    // setting, and it never runs in release.
    await FirebaseAuth.instance
        .setSettings(appVerificationDisabledForTesting: true);
  }
  runApp(const EventSwiperApp());
}
