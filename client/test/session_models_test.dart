import 'package:event_swiper/src/models/session_detail.dart';
import 'package:event_swiper/src/models/session_summary.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  test('SessionSummary.fromJson parses the history list shape', () {
    final summary = SessionSummary.fromJson({
      'session_id': 's1',
      'location': 'Austin',
      'distance': 25.0,
      'time_range': 'this weekend',
      'created_at': '2030-06-15T20:00:00',
      'ended_at': '2030-06-15T20:30:00',
      'swipe_count': 12,
      'yes_count': 3,
    });

    expect(summary.id, 's1');
    expect(summary.location, 'Austin');
    expect(summary.distance, 25.0);
    expect(summary.swipeCount, 12);
    expect(summary.yesCount, 3);
    expect(summary.createdAt, DateTime(2030, 6, 15, 20));
  });

  test('SessionSummary.fromJson tolerates missing optional fields', () {
    final summary = SessionSummary.fromJson({'session_id': 's1'});

    expect(summary.id, 's1');
    expect(summary.location, isNull);
    expect(summary.createdAt, isNull);
    expect(summary.swipeCount, 0);
    expect(summary.yesCount, 0);
  });

  test('SessionDetail.fromJson parses the yes list into events', () {
    final detail = SessionDetail.fromJson({
      'session_id': 's1',
      'location': 'Austin',
      'created_at': '2030-06-15T20:00:00',
      'swipe_count': 2,
      'yes': [
        {'id': 'a', 'title': 'Jazz Night', 'category': 'music'},
        {'id': 'b', 'title': 'Art Walk', 'category': 'art'},
      ],
    });

    expect(detail.id, 's1');
    expect(detail.swipeCount, 2);
    expect(detail.liked.map((e) => e.title).toList(),
        ['Jazz Night', 'Art Walk']);
  });

  test('SessionDetail.fromJson handles an empty yes list', () {
    final detail = SessionDetail.fromJson({
      'session_id': 's1',
      'swipe_count': 5,
      'yes': <dynamic>[],
    });

    expect(detail.liked, isEmpty);
  });
}
