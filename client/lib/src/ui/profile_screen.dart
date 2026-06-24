import 'package:flutter/material.dart';

import '../data/auth_service.dart';
import '../data/event_api.dart';
import '../models/user_profile.dart';
import 'session_history.dart';

/// The Profile tab: greets the user by their generated (and editable) handle,
/// lets them set the free-text "Preferred Activities" used to rank cards, and
/// hosts the account actions (past sessions, sign out).
///
/// Nothing here relies on identity-provider profile fields (name/email/avatar)
/// — the username is generated and persisted by the backend.
class ProfileScreen extends StatefulWidget {
  const ProfileScreen({
    super.key,
    required this.api,
    required this.authService,
  });

  final EventApi api;
  final AuthService authService;

  @override
  State<ProfileScreen> createState() => _ProfileScreenState();
}

class _ProfileScreenState extends State<ProfileScreen> {
  final TextEditingController _usernameController = TextEditingController();
  final TextEditingController _activitiesController = TextEditingController();

  // The profile last loaded/saved from the backend. Used for the greeting and
  // to detect unsaved edits.
  UserProfile? _profile;
  bool _loading = true;
  bool _saving = false;
  String? _error;

  @override
  void initState() {
    super.initState();
    _usernameController.addListener(_onChanged);
    _activitiesController.addListener(_onChanged);
    _load();
  }

  @override
  void dispose() {
    _usernameController.dispose();
    _activitiesController.dispose();
    super.dispose();
  }

  void _onChanged() => setState(() {});

  /// Load the profile via sync, which provisions the user (and a generated
  /// username) on first login and returns the current handle + activities.
  Future<void> _load() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final profile = await widget.api.syncUser();
      if (!mounted) return;
      setState(() {
        _profile = profile;
        _usernameController.text = profile.username;
        _activitiesController.text = profile.preferredActivities;
        _loading = false;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _error = '$e';
        _loading = false;
      });
    }
  }

  /// Whether the form differs from the last-saved profile (and is valid).
  bool get _canSave {
    final profile = _profile;
    if (profile == null || _saving) return false;
    if (_usernameController.text.trim().isEmpty) return false;
    return _usernameController.text.trim() != profile.username ||
        _activitiesController.text.trim() != profile.preferredActivities;
  }

  Future<void> _save() async {
    setState(() => _saving = true);
    try {
      final updated = await widget.api.updateProfile(
        username: _usernameController.text.trim(),
        preferredActivities: _activitiesController.text.trim(),
      );
      if (!mounted) return;
      setState(() {
        _profile = updated;
        _usernameController.text = updated.username;
        _activitiesController.text = updated.preferredActivities;
        _saving = false;
      });
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Profile saved')),
      );
    } catch (e) {
      if (!mounted) return;
      setState(() => _saving = false);
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text("Couldn't save profile: $e")),
      );
    }
  }

  Future<void> _signOut() async {
    try {
      // On success the auth-state stream emits null and routes back to the
      // sign-in screen automatically.
      await widget.authService.signOut();
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Sign-out failed: $e')),
        );
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Profile')),
      body: _buildBody(),
    );
  }

  Widget _buildBody() {
    if (_loading) {
      return const Center(child: CircularProgressIndicator());
    }
    if (_error != null) {
      return Center(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              const Icon(Icons.error_outline, size: 48),
              const SizedBox(height: 12),
              Text('Couldn\'t load your profile.\n$_error',
                  textAlign: TextAlign.center),
              const SizedBox(height: 16),
              FilledButton(onPressed: _load, child: const Text('Retry')),
            ],
          ),
        ),
      );
    }

    final theme = Theme.of(context);
    return ListView(
      padding: const EdgeInsets.all(24),
      children: [
        Text(
          'Hello, ${_profile!.username}!',
          style: theme.textTheme.headlineSmall
              ?.copyWith(fontWeight: FontWeight.bold),
        ),
        const SizedBox(height: 24),
        TextField(
          controller: _usernameController,
          textInputAction: TextInputAction.next,
          decoration: const InputDecoration(
            labelText: 'Username',
            helperText: 'Your randomly generated name — edit it if you like.',
            border: OutlineInputBorder(),
          ),
        ),
        const SizedBox(height: 24),
        Text('Preferred activities', style: theme.textTheme.titleMedium),
        const SizedBox(height: 8),
        TextField(
          controller: _activitiesController,
          minLines: 3,
          maxLines: 5,
          keyboardType: TextInputType.multiline,
          decoration: const InputDecoration(
            hintText: 'I like hikes, concerts, music, etc',
            helperText: 'We use this to rank activities for you.',
            border: OutlineInputBorder(),
          ),
        ),
        const SizedBox(height: 16),
        FilledButton(
          onPressed: _canSave ? _save : null,
          child: _saving
              ? const SizedBox(
                  width: 18,
                  height: 18,
                  child: CircularProgressIndicator(strokeWidth: 2),
                )
              : const Text('Save'),
        ),
        const Divider(height: 48),
        SessionHistorySection(api: widget.api),
        const Divider(height: 48),
        ListTile(
          contentPadding: EdgeInsets.zero,
          leading: const Icon(Icons.logout),
          title: const Text('Sign out'),
          onTap: _signOut,
        ),
      ],
    );
  }
}
