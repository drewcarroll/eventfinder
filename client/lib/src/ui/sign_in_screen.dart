import 'package:firebase_auth/firebase_auth.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../data/auth_service.dart';

/// Formats a US phone number as the user types — `6504959501` becomes
/// `(650) 495-9501`. If the input starts with `+`, it is treated as an
/// already-internationalised number and left untouched.
class _UsPhoneInputFormatter extends TextInputFormatter {
  @override
  TextEditingValue formatEditUpdate(
    TextEditingValue oldValue,
    TextEditingValue newValue,
  ) {
    if (newValue.text.startsWith('+')) return newValue;

    final digits = newValue.text.replaceAll(RegExp(r'\D'), '');
    final capped = digits.length > 10 ? digits.substring(0, 10) : digits;

    final buffer = StringBuffer();
    for (var i = 0; i < capped.length; i++) {
      if (i == 0) buffer.write('(');
      if (i == 3) buffer.write(') ');
      if (i == 6) buffer.write('-');
      buffer.write(capped[i]);
    }
    final text = buffer.toString();
    return TextEditingValue(
      text: text,
      selection: TextSelection.collapsed(offset: text.length),
    );
  }
}

/// Normalises user input into an E.164 number for Firebase, assuming a US
/// (+1) number when no country code is given. Returns `null` when the input
/// can't be a valid phone number so the caller can show an error.
String? normalizePhoneNumber(String input) {
  final trimmed = input.trim();
  if (trimmed.startsWith('+')) {
    final digits = trimmed.substring(1).replaceAll(RegExp(r'\D'), '');
    return digits.isEmpty ? null : '+$digits';
  }
  final digits = trimmed.replaceAll(RegExp(r'\D'), '');
  if (digits.length == 10) return '+1$digits';
  if (digits.length == 11 && digits.startsWith('1')) return '+$digits';
  return null;
}

class SignInScreen extends StatefulWidget {
  const SignInScreen({super.key, required this.authService});

  final AuthService authService;

  @override
  State<SignInScreen> createState() => _SignInScreenState();
}

enum _Step { enterPhone, enterCode }

class _SignInScreenState extends State<SignInScreen> {
  final _phoneController = TextEditingController();
  final _codeController = TextEditingController();

  _Step _step = _Step.enterPhone;
  bool _busy = false;
  String? _verificationId;

  @override
  void dispose() {
    _phoneController.dispose();
    _codeController.dispose();
    super.dispose();
  }

  void _showError(String message) {
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text(message)),
    );
  }

  Future<void> _sendCode() async {
    final phone = normalizePhoneNumber(_phoneController.text);
    if (phone == null) {
      _showError('Enter a valid phone number.');
      return;
    }
    setState(() => _busy = true);
    try {
      await widget.authService.verifyPhoneNumber(
        phoneNumber: phone,
        codeSent: (verificationId) {
          if (!mounted) return;
          setState(() {
            _verificationId = verificationId;
            _step = _Step.enterCode;
            _busy = false;
          });
        },
        verificationFailed: (error) {
          if (!mounted) return;
          setState(() => _busy = false);
          _showError(error.message ?? 'Phone verification failed.');
        },
        // Android may resolve the credential automatically. The auth-state
        // stream then routes the user onward, so just clear the busy state.
        autoVerified: (_) {
          if (mounted) setState(() => _busy = false);
        },
      );
    } catch (e) {
      if (mounted) setState(() => _busy = false);
      _showError('Could not start verification: $e');
    }
  }

  Future<void> _verifyCode() async {
    final code = _codeController.text.trim();
    final verificationId = _verificationId;
    if (code.isEmpty || verificationId == null) {
      _showError('Enter the code from the SMS.');
      return;
    }
    setState(() => _busy = true);
    try {
      // On success the auth-state stream emits the signed-in user and routes
      // away from this screen automatically.
      await widget.authService.signInWithSmsCode(
        verificationId: verificationId,
        smsCode: code,
      );
    } on FirebaseAuthException catch (e) {
      if (mounted) setState(() => _busy = false);
      _showError(e.message ?? 'Invalid code.');
    } catch (e) {
      if (mounted) setState(() => _busy = false);
      _showError('Sign-in failed: $e');
    }
  }

  void _editPhone() {
    setState(() {
      _step = _Step.enterPhone;
      _verificationId = null;
      _codeController.clear();
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: Center(
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 360),
          child: Padding(
            padding: const EdgeInsets.symmetric(horizontal: 24),
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
                if (_step == _Step.enterPhone) ..._phoneStep() else ..._codeStep(),
              ],
            ),
          ),
        ),
      ),
    );
  }

  List<Widget> _phoneStep() {
    return [
      TextField(
        controller: _phoneController,
        keyboardType: TextInputType.phone,
        autofillHints: const [AutofillHints.telephoneNumber],
        inputFormatters: [_UsPhoneInputFormatter()],
        decoration: const InputDecoration(
          labelText: 'Phone number',
          hintText: '(650) 555-1234',
          border: OutlineInputBorder(),
        ),
      ),
      const SizedBox(height: 16),
      _busy
          ? const CircularProgressIndicator()
          : FilledButton.icon(
              icon: const Icon(Icons.sms),
              label: const Text('Send code'),
              onPressed: _sendCode,
            ),
    ];
  }

  List<Widget> _codeStep() {
    return [
      Text(
        'Enter the code sent to ${_phoneController.text.trim()}',
        textAlign: TextAlign.center,
      ),
      const SizedBox(height: 16),
      TextField(
        controller: _codeController,
        keyboardType: TextInputType.number,
        autofillHints: const [AutofillHints.oneTimeCode],
        decoration: const InputDecoration(
          labelText: 'Verification code',
          hintText: '123456',
          border: OutlineInputBorder(),
        ),
      ),
      const SizedBox(height: 16),
      if (_busy)
        const CircularProgressIndicator()
      else ...[
        FilledButton.icon(
          icon: const Icon(Icons.check),
          label: const Text('Verify'),
          onPressed: _verifyCode,
        ),
        TextButton(
          onPressed: _editPhone,
          child: const Text('Use a different number'),
        ),
      ],
    ];
  }
}
