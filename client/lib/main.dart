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
  // Debug builds only: route auth through the local Firebase Auth Emulator.
  // The simulator has no APNs and the project has no reCAPTCHA URL scheme, so
  // real phone verification crashes; the emulator accepts any number and
  // surfaces the SMS code in its log. Never runs in release.
  if (kDebugMode) {
    await FirebaseAuth.instance.useAuthEmulator('localhost', 9099);
  }
  runApp(const EventSwiperApp());
}
