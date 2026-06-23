import 'package:flutter/material.dart';

import '../models/event.dart';
import 'event_format.dart';

/// Swipe outcomes reported to the parent. Mirrors the backend's swipe
/// directions: a right swipe is a like, a left swipe is a pass.
const String _like = 'like';
const String _pass = 'pass';

/// A Tinder-style stack of [Event] cards.
///
/// The front card follows the user's drag and tilts as it moves. Flinging it
/// far enough — or past the velocity threshold — sends it off-screen and
/// reports the swipe via [onSwipe]; releasing short of that springs it back.
/// The next card sits just behind, pre-rendered at rest, so advancing the
/// stack is seamless.
///
/// The widget renders from [events] and reports swipes; it does not mutate the
/// list. The parent removes the swiped card (and records it) in [onSwipe],
/// which shrinks [events] and promotes the card that was already waiting
/// behind.
class SwipeCardStack extends StatefulWidget {
  const SwipeCardStack({
    super.key,
    required this.events,
    required this.onSwipe,
  });

  final List<Event> events;
  final void Function(Event event, String direction) onSwipe;

  @override
  State<SwipeCardStack> createState() => _SwipeCardStackState();
}

class _SwipeCardStackState extends State<SwipeCardStack>
    with SingleTickerProviderStateMixin {
  /// Drag distance, in pixels, beyond which a release commits the swipe.
  static const double _commitDistance = 110;

  /// Fling speed, in px/s, that commits a swipe regardless of distance.
  static const double _commitVelocity = 800;

  late final AnimationController _controller;
  Animation<Offset>? _flight;

  /// Current offset of the front card from its resting position.
  Offset _drag = Offset.zero;

  /// True while a card animates off-screen, so input is ignored until the
  /// parent has advanced the stack.
  bool _leaving = false;

  @override
  void initState() {
    super.initState();
    _controller = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 250),
    )..addListener(() {
        final flight = _flight;
        if (flight != null) setState(() => _drag = flight.value);
      });
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  void _onPanUpdate(DragUpdateDetails details) {
    if (_leaving) return;
    setState(() => _drag += details.delta);
  }

  void _onPanEnd(DragEndDetails details) {
    if (_leaving) return;
    final velocity = details.velocity.pixelsPerSecond.dx;
    final committed = _drag.dx.abs() > _commitDistance ||
        velocity.abs() > _commitVelocity;
    if (committed) {
      _flingOff(_drag.dx < 0 ? _pass : _like);
    } else {
      _springBack();
    }
  }

  /// Animate the front card off-screen in the swiped direction, then report
  /// it. The parent removes it from [events]; the next card is already in
  /// place behind, so the reset to [Offset.zero] lands on a fresh front card.
  void _flingOff(String direction) {
    final event = widget.events.first;
    final width = MediaQuery.of(context).size.width;
    final target = Offset(
      (direction == _like ? 1 : -1) * (width + 200),
      _drag.dy,
    );
    setState(() => _leaving = true);
    _animateTo(target, () {
      widget.onSwipe(event, direction);
      setState(() {
        _drag = Offset.zero;
        _leaving = false;
      });
    });
  }

  void _springBack() => _animateTo(Offset.zero, null);

  void _animateTo(Offset target, VoidCallback? onDone) {
    _flight = Tween<Offset>(begin: _drag, end: target).animate(
      CurvedAnimation(parent: _controller, curve: Curves.easeOut),
    );
    _controller.forward(from: 0).whenCompleteOrCancel(() {
      if (onDone != null) onDone();
    });
  }

  /// Trigger a swipe from a button (no drag), animating the card off-screen.
  void _swipeFromButton(String direction) {
    if (_leaving || widget.events.isEmpty) return;
    _flingOff(direction);
  }

  @override
  Widget build(BuildContext context) {
    final events = widget.events;
    // The card behind the front one, drawn first so it sits underneath.
    final children = <Widget>[
      if (events.length > 1)
        Positioned.fill(
          child: _CardFrame(
            scale: 0.95,
            child: EventCard(event: events[1]),
          ),
        ),
      if (events.isNotEmpty) _buildFront(events.first),
    ];

    return Column(
      children: [
        Expanded(child: Stack(children: children)),
        const SizedBox(height: 16),
        _SwipeActions(
          onPass: () => _swipeFromButton(_pass),
          onLike: () => _swipeFromButton(_like),
        ),
      ],
    );
  }

  Widget _buildFront(Event event) {
    final width = MediaQuery.of(context).size.width;
    // Tilt up to ~12° based on how far the card has been dragged sideways.
    final angle = (_drag.dx / width) * 0.4;
    // Fade in a LIKE / NOPE stamp as the card approaches the commit distance.
    final stampOpacity = (_drag.dx.abs() / _commitDistance).clamp(0.0, 1.0);

    return Positioned.fill(
      child: GestureDetector(
        onPanUpdate: _onPanUpdate,
        onPanEnd: _onPanEnd,
        child: Transform.translate(
          offset: _drag,
          child: Transform.rotate(
            angle: angle,
            child: Stack(
              children: [
                Positioned.fill(child: EventCard(event: event)),
                if (_drag.dx > 0)
                  _SwipeStamp(
                    label: 'LIKE',
                    color: Colors.green,
                    alignment: Alignment.topLeft,
                    angle: -0.4,
                    opacity: stampOpacity,
                  ),
                if (_drag.dx < 0)
                  _SwipeStamp(
                    label: 'NOPE',
                    color: Colors.red,
                    alignment: Alignment.topRight,
                    angle: 0.4,
                    opacity: stampOpacity,
                  ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

/// Wraps a card so the one behind sits slightly scaled down and pinned to the
/// bottom, peeking out beneath the front card.
class _CardFrame extends StatelessWidget {
  const _CardFrame({required this.scale, required this.child});

  final double scale;
  final Widget child;

  @override
  Widget build(BuildContext context) {
    return Transform.scale(
      scale: scale,
      alignment: Alignment.bottomCenter,
      child: child,
    );
  }
}

/// The pass / like buttons. They drive the same animated swipe as a gesture,
/// so they work as an accessible alternative to dragging.
class _SwipeActions extends StatelessWidget {
  const _SwipeActions({required this.onPass, required this.onLike});

  final VoidCallback onPass;
  final VoidCallback onLike;

  @override
  Widget build(BuildContext context) {
    return Row(
      mainAxisAlignment: MainAxisAlignment.spaceEvenly,
      children: [
        FloatingActionButton(
          heroTag: 'pass',
          backgroundColor: Colors.red,
          onPressed: onPass,
          tooltip: 'Pass',
          child: const Icon(Icons.close),
        ),
        FloatingActionButton(
          heroTag: 'like',
          backgroundColor: Colors.green,
          onPressed: onLike,
          tooltip: 'Like',
          child: const Icon(Icons.favorite),
        ),
      ],
    );
  }
}

/// The translucent "LIKE" / "NOPE" stamp that fades in during a drag.
class _SwipeStamp extends StatelessWidget {
  const _SwipeStamp({
    required this.label,
    required this.color,
    required this.alignment,
    required this.angle,
    required this.opacity,
  });

  final String label;
  final Color color;
  final Alignment alignment;
  final double angle;
  final double opacity;

  @override
  Widget build(BuildContext context) {
    return Positioned.fill(
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: Align(
          alignment: alignment,
          child: Opacity(
            opacity: opacity,
            child: Transform.rotate(
              angle: angle,
              child: Container(
                padding:
                    const EdgeInsets.symmetric(horizontal: 12, vertical: 4),
                decoration: BoxDecoration(
                  border: Border.all(color: color, width: 4),
                  borderRadius: BorderRadius.circular(8),
                ),
                child: Text(
                  label,
                  style: TextStyle(
                    color: color,
                    fontSize: 36,
                    fontWeight: FontWeight.w800,
                    letterSpacing: 2,
                  ),
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }
}

/// A single event card: image header (when present), title, category,
/// distance, time, and a scrollable description.
class EventCard extends StatelessWidget {
  const EventCard({super.key, required this.event});

  final Event event;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Card(
      clipBehavior: Clip.antiAlias,
      elevation: 4,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(16),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          if (event.imageUrl != null && event.imageUrl!.isNotEmpty)
            _CardImage(url: event.imageUrl!),
          Expanded(
            child: Padding(
              padding: const EdgeInsets.all(20),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    event.title,
                    style: theme.textTheme.headlineSmall
                        ?.copyWith(fontWeight: FontWeight.w600),
                  ),
                  const SizedBox(height: 12),
                  _CardMeta(event: event),
                  const SizedBox(height: 16),
                  Expanded(
                    child: SingleChildScrollView(
                      child: Text(
                        event.description,
                        style: theme.textTheme.bodyMedium,
                      ),
                    ),
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _CardImage extends StatelessWidget {
  const _CardImage({required this.url});

  final String url;

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      height: 180,
      width: double.infinity,
      child: Image.network(
        url,
        fit: BoxFit.cover,
        // Keep the card lean if an image fails: collapse to nothing.
        errorBuilder: (_, __, ___) => const SizedBox.shrink(),
        loadingBuilder: (context, child, progress) {
          if (progress == null) return child;
          return const ColoredBox(
            color: Color(0x11000000),
            child: Center(child: CircularProgressIndicator()),
          );
        },
      ),
    );
  }
}

/// The category chip plus distance and time, laid out as a wrapping row of
/// small labelled facts.
class _CardMeta extends StatelessWidget {
  const _CardMeta({required this.event});

  final Event event;

  @override
  Widget build(BuildContext context) {
    return Wrap(
      spacing: 12,
      runSpacing: 8,
      crossAxisAlignment: WrapCrossAlignment.center,
      children: [
        Chip(
          label: Text(event.category),
          visualDensity: VisualDensity.compact,
        ),
        if (event.distanceKm != null)
          _MetaFact(
            icon: Icons.place_outlined,
            text: formatDistance(event.distanceKm!),
          ),
        if (event.startsAt != null)
          _MetaFact(
            icon: Icons.schedule,
            text: formatEventTime(event.startsAt!),
          ),
      ],
    );
  }
}

class _MetaFact extends StatelessWidget {
  const _MetaFact({required this.icon, required this.text});

  final IconData icon;
  final String text;

  @override
  Widget build(BuildContext context) {
    final color = Theme.of(context).colorScheme.onSurfaceVariant;
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        Icon(icon, size: 16, color: color),
        const SizedBox(width: 4),
        Text(
          text,
          style: Theme.of(context)
              .textTheme
              .bodyMedium
              ?.copyWith(color: color),
        ),
      ],
    );
  }
}

