import 'package:event_swiper/src/models/session_summary.dart';
import 'package:event_swiper/src/ui/session_history.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

SessionSummary _session(
  String id, {
  String? location = 'Austin',
  int swipeCount = 10,
  int yesCount = 3,
  DateTime? createdAt,
}) =>
    SessionSummary(
      id: id,
      location: location,
      swipeCount: swipeCount,
      yesCount: yesCount,
      createdAt: createdAt ?? DateTime(2030, 6, 15, 20),
    );

Future<void> _pump(
  WidgetTester tester, {
  required List<SessionSummary> sessions,
  void Function(SessionSummary)? onTap,
}) async {
  await tester.pumpWidget(
    MaterialApp(
      home: Scaffold(
        body: HistoryListView(
          sessions: sessions,
          onTap: onTap ?? (_) {},
        ),
      ),
    ),
  );
}

void main() {
  testWidgets('lists past sessions with date and summary', (tester) async {
    await _pump(tester, sessions: [
      _session('s1', location: 'Austin', yesCount: 3, swipeCount: 10),
      _session('s2', location: 'Dallas', yesCount: 1, swipeCount: 4),
    ]);

    // Date headline (from formatEventTime) for each session.
    expect(find.textContaining('Jun 15'), findsNWidgets(2));
    // Summary line: location + liked/swiped counts.
    expect(find.textContaining('Austin'), findsOneWidget);
    expect(find.textContaining('3 liked'), findsOneWidget);
    expect(find.textContaining('10 swiped'), findsOneWidget);
  });

  testWidgets('shows an empty state when there is no history',
      (tester) async {
    await _pump(tester, sessions: []);

    expect(find.textContaining('No sessions yet'), findsOneWidget);
    expect(find.byIcon(Icons.history), findsOneWidget);
  });

  testWidgets('tapping a session fires the open callback', (tester) async {
    SessionSummary? opened;
    await _pump(
      tester,
      sessions: [_session('s1'), _session('s2')],
      onTap: (s) => opened = s,
    );

    await tester.tap(find.text('Austin · 3 liked · 10 swiped').first);
    await tester.pump();

    expect(opened, isNotNull);
    expect(opened!.id, 's1');
  });
}
