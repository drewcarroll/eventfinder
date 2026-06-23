# Firebase setup

The Flutter app authenticates with **Firebase Phone Auth** (SMS one-time code).
The generated Firebase config files hold per-project keys and are
**git-ignored**, so a fresh clone (or CI) must regenerate them before the app
will build.

Ignored, machine-generated files (see `.gitignore`):

- `lib/firebase_options.dart`
- `android/app/google-services.json`
- `ios/Runner/GoogleService-Info.plist`

## Regenerate the config

```bash
# One-time tooling
firebase login                       # use the account that owns the project
dart pub global activate flutterfire_cli
export PATH="$PATH:$HOME/.pub-cache/bin"

# From the client/ directory
flutterfire configure --project=<your-firebase-project-id>
```

When prompted, select the **android** and **ios** platforms and accept the
detected bundle/package IDs:

| Platform | Identifier                |
| -------- | ------------------------- |
| Android  | `com.chiron.event_swiper` |
| iOS      | `com.chiron.eventSwiper`  |

`flutterfire configure` writes all three files above and applies the
`com.google.gms.google-services` Gradle plugin on Android.

## Enable Phone sign-in

In the [Firebase console](https://console.firebase.google.com/) for the
project: **Authentication → Sign-in method → Phone → Enable**.

### Development: test phone numbers (no real SMS)

Under the Phone provider, expand **Phone numbers for testing** and add a
fictional number + fixed code, e.g.:

| Phone number      | Code     |
| ----------------- | -------- |
| `+1 650-555-1234` | `123456` |

Enter that number on the sign-in screen and use the fixed code — Firebase skips
the real SMS, so this works on the simulator with **no APNs or SHA-1 setup**.

### Production: real SMS

Real text messages require platform app-verification:

- **Android** — add the app's **SHA-1** (and SHA-256) signing fingerprints to
  the Firebase Android app (`./gradlew signingReport` to find them).
- **iOS** — upload an **APNs auth key** under Project Settings → Cloud
  Messaging, and enable the Push Notifications capability / remote-notification
  background mode on the Runner target. Firebase uses a silent push to verify
  the app, falling back to reCAPTCHA.

## Project notes

- App init lives in `lib/main.dart`:
  `Firebase.initializeApp(options: DefaultFirebaseOptions.currentPlatform)`.
- Auth flow lives in `lib/src/data/auth_service.dart`
  (`verifyPhoneNumber` → `signInWithSmsCode`) and the two-step UI in
  `lib/src/ui/sign_in_screen.dart`.
- Firebase iOS SDK 12.x (via `firebase_core` 4.x) requires **iOS 15+** — the
  Podfile and Xcode deployment target are pinned to `15.0`.
