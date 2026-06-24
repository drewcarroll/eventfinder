/// The signed-in user's editable profile, as returned by the backend.
///
/// The [username] is a backend-generated, user-editable handle — deliberately
/// independent of any identity-provider profile field. [preferredActivities]
/// is the free-text blurb the ranking pipeline uses to order cards.
class UserProfile {
  const UserProfile({
    required this.uid,
    required this.username,
    required this.preferredActivities,
  });

  final String uid;
  final String username;
  final String preferredActivities;

  factory UserProfile.fromJson(Map<String, dynamic> json) {
    return UserProfile(
      uid: json['uid'] as String? ?? '',
      username: json['username'] as String? ?? '',
      preferredActivities: json['preferred_activities'] as String? ?? '',
    );
  }
}
