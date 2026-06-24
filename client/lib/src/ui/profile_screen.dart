import 'package:flutter/material.dart';

import '../data/auth_service.dart';
import '../data/event_api.dart';
import '../models/user_profile.dart';
import 'liked_ideas_section.dart';
import 'theme/app_theme.dart';
import 'widgets/brand_widgets.dart';

/// The Profile tab: greets the user by their generated (and editable) handle,
/// lets them set the free-text "Preferred Activities" used to rank cards, and
/// hosts their liked ideas plus the account actions (sign out).
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
    return Scaffold(body: _buildBody());
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
              const Icon(Icons.error_outline_rounded, size: 48),
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
      padding: EdgeInsets.zero,
      children: [
        _ProfileHeader(username: _profile!.username),
        Padding(
          padding: const EdgeInsets.fromLTRB(20, 24, 20, 24),
          child: FadeSlideIn(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                const _SectionLabel('Username'),
                const SizedBox(height: 10),
                TextField(
                  controller: _usernameController,
                  textInputAction: TextInputAction.next,
                  decoration: const InputDecoration(
                    prefixIcon: Icon(Icons.alternate_email_rounded),
                  ),
                ),
                const SizedBox(height: 24),
                const _SectionLabel('Preferred activities'),
                const SizedBox(height: 4),
                Text(
                  'We use this to rank activities for you.',
                  style: theme.textTheme.bodyMedium
                      ?.copyWith(color: theme.colorScheme.onSurfaceVariant),
                ),
                const SizedBox(height: 10),
                TextField(
                  controller: _activitiesController,
                  minLines: 3,
                  maxLines: 5,
                  keyboardType: TextInputType.multiline,
                  decoration: const InputDecoration(
                    hintText: 'I like hikes, concerts, music, etc',
                  ),
                ),
                const SizedBox(height: 20),
                PrimaryButton(
                  onPressed: _canSave ? _save : null,
                  label: _saving ? 'Saving…' : 'Save changes',
                  icon: Icons.check_rounded,
                  expand: true,
                ),
                const Divider(height: 48),
                LikedIdeasSection(api: widget.api),
                const Divider(height: 48),
                _SignOutTile(onTap: _signOut),
                const SizedBox(height: 8),
              ],
            ),
          ),
        ),
      ],
    );
  }
}

/// The gradient banner at the top of the Profile tab: a monogram avatar and a
/// greeting on the brand sweep.
class _ProfileHeader extends StatelessWidget {
  const _ProfileHeader({required this.username});

  final String username;

  @override
  Widget build(BuildContext context) {
    final initial =
        username.isNotEmpty ? username.characters.first.toUpperCase() : '?';
    return Container(
      width: double.infinity,
      padding: EdgeInsets.fromLTRB(
        24,
        MediaQuery.of(context).padding.top + 32,
        24,
        36,
      ),
      decoration: const BoxDecoration(
        color: AppColors.blue,
        borderRadius: BorderRadius.vertical(
          bottom: Radius.circular(AppRadii.lg),
        ),
      ),
      child: Column(
        children: [
          Container(
            height: 84,
            width: 84,
            alignment: Alignment.center,
            decoration: BoxDecoration(
              color: Colors.white.withValues(alpha: 0.22),
              shape: BoxShape.circle,
              border: Border.all(color: Colors.white54, width: 2),
            ),
            child: Text(
              initial,
              style: const TextStyle(
                color: Colors.white,
                fontSize: 38,
                fontWeight: FontWeight.w800,
              ),
            ),
          ),
          const SizedBox(height: 16),
          Text(
            username,
            style: const TextStyle(
              color: Colors.white,
              fontSize: 24,
              fontWeight: FontWeight.w800,
              letterSpacing: -0.4,
            ),
          ),
          const SizedBox(height: 2),
          Text(
            'Your profile',
            style: TextStyle(
              color: Colors.white.withValues(alpha: 0.85),
              fontSize: 14,
              fontWeight: FontWeight.w500,
            ),
          ),
        ],
      ),
    );
  }
}

class _SectionLabel extends StatelessWidget {
  const _SectionLabel(this.text);

  final String text;

  @override
  Widget build(BuildContext context) {
    return Text(
      text,
      style: Theme.of(context)
          .textTheme
          .titleMedium
          ?.copyWith(fontWeight: FontWeight.w700),
    );
  }
}

/// A bordered, tappable sign-out row with a quiet danger tint.
class _SignOutTile extends StatelessWidget {
  const _SignOutTile({required this.onTap});

  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return Material(
      color: AppColors.pass.withValues(alpha: 0.08),
      borderRadius: BorderRadius.circular(AppRadii.sm),
      child: InkWell(
        borderRadius: BorderRadius.circular(AppRadii.sm),
        onTap: onTap,
        child: const Padding(
          padding: EdgeInsets.symmetric(horizontal: 16, vertical: 14),
          child: Row(
            children: [
              Icon(Icons.logout_rounded, color: AppColors.pass),
              SizedBox(width: 12),
              Text(
                'Sign out',
                style: TextStyle(
                  color: AppColors.pass,
                  fontWeight: FontWeight.w700,
                  fontSize: 15,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
