// Presentation helpers for an event's distance and time, shared by the swipe
// cards and the results list so both read identically.

String formatDistance(double km) {
  if (km < 1) return '${(km * 1000).round()} m away';
  final rounded = km < 10 ? km.toStringAsFixed(1) : km.round().toString();
  return '$rounded km away';
}

const List<String> _weekdays = [
  'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun',
];
const List<String> _months = [
  'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
  'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec',
];

/// Format a start time as e.g. "Sat, Jun 15 · 8:00 PM" using the datetime's
/// wall-clock components (the payload is naive, so no timezone conversion).
String formatEventTime(DateTime dt) {
  final weekday = _weekdays[dt.weekday - 1];
  final month = _months[dt.month - 1];
  final hour12 = dt.hour % 12 == 0 ? 12 : dt.hour % 12;
  final minute = dt.minute.toString().padLeft(2, '0');
  final period = dt.hour < 12 ? 'AM' : 'PM';
  return '$weekday, $month ${dt.day} · $hour12:$minute $period';
}
