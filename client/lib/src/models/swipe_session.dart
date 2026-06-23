import 'event.dart';

/// A single swipe decision: left is [no], right is [yes].
enum SwipeChoice { yes, no }

/// One recorded decision — the event and which way it was swiped.
class SwipeDecision {
  const SwipeDecision({required this.event, required this.choice});

  final Event event;
  final SwipeChoice choice;
}

/// Client-side state for a single swipe run.
///
/// Holds every decision the user makes — both right/[yes] and left/[no] — in
/// the order they were swiped, scoped to the current run. A new run starts
/// with a fresh [SwipeSession]; nothing here survives a reload.
class SwipeSession {
  final List<SwipeDecision> _decisions = [];

  /// Every decision made this run, in swipe order.
  List<SwipeDecision> get decisions => List.unmodifiable(_decisions);

  /// Events swiped right (yes), in order.
  List<Event> get yes => [
        for (final d in _decisions)
          if (d.choice == SwipeChoice.yes) d.event,
      ];

  /// Events swiped left (no), in order.
  List<Event> get no => [
        for (final d in _decisions)
          if (d.choice == SwipeChoice.no) d.event,
      ];

  /// Total decisions recorded this run.
  int get length => _decisions.length;

  bool get isEmpty => _decisions.isEmpty;

  /// Record [event] as swiped [choice].
  void record(Event event, SwipeChoice choice) {
    _decisions.add(SwipeDecision(event: event, choice: choice));
  }
}
