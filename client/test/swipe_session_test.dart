import 'package:event_swiper/src/models/event.dart';
import 'package:event_swiper/src/models/swipe_session.dart';
import 'package:flutter_test/flutter_test.dart';

Event _event(String id) => Event(
      id: id,
      title: 'Event $id',
      description: '',
      category: 'music',
      sourceUrl: '',
    );

void main() {
  test('a new session starts empty', () {
    final session = SwipeSession();
    expect(session.isEmpty, isTrue);
    expect(session.length, 0);
    expect(session.yes, isEmpty);
    expect(session.no, isEmpty);
  });

  test('right swipes go to the yes list, left swipes to the no list', () {
    final session = SwipeSession();
    final e1 = _event('e1');
    final e2 = _event('e2');
    final e3 = _event('e3');

    session.record(e1, SwipeChoice.yes);
    session.record(e2, SwipeChoice.no);
    session.record(e3, SwipeChoice.yes);

    expect(session.yes, [e1, e3]);
    expect(session.no, [e2]);
  });

  test('holds every decision for the run in swipe order', () {
    final session = SwipeSession();
    final e1 = _event('e1');
    final e2 = _event('e2');

    session.record(e1, SwipeChoice.no);
    session.record(e2, SwipeChoice.yes);

    expect(session.length, 2);
    expect(
      session.decisions.map((d) => d.event).toList(),
      [e1, e2],
    );
    expect(
      session.decisions.map((d) => d.choice).toList(),
      [SwipeChoice.no, SwipeChoice.yes],
    );
  });

  test('decisions list is unmodifiable', () {
    final session = SwipeSession();
    session.record(_event('e1'), SwipeChoice.yes);
    expect(
      () => session.decisions.add(
        SwipeDecision(event: _event('e2'), choice: SwipeChoice.no),
      ),
      throwsUnsupportedError,
    );
  });
}
