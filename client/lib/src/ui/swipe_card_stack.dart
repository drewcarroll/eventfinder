import 'package:flutter/material.dart';

import '../models/event.dart';
import 'event_format.dart';
import 'theme/app_theme.dart';

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
    // How far the front card has been dragged toward a commit, 0..1. The card
    // behind grows toward full size as the front one leaves, à la Tinder.
    final progress = (_drag.dx.abs() / _commitDistance).clamp(0.0, 1.0);
    final children = <Widget>[
      if (events.length > 1)
        Positioned.fill(
          child: _CardFrame(
            scale: 0.92 + 0.08 * progress,
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
                    color: AppColors.like,
                    alignment: Alignment.topLeft,
                    angle: -0.4,
                    opacity: stampOpacity,
                  ),
                if (_drag.dx < 0)
                  _SwipeStamp(
                    label: 'NOPE',
                    color: AppColors.pass,
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
      mainAxisAlignment: MainAxisAlignment.center,
      children: [
        _CircleAction(
          icon: Icons.close_rounded,
          tooltip: 'Pass',
          size: 62,
          iconColor: AppColors.pass,
          onPressed: onPass,
        ),
        const SizedBox(width: 36),
        _CircleAction(
          icon: Icons.favorite_rounded,
          tooltip: 'Like',
          size: 72,
          fill: AppColors.like,
          glow: AppColors.like,
          iconColor: Colors.white,
          onPressed: onLike,
        ),
      ],
    );
  }
}

/// A circular action button that dips slightly on press. With a [gradient] it
/// reads as a primary action; without, it's an outlined surface button.
class _CircleAction extends StatefulWidget {
  const _CircleAction({
    required this.icon,
    required this.tooltip,
    required this.size,
    required this.iconColor,
    required this.onPressed,
    this.fill,
    this.glow,
  });

  final IconData icon;
  final String tooltip;
  final double size;
  final Color iconColor;
  final VoidCallback onPressed;
  final Color? fill;
  final Color? glow;

  @override
  State<_CircleAction> createState() => _CircleActionState();
}

class _CircleActionState extends State<_CircleAction> {
  bool _down = false;

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    final filled = widget.fill != null;
    return Tooltip(
      message: widget.tooltip,
      child: GestureDetector(
        onTapDown: (_) => setState(() => _down = true),
        onTapUp: (_) => setState(() => _down = false),
        onTapCancel: () => setState(() => _down = false),
        onTap: widget.onPressed,
        child: AnimatedScale(
          scale: _down ? 0.88 : 1,
          duration: const Duration(milliseconds: 120),
          curve: Curves.easeOut,
          child: Container(
            height: widget.size,
            width: widget.size,
            decoration: BoxDecoration(
              shape: BoxShape.circle,
              color: filled ? widget.fill : scheme.surface,
              border: filled
                  ? null
                  : Border.all(color: scheme.outlineVariant, width: 1.5),
              boxShadow: [
                BoxShadow(
                  color: (widget.glow ?? Colors.black)
                      .withValues(alpha: filled ? 0.4 : 0.1),
                  blurRadius: filled ? 22 : 12,
                  offset: const Offset(0, 8),
                ),
              ],
            ),
            child: Icon(
              widget.icon,
              color: widget.iconColor,
              size: widget.size * 0.42,
            ),
          ),
        ),
      ),
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
        padding: const EdgeInsets.all(28),
        child: Align(
          alignment: alignment,
          child: Opacity(
            opacity: opacity,
            child: Transform.rotate(
              angle: angle,
              child: Container(
                padding:
                    const EdgeInsets.symmetric(horizontal: 16, vertical: 6),
                decoration: BoxDecoration(
                  color: color.withValues(alpha: 0.16),
                  border: Border.all(color: color, width: 4),
                  borderRadius: BorderRadius.circular(14),
                  boxShadow: [
                    BoxShadow(
                      color: color.withValues(alpha: 0.35),
                      blurRadius: 18,
                    ),
                  ],
                ),
                child: Text(
                  label,
                  style: TextStyle(
                    color: color,
                    fontSize: 38,
                    fontWeight: FontWeight.w900,
                    letterSpacing: 3,
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
    final hasImage = event.imageUrl != null && event.imageUrl!.isNotEmpty;
    return Container(
      clipBehavior: Clip.antiAlias,
      decoration: BoxDecoration(
        color: theme.colorScheme.surface,
        borderRadius: BorderRadius.circular(AppRadii.lg),
        boxShadow: [
          BoxShadow(
            color: AppColors.blue.withValues(alpha: 0.16),
            blurRadius: 34,
            offset: const Offset(0, 16),
          ),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          if (hasImage)
            _CardImage(url: event.imageUrl!, category: event.category),
          Expanded(
            child: Padding(
              padding: const EdgeInsets.fromLTRB(22, 20, 22, 20),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  // With no image, the category needs a home up top.
                  if (!hasImage) ...[
                    _CategoryChip(label: event.category),
                    const SizedBox(height: 14),
                  ],
                  Text(
                    event.title,
                    style: theme.textTheme.headlineSmall,
                  ),
                  const SizedBox(height: 14),
                  _CardMeta(event: event),
                  const SizedBox(height: 16),
                  Expanded(
                    child: ShaderMask(
                      // Fade the description out at the bottom edge so longer
                      // copy hints that it scrolls rather than hard-clipping.
                      shaderCallback: (bounds) => const LinearGradient(
                        begin: Alignment.topCenter,
                        end: Alignment.bottomCenter,
                        colors: [Colors.white, Colors.white, Colors.transparent],
                        stops: [0, 0.85, 1],
                      ).createShader(bounds),
                      blendMode: BlendMode.dstIn,
                      child: SingleChildScrollView(
                        child: Text(
                          event.description,
                          style: theme.textTheme.bodyLarge?.copyWith(
                            color: theme.colorScheme.onSurfaceVariant,
                          ),
                        ),
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
  const _CardImage({required this.url, required this.category});

  final String url;
  final String category;

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      height: 220,
      width: double.infinity,
      child: Stack(
        fit: StackFit.expand,
        children: [
          Image.network(
            url,
            fit: BoxFit.cover,
            // Keep the card lean if an image fails: collapse to nothing.
            errorBuilder: (_, __, ___) => const SizedBox.shrink(),
            loadingBuilder: (context, child, progress) {
              if (progress == null) return child;
              return ColoredBox(
                color: Theme.of(context).colorScheme.surfaceContainerHighest,
                child: const Center(child: CircularProgressIndicator()),
              );
            },
          ),
          // Scrim so the overlaid chip stays legible over bright photos.
          const DecoratedBox(
            decoration: BoxDecoration(gradient: AppGradients.scrim),
          ),
          Positioned(
            left: 14,
            bottom: 14,
            child: _CategoryChip(label: category, onImage: true),
          ),
        ],
      ),
    );
  }
}

/// The category pill. Over imagery it uses a translucent dark fill; on the card
/// body it uses the brand gradient.
class _CategoryChip extends StatelessWidget {
  const _CategoryChip({required this.label, this.onImage = false});

  final String label;
  final bool onImage;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 7),
      decoration: BoxDecoration(
        color: onImage ? Colors.black.withValues(alpha: 0.45) : AppColors.pink,
        borderRadius: BorderRadius.circular(AppRadii.pill),
        border: onImage
            ? Border.all(color: Colors.white.withValues(alpha: 0.4))
            : null,
      ),
      child: Text(
        label,
        style: const TextStyle(
          color: Colors.white,
          fontSize: 12,
          fontWeight: FontWeight.w700,
          letterSpacing: 0.4,
        ),
      ),
    );
  }
}

/// Distance and time, laid out as a wrapping row of small labelled facts.
class _CardMeta extends StatelessWidget {
  const _CardMeta({required this.event});

  final Event event;

  @override
  Widget build(BuildContext context) {
    // Prefer a real availability range; show no time at all rather than a
    // misleading single clock value when the source gave no times.
    final window =
        event.availabilityTimes.isNotEmpty ? event.availabilityTimes.first : null;
    return Wrap(
      spacing: 16,
      runSpacing: 8,
      crossAxisAlignment: WrapCrossAlignment.center,
      children: [
        if (event.distanceKm != null)
          _MetaFact(
            icon: Icons.place_outlined,
            text: formatDistance(event.distanceKm!),
          ),
        if (window != null)
          _MetaFact(
            icon: Icons.schedule_rounded,
            text: formatTimeRange(window.start, window.end),
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
    final scheme = Theme.of(context).colorScheme;
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        Icon(icon, size: 17, color: scheme.primary),
        const SizedBox(width: 5),
        // Flexible so a long fact ellipsizes within the row's width instead of
        // overflowing the card (the row is bounded by the surrounding Wrap).
        Flexible(
          child: Text(
            text,
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
            style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                  color: scheme.onSurfaceVariant,
                  fontWeight: FontWeight.w600,
                ),
          ),
        ),
      ],
    );
  }
}

