import 'package:firebase_auth/firebase_auth.dart';

/// Wraps Firebase Phone Auth and exposes the ID token used to authenticate
/// calls to the backend.
class AuthService {
  AuthService({FirebaseAuth? auth}) : _auth = auth ?? FirebaseAuth.instance;

  final FirebaseAuth _auth;

  Stream<User?> get authStateChanges => _auth.authStateChanges();

  User? get currentUser => _auth.currentUser;

  /// Starts phone-number verification.
  ///
  /// Firebase sends an SMS and calls [codeSent] with a `verificationId` that
  /// must be paired with the user-entered code in [signInWithSmsCode]. On
  /// Android the credential can be resolved automatically (instant
  /// verification / auto-retrieval), in which case [autoVerified] fires with a
  /// completed [UserCredential] and no manual code entry is needed.
  /// [verificationFailed] reports invalid numbers, quota errors, etc.
  Future<void> verifyPhoneNumber({
    required String phoneNumber,
    required void Function(String verificationId) codeSent,
    required void Function(FirebaseAuthException error) verificationFailed,
    void Function(UserCredential credential)? autoVerified,
  }) {
    return _auth.verifyPhoneNumber(
      phoneNumber: phoneNumber,
      verificationCompleted: (PhoneAuthCredential credential) async {
        final userCredential = await _auth.signInWithCredential(credential);
        autoVerified?.call(userCredential);
      },
      verificationFailed: verificationFailed,
      codeSent: (verificationId, _) => codeSent(verificationId),
      codeAutoRetrievalTimeout: (_) {},
    );
  }

  /// Completes sign-in with the SMS [smsCode] for a [verificationId] returned
  /// by a prior [verifyPhoneNumber] call.
  Future<UserCredential> signInWithSmsCode({
    required String verificationId,
    required String smsCode,
  }) {
    final credential = PhoneAuthProvider.credential(
      verificationId: verificationId,
      smsCode: smsCode,
    );
    return _auth.signInWithCredential(credential);
  }

  /// Returns a fresh Firebase ID token for backend Authorization headers.
  Future<String> idToken() async {
    final user = _auth.currentUser;
    if (user == null) {
      throw Exception('Not authenticated');
    }
    return (await user.getIdToken()) ?? '';
  }

  Future<void> signOut() => _auth.signOut();
}
