// Presentation helpers for an event's distance and time, shared by the swipe
// cards and the results list so both read identically.

String formatDistance(double km) {
  if (km < 1) return '${(km * 1000).round()} m away';
  final rounded = km < 10 ? km.toStringAsFixed(1) : km.round().toString();
  return '$rounded km away';
}

/// Format an availability window as a compact start–end time range, e.g.
/// "8:00 – 11:00 PM" or, across midnight, "10:00 PM – 2:00 AM". This is a
/// "today" feed, so the date is implied and omitted to keep cards short. When
/// start and end share an AM/PM half, the period is shown once, on the end.
String formatTimeRange(DateTime start, DateTime end) {
  final samePeriod = (start.hour < 12) == (end.hour < 12);
  final startClock =
      samePeriod ? _formatClockNoPeriod(start) : _formatClock(start);
  return '$startClock – ${_formatClock(end)}';
}

String _formatClock(DateTime dt) {
  final period = dt.hour < 12 ? 'AM' : 'PM';
  return '${_formatClockNoPeriod(dt)} $period';
}

String _formatClockNoPeriod(DateTime dt) {
  final hour12 = dt.hour % 12 == 0 ? 12 : dt.hour % 12;
  final minute = dt.minute.toString().padLeft(2, '0');
  return '$hour12:$minute';
}
