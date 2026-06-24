import 'package:flutter/material.dart';

import '../theme/app_theme.dart';

/// Paints its [child] (typically [Text] or an [Icon]) with a gradient by
/// masking the gradient through the child's own shape.
class GradientText extends StatelessWidget {
  const GradientText(
    this.text, {
    super.key,
    this.style,
    this.gradient = AppGradients.brand,
    this.textAlign,
  });

  final String text;
  final TextStyle? style;
  final Gradient gradient;
  final TextAlign? textAlign;

  @override
  Widget build(BuildContext context) {
    return ShaderMask(
      blendMode: BlendMode.srcIn,
      shaderCallback: (bounds) => gradient.createShader(
        Rect.fromLTWH(0, 0, bounds.width, bounds.height),
      ),
      child: Text(
        text,
        textAlign: textAlign,
        style: (style ?? const TextStyle()).copyWith(color: Colors.white),
      ),
    );
  }
}

/// A pill-shaped primary CTA: a solid blue fill with an ink ripple and a soft
/// shadow. Renders muted when [onPressed] is null.
class PrimaryButton extends StatelessWidget {
  const PrimaryButton({
    super.key,
    required this.onPressed,
    required this.label,
    this.icon,
    this.color,
    this.expand = false,
  });

  final VoidCallback? onPressed;
  final String label;
  final IconData? icon;
  final Color? color;
  final bool expand;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final enabled = onPressed != null;
    final fill = color ?? AppColors.blue;
    final radius = BorderRadius.circular(AppRadii.pill);

    return Opacity(
      opacity: enabled ? 1 : 0.5,
      child: DecoratedBox(
        decoration: BoxDecoration(
          borderRadius: radius,
          color: fill,
          boxShadow: enabled
              ? [
                  BoxShadow(
                    color: fill.withValues(alpha: 0.32),
                    blurRadius: 20,
                    offset: const Offset(0, 9),
                  ),
                ]
              : null,
        ),
        child: Material(
          color: Colors.transparent,
          child: InkWell(
            borderRadius: radius,
            onTap: onPressed,
            child: Container(
              height: 54,
              width: expand ? double.infinity : null,
              padding: const EdgeInsets.symmetric(horizontal: 28),
              alignment: Alignment.center,
              child: Row(
                mainAxisSize: MainAxisSize.min,
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  if (icon != null) ...[
                    Icon(icon, color: Colors.white, size: 20),
                    const SizedBox(width: 10),
                  ],
                  Text(
                    label,
                    style: theme.textTheme.titleMedium?.copyWith(
                      color: Colors.white,
                      fontWeight: FontWeight.w700,
                    ),
                  ),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}

/// Fades and lifts its [child] into place once, on first build. Used to give
/// content a soft entrance instead of popping in.
class FadeSlideIn extends StatefulWidget {
  const FadeSlideIn({
    super.key,
    required this.child,
    this.delay = Duration.zero,
    this.offset = const Offset(0, 0.06),
    this.duration = const Duration(milliseconds: 480),
  });

  final Widget child;
  final Duration delay;
  final Offset offset;
  final Duration duration;

  @override
  State<FadeSlideIn> createState() => _FadeSlideInState();
}

class _FadeSlideInState extends State<FadeSlideIn>
    with SingleTickerProviderStateMixin {
  late final AnimationController _controller = AnimationController(
    vsync: this,
    duration: widget.duration,
  );
  late final Animation<double> _curve = CurvedAnimation(
    parent: _controller,
    curve: Curves.easeOutCubic,
  );

  @override
  void initState() {
    super.initState();
    if (widget.delay == Duration.zero) {
      _controller.forward();
    } else {
      Future<void>.delayed(widget.delay, () {
        if (mounted) _controller.forward();
      });
    }
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return FadeTransition(
      opacity: _curve,
      child: SlideTransition(
        position: Tween<Offset>(begin: widget.offset, end: Offset.zero)
            .animate(_curve),
        child: widget.child,
      ),
    );
  }
}

/// A looping shimmer used as a graceful placeholder while content loads.
class Shimmer extends StatefulWidget {
  const Shimmer({
    super.key,
    this.width = double.infinity,
    required this.height,
    this.radius = AppRadii.sm,
  });

  final double width;
  final double height;
  final double radius;

  @override
  State<Shimmer> createState() => _ShimmerState();
}

class _ShimmerState extends State<Shimmer>
    with SingleTickerProviderStateMixin {
  late final AnimationController _controller = AnimationController(
    vsync: this,
    duration: const Duration(milliseconds: 1300),
  )..repeat();

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    final base = scheme.surfaceContainerHighest;
    final highlight = Color.alphaBlend(
      scheme.onSurface.withValues(alpha: 0.06),
      base,
    );
    return AnimatedBuilder(
      animation: _controller,
      builder: (context, _) {
        return Container(
          width: widget.width,
          height: widget.height,
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(widget.radius),
            gradient: LinearGradient(
              begin: Alignment(-1 - 2 * _controller.value, 0),
              end: Alignment(1 - 2 * _controller.value, 0),
              colors: [base, highlight, base],
              stops: const [0.35, 0.5, 0.65],
            ),
          ),
        );
      },
    );
  }
}
