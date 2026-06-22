class ApiConfig {
  /// Base URL of the FastAPI backend.
  /// Override at build time with: --dart-define=API_BASE_URL=https://...
  static const String baseUrl = String.fromEnvironment(
    'API_BASE_URL',
    defaultValue: 'http://10.0.2.2:8000',
  );
}
