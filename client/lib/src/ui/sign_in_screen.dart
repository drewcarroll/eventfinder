import 'package:flutter/material.dart';

import '../data/auth_service.dart';

class SignInScreen extends StatefulWidget {
  const SignInScreen({super.key, required this.authService});

  final AuthService authService;

  @override
  State<SignInScreen> createState() => _SignInScreenState();
}

class _SignInScreenState extends State<SignInScreen> {
  bool _signingIn = false;

  Future<void> _signIn() async {
    setState(() => _signingIn = true);
    try {
      final credential = await widget.authService.signInWithGoogle();
      // A null credential means the user dismissed the account picker.
      // That's a cancellation, not a failure — leave them on this screen
      // silently. On success, the auth-state stream routes them onward.
      if (credential == null && mounted) {
        setState(() => _signingIn = false);
      }
    } catch (e) {
      if (mounted) {
        setState(() => _signingIn = false);
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Sign-in failed: $e')),
        );
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            const Text(
              'Event Swiper',
              style: TextStyle(fontSize: 32, fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 8),
            const Text('Swipe to discover events you love'),
            const SizedBox(height: 32),
            if (_signingIn)
              const CircularProgressIndicator()
            else
              FilledButton.icon(
                icon: const Icon(Icons.login),
                label: const Text('Sign in with Google'),
                onPressed: _signIn,
              ),
          ],
        ),
      ),
    );
  }
}
