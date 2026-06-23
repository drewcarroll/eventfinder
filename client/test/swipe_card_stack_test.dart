import 'package:event_swiper/src/models/event.dart';
import 'package:event_swiper/src/ui/swipe_card_stack.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

Event _event(String id, {String title = 'Title'}) => Event(
      id: id,
      title: title,
      description: 'A lovely description',
      category: 'music',
      sourceUrl: '',
      distanceKm: 3.4,
      startsAt: DateTime(2030, 6, 15, 20),
    );

/// Pump the stack inside a host that owns the event list and removes the
/// front card on swipe — mirroring how FeedScreen wires it up.
Future<List<String>> _pumpStack(
  WidgetTester tester,
  List<Event> events,
) async {
  final swiped = <String>[];
  await tester.pumpWidget(
    MaterialApp(
      home: Scaffold(
        body: _StackHost(
          events: events,
          onSwipe: (event, direction) =>
              swiped.add('${event.id}:$direction'),
        ),
      ),
    ),
  );
  return swiped;
}

void main() {
  testWidgets('renders title, category, distance and time', (tester) async {
    await _pumpStack(tester, [_event('e1', title: 'Jazz Night')]);

    expect(find.text('Jazz Night'), findsOneWidget);
    expect(find.text('music'), findsOneWidget);
    expect(find.textContaining('km away'), findsOneWidget);
    // "Sat, Jun 15 · 8:00 PM"
    expect(find.textContaining('Jun 15'), findsOneWidget);
    expect(find.textContaining('8:00 PM'), findsOneWidget);
    expect(find.text('A lovely description'), findsOneWidget);
  });

  testWidgets('swiping right reports a like and advances', (tester) async {
    final swiped =
        await _pumpStack(tester, [_event('e1'), _event('e2')]);

    await tester.fling(find.byType(EventCard).first,
        const Offset(400, 0), 1200, warnIfMissed: false);
    await tester.pumpAndSettle();

    expect(swiped, ['e1:like']);
  });

  testWidgets('swiping left reports a pass and advances', (tester) async {
    final swiped =
        await _pumpStack(tester, [_event('e1'), _event('e2')]);

    await tester.fling(find.byType(EventCard).first,
        const Offset(-400, 0), 1200, warnIfMissed: false);
    await tester.pumpAndSettle();

    expect(swiped, ['e1:pass']);
  });

  testWidgets('like button reports a like', (tester) async {
    final swiped = await _pumpStack(tester, [_event('e1'), _event('e2')]);

    await tester.tap(find.byTooltip('Like'));
    await tester.pumpAndSettle();

    expect(swiped, ['e1:like']);
  });

  testWidgets('pass button reports a pass', (tester) async {
    final swiped = await _pumpStack(tester, [_event('e1'), _event('e2')]);

    await tester.tap(find.byTooltip('Pass'));
    await tester.pumpAndSettle();

    expect(swiped, ['e1:pass']);
  });
}

/// A minimal stateful host that removes the swiped card from its list, the
/// way FeedScreen does, so the stack can be exercised end to end.
class _StackHost extends StatefulWidget {
  const _StackHost({required this.events, required this.onSwipe});

  final List<Event> events;
  final void Function(Event event, String direction) onSwipe;

  @override
  State<_StackHost> createState() => _StackHostState();
}

class _StackHostState extends State<_StackHost> {
  late List<Event> _events = List.of(widget.events);

  @override
  Widget build(BuildContext context) {
    return SwipeCardStack(
      events: _events,
      onSwipe: (event, direction) {
        widget.onSwipe(event, direction);
        setState(() => _events = _events.where((e) => e.id != event.id).toList());
      },
    );
  }
}
