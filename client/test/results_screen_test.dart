import 'package:event_swiper/src/models/event.dart';
import 'package:event_swiper/src/ui/results_screen.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

Event _event(String id, {String title = 'Title'}) => Event(
      id: id,
      title: title,
      description: 'desc',
      category: 'music',
      sourceUrl: '',
      distanceKm: 3.4,
      startsAt: DateTime(2030, 6, 15, 20),
    );

Future<void> _pump(
  WidgetTester tester, {
  required List<Event> liked,
  VoidCallback? onNewSearch,
}) async {
  await tester.pumpWidget(
    MaterialApp(
      home: ResultsScreen(
        liked: liked,
        onNewSearch: onNewSearch ?? () {},
        onSignOut: () {},
      ),
    ),
  );
}

void main() {
  testWidgets('lists liked events with a count header', (tester) async {
    await _pump(tester, liked: [
      _event('e1', title: 'Jazz Night'),
      _event('e2', title: 'Art Walk'),
    ]);

    expect(find.text('2 events saved'), findsOneWidget);
    expect(find.text('Jazz Night'), findsOneWidget);
    expect(find.text('Art Walk'), findsOneWidget);
    expect(find.textContaining('km away'), findsNWidgets(2));
  });

  testWidgets('singular header for one pick', (tester) async {
    await _pump(tester, liked: [_event('e1')]);
    expect(find.text('1 event saved'), findsOneWidget);
  });

  testWidgets('shows a friendly message when nothing was liked',
      (tester) async {
    await _pump(tester, liked: []);

    expect(find.textContaining("didn't save any events"), findsOneWidget);
    expect(find.text('Jazz Night'), findsNothing);
  });

  testWidgets('New search button fires the callback', (tester) async {
    var started = 0;
    await _pump(tester, liked: [_event('e1')], onNewSearch: () => started++);

    await tester.tap(find.text('New search'));
    await tester.pump();

    expect(started, 1);
  });
}
