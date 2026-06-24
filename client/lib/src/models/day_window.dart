// The single, fixed window the app searches. The whole premise is "what can I
// do today?", where "today" runs from right now until the early hours of the
// next morning (4 AM) rather than stopping at midnight — so an evening or
// late-night open still surfaces things to do tonight.

/// A concrete `[start, end]` instant range the feed is fetched for.
class DayWindow {
  const DayWindow(this.start, this.end);

  final DateTime start;
  final DateTime end;

  /// The hour (local time) the window closes at: 4 AM.
  static const int closingHour = 4;

  /// The window anchored at [now]: it starts now and ends at the next
  /// occurrence of 4 AM. Opening before 4 AM closes at 4 AM the same morning;
  /// opening any later closes at 4 AM the next morning. So 8 PM → 4 AM next
  /// day, 2 PM → 4 AM next day, 5 AM → 4 AM next day, 1 AM → 4 AM today.
  factory DayWindow.today(DateTime now) {
    final fourAmToday =
        DateTime(now.year, now.month, now.day, closingHour);
    final end = now.isBefore(fourAmToday)
        ? fourAmToday
        : fourAmToday.add(const Duration(days: 1));
    return DayWindow(now, end);
  }
}
