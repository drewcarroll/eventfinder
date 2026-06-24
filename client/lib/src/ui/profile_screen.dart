import 'package:flutter/material.dart';

import '../data/auth_service.dart';
import '../data/event_api.dart';
import 'history_screen.dart';

/// The Profile tab: shows the signed-in account and the account-level actions
/// that used to hang off the feed's app bar — viewing past sessions and
/// signing out.
class ProfileScreen extends StatelessWidget {
  const ProfileScreen({
    super.key,
    required this.api,
    required this.authService,
  });

  final EventApi api;
  final AuthService authService;

  Future<void> _signOut(BuildContext context) async {
    try {
      // On success the auth-state stream emits null and routes back to the
      // sign-in screen automatically.
      await authService.signOut();
    } catch (e) {
      if (context.mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Sign-out failed: $e')),
        );
      }
    }
  }

  void _openHistory(BuildContext context) {
    Navigator.of(context).push(
      MaterialPageRoute<void>(
        builder: (_) => HistoryScreen(api: api),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final phone = authService.currentUser?.phoneNumber;
    return Scaffold(
      appBar: AppBar(title: const Text('Profile')),
      body: ListView(
        children: [
          ListTile(
            leading: const Icon(Icons.account_circle, size: 40),
            title: Text(phone ?? 'Signed in'),
            subtitle: phone != null ? const Text('Phone number') : null,
          ),
          const Divider(),
          ListTile(
            leading: const Icon(Icons.history),
            title: const Text('Past sessions'),
            trailing: const Icon(Icons.chevron_right),
            onTap: () => _openHistory(context),
          ),
          ListTile(
            leading: const Icon(Icons.logout),
            title: const Text('Sign out'),
            onTap: () => _signOut(context),
          ),
        ],
      ),
    );
  }
}
