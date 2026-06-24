import 'dart:async';

import 'package:flutter/material.dart';

import '../data/device_location_service.dart';
import '../data/event_api.dart';
import '../data/filter_service.dart';
import '../data/location_service.dart';
import '../models/event.dart';
import 'filter_sheet.dart';
import 'swipe_card_stack.dart';
import 'theme/app_theme.dart';
import 'widgets/brand_widgets.dart';

/// The interest the feed searches for. Combined with the location to form the
/// backend query, e.g. "things to do near Mountain View". Kept broad so the
/// feed surfaces a varied stream of specific ideas — a drink, a concert, a
/// park — rather than one narrow category.
const String _interest = 'things to do';

class FeedScreen extends StatefulWidget {
  const FeedScreen({
    super.key,
    required this.api,
    required this.locationService,
    required this.filterService,
  });

  final EventApi api;
  final LocationService locationService;
  final FilterService filterService;

  @override
  State<FeedScreen> createState() => _FeedScreenState();
}

class _FeedScreenState extends State<FeedScreen> {
  // The full set of ideas the current generation produced. Kept intact so a
  // pass through the deck can start over from the first idea.
  List<Event> _allEvents = [];
  // The cards still to be shown this pass. A swipe removes the front card;
  // when it empties, the user has reached the end of the deck.
  List<Event> _deck = [];
  // True once the deck has been swiped through. The end card replaces the
  // stack and invites starting over (or refreshing for new ideas).
  bool _reachedEnd = false;
  // The app opens idle: no feed fetch, no spinner, no location capture. The
  // body lands on the "set your location" placeholder, and the user kicks off
  // the first search themselves (via the searchbar), keeping cold-open instant.
  bool _loading = false;
  String? _error;

  // Identifies the location + filters the currently loaded feed was fetched
  // for. A reload whose signature matches reuses the cached feed instead of
  // re-running the (credit-costing) ideas pipeline.
  String? _loadedSignature;
  // Smallest gap between two explicit refreshes. Rapid taps inside this window
  // are ignored so a user can't spam the pipeline and burn credits.
  static const Duration _refreshCooldown = Duration(seconds: 10);
  DateTime? _lastRefreshAt;

  // Backs the top searchbar. Empty by default (no auto-prompt) and kept in
  // sync with the active location so the bar doubles as a "current location"
  // shower: the manual override's name, or "My location" for a GPS fix.
  late final TextEditingController _locationController =
      TextEditingController(text: _locationLabel());

  @override
  void dispose() {
    _locationController.dispose();
    super.dispose();
  }

  /// The text the searchbar shows for the active location: the manual
  /// override's name, "My location" for a GPS fix, or empty when none is set.
  String _locationLabel() {
    final location = widget.locationService;
    if (location.hasOverride) return location.manualOverride!.displayName;
    if (location.hasLocation) return 'My location';
    return '';
  }

  /// Capture the device's GPS position and adopt it as the search location.
  /// Invoked only by an explicit user action (the searchbar's "use my
  /// location" button) — never on launch. Requesting the position triggers the
  /// OS permission prompt on first use. When permission is denied or location
  /// services are off, surface a message and leave the searchbar for manual
  /// entry. Does not fetch the feed — generation stays an explicit action.
  Future<void> _useDeviceLocation() async {
    final location = widget.locationService;
    if (!location.hasLocation) {
      final outcome = await location.captureDeviceLocation();
      if (outcome != LocationPermissionOutcome.granted) {
        if (!mounted) return;
        final String message;
        switch (outcome) {
          case LocationPermissionOutcome.serviceDisabled:
            message = 'Location services are off. Enter a location to search.';
          case LocationPermissionOutcome.unavailable:
            message = "Couldn't get your location. Enter one to search.";
          case LocationPermissionOutcome.denied:
          case LocationPermissionOutcome.granted:
            message = 'Location permission denied. Enter a location to search.';
        }
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text(message)),
        );
        return;
      }
    }
    if (!mounted) return;
    setState(() {
      location.clearOverride();
      _locationController.text = _locationLabel();
    });
  }

  /// Resolve the text typed into the searchbar to coordinates on the backend
  /// and adopt it as the search location. Does not fetch the feed — running
  /// the pipeline is an explicit action ("Generate ideas" / refresh), so this
  /// just updates the placeholder to invite generation.
  Future<void> _searchLocation(String query) async {
    final trimmed = query.trim();
    if (trimmed.isEmpty) return;
    try {
      final resolved = await widget.api.resolveLocation(trimmed);
      if (!mounted) return;
      setState(() {
        widget.locationService.setManualOverride(resolved);
        _locationController.text = resolved.displayName;
      });
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(
            'Location set to ${resolved.displayName}. Tap Generate ideas.',
          ),
        ),
      );
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('$e')),
      );
    }
  }

  /// A stable identity for "the feed the current location + filters would
  /// produce". Two loads with the same signature would re-run the pipeline for
  /// identical inputs, so a matching signature lets us reuse the cached feed.
  String _feedSignature() {
    final f = widget.filterService.filters;
    return [
      widget.locationService.searchLabel,
      f.maxDistanceKm,
      f.timeRange.name,
      f.customStart?.toIso8601String() ?? '',
      f.customEnd?.toIso8601String() ?? '',
    ].join('|');
  }

  /// (Re)load the feed for the current location + filters.
  ///
  /// Unless [force] is set, a load whose location + filters are unchanged from
  /// the loaded feed reuses the cached ideas instead of re-running the ideas
  /// pipeline — avoiding a needless, credit-costing fetch. Explicit refresh
  /// passes [force] to always re-run and generate an entirely new set.
  Future<void> _load({bool force = false}) async {
    // Can't search without somewhere to search around. The "Generate ideas"
    // button prompts for a location; this guards every other caller too.
    if (!widget.locationService.hasLocation) return;
    final signature = _feedSignature();
    if (!force && signature == _loadedSignature && _allEvents.isNotEmpty) {
      // Same location + filters and we still hold a feed: start a fresh pass
      // over the cached ideas, no network/pipeline work.
      setState(() {
        _error = null;
        _deck = List.of(_allEvents);
        _reachedEnd = false;
      });
      return;
    }
    setState(() {
      _loading = true;
      _error = null;
      _reachedEnd = false;
    });
    try {
      // Provision/refresh the user record on the backend before fetching.
      await widget.api.syncUser();
      // Search around the active location: the manual override if set,
      // otherwise "near me" (the device's GPS position).
      final query = '$_interest near ${widget.locationService.searchLabel}';
      // Apply the filters: search radius and a time window resolved from the
      // chosen preset (tonight / this weekend / custom).
      final filters = widget.filterService.filters;
      final window = filters.resolveWindow(DateTime.now());
      final events = await widget.api.fetchFeed(
        query,
        radiusKm: filters.maxDistanceKm,
        startsAfter: window.start,
        startsBefore: window.end,
      );
      setState(() {
        _allEvents = events;
        _deck = List.of(events);
        // Remember what these ideas were fetched for, so an unchanged reload
        // can reuse them.
        _loadedSignature = signature;
        _reachedEnd = false;
        _loading = false;
      });
    } catch (e) {
      setState(() {
        _error = '$e';
        _loading = false;
      });
    }
  }

  /// Explicit refresh: re-run the ideas pipeline for the current location +
  /// filters, generating an entirely new set. Guarded against credit waste by
  /// a [_refreshCooldown] debounce so rapid repeated taps don't fire repeated
  /// pipeline runs.
  Future<void> _refresh() async {
    // Nothing to refresh until a location is set.
    if (!widget.locationService.hasLocation) return;
    final now = DateTime.now();
    if (_lastRefreshAt != null &&
        now.difference(_lastRefreshAt!) < _refreshCooldown) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Just refreshed — give it a moment.')),
      );
      return;
    }
    _lastRefreshAt = now;
    await _load(force: true);
  }

  /// Explicit generation from the blank placeholder card: run the ideas
  /// pipeline for the current location + filters. With no location set yet,
  /// prompt the user to choose one first rather than searching around nothing.
  Future<void> _generateEvents() async {
    if (!widget.locationService.hasLocation) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Set a location first — search the bar up top.'),
        ),
      );
      return;
    }
    await _load(force: true);
  }

  void _swipe(Event event, String direction) {
    // Right/like persists the idea immediately (fire-and-forget); left/pass
    // is discarded. There's no session — each yes stands on its own.
    if (direction == 'like') {
      unawaited(_persistLike(event));
    }
    setState(() {
      _deck = _deck.where((e) => e.id != event.id).toList();
      // Reaching the end of the deck stops the stack and shows the end card,
      // rather than auto-recycling — the user chooses to start over.
      if (_deck.isEmpty) _reachedEnd = true;
    });
  }

  /// Persist a liked idea, surfacing a quiet message if the save can't be
  /// reached. The swipe itself isn't blocked on this.
  Future<void> _persistLike(Event event) async {
    try {
      await widget.api.likeIdea(event);
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text("Couldn't save your like: $e")),
      );
    }
  }

  /// Start the deck over from the first idea (the same generated set). New
  /// ideas come only from an explicit refresh.
  void _startOver() {
    setState(() {
      _deck = List.of(_allEvents);
      _reachedEnd = false;
    });
  }

  /// Open the filter sheet and, if the user applies changes, store them and
  /// reload the feed with the new distance/time window.
  Future<void> _changeFilters() async {
    final updated = await showFilterSheet(
      context,
      widget.filterService.filters,
    );
    if (updated == null) return; // Dismissed without applying.
    widget.filterService.update(updated);
    await _load();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: SafeArea(
        bottom: false,
        child: Column(
          children: [
            const SizedBox(height: 8),
            _buildLocationBar(),
            _buildActionBar(),
            Expanded(child: _buildBody()),
          ],
        ),
      ),
    );
  }

  /// The reload + filter controls, sitting just below the searchbar so the
  /// search field stays the top-most affordance. Right-aligned to echo the
  /// trailing-action placement they used to have in the AppBar.
  Widget _buildActionBar() {
    final canRefresh = widget.locationService.hasLocation;
    return Padding(
      padding: const EdgeInsets.fromLTRB(20, 4, 20, 4),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.end,
        children: [
          _SoftIconButton(
            icon: Icons.refresh_rounded,
            tooltip: 'New ideas',
            onPressed: canRefresh ? _refresh : null,
          ),
          const SizedBox(width: 10),
          _SoftIconButton(
            icon: Icons.tune_rounded,
            tooltip: 'Filters',
            onPressed: _changeFilters,
          ),
        ],
      ),
    );
  }

  /// The top location bar: a searchbar that doubles as a "current location"
  /// shower. Empty by default with no auto-prompt; submitting a place resolves
  /// it. The trailing button captures the device's GPS position instead.
  Widget _buildLocationBar() {
    return Padding(
      padding: const EdgeInsets.fromLTRB(20, 12, 20, 4),
      child: TextField(
        controller: _locationController,
        textInputAction: TextInputAction.search,
        onSubmitted: _searchLocation,
        decoration: InputDecoration(
          hintText: 'Search a place…',
          prefixIcon: const Icon(Icons.search_rounded),
          suffixIcon: IconButton(
            icon: const Icon(Icons.my_location_rounded),
            tooltip: 'Use my location',
            color: Theme.of(context).colorScheme.primary,
            onPressed: _useDeviceLocation,
          ),
          border: OutlineInputBorder(
            borderRadius: BorderRadius.circular(AppRadii.pill),
          ),
          enabledBorder: OutlineInputBorder(
            borderRadius: BorderRadius.circular(AppRadii.pill),
            borderSide: const BorderSide(color: Color(0xFFE6E1F2)),
          ),
          focusedBorder: OutlineInputBorder(
            borderRadius: BorderRadius.circular(AppRadii.pill),
            borderSide: BorderSide(
              color: Theme.of(context).colorScheme.primary,
              width: 1.8,
            ),
          ),
        ),
      ),
    );
  }

  /// The blank placeholder shown when there's no feed yet. Its "Generate
  /// ideas" button is the explicit trigger for the ideas pipeline. With no
  /// location set, the copy points at the searchbar and tapping prompts the
  /// user to choose one first.
  Widget _buildGeneratePlaceholder() {
    final hasLocation = widget.locationService.hasLocation;
    return _StateCard(
      icon:
          hasLocation ? Icons.auto_awesome_rounded : Icons.location_on_rounded,
      title: hasLocation ? 'Ready to find ideas' : 'Set your location',
      message: hasLocation
          ? 'Generate ideas near ${_locationLabel()} with your current filters.'
          : 'Search for a place in the bar above, then generate ideas.',
      primaryLabel: 'Generate ideas',
      primaryIcon: Icons.auto_awesome_rounded,
      onPrimary: _generateEvents,
    );
  }

  /// Shown after a generation that genuinely came back empty: nudge the user
  /// to widen the search, with a one-tap way to run it again.
  Widget _buildNoEventsCard() {
    return _StateCard(
      icon: Icons.event_busy_rounded,
      title: 'No ideas found near here',
      message: 'Try widening your distance or time range, '
          'or searching a different spot.',
      primaryLabel: 'Adjust filters',
      primaryIcon: Icons.tune_rounded,
      onPrimary: _changeFilters,
      secondaryLabel: 'Generate again',
      onSecondary: _generateEvents,
    );
  }

  /// Shown when the user has swiped through every idea in the deck. Offers to
  /// run back through the same ideas, or to generate a brand-new set.
  Widget _buildReachedEndCard() {
    return _StateCard(
      icon: Icons.replay_rounded,
      title: 'Reached the end!',
      message: "You've seen every idea in this batch. Start again from the "
          'top, or refresh for a fresh set.',
      primaryLabel: 'Start again',
      primaryIcon: Icons.replay_rounded,
      onPrimary: _startOver,
      secondaryLabel: 'Generate new ideas',
      onSecondary: _refresh,
    );
  }

  Widget _buildBody() {
    if (_loading) {
      return const _FeedLoading();
    }
    if (_error != null) {
      return _StateCard(
        icon: Icons.error_outline_rounded,
        title: 'Something went wrong',
        message: _error!,
        primaryLabel: 'Try again',
        primaryIcon: Icons.refresh_rounded,
        onPrimary: _refresh,
      );
    }
    // No feed yet. The pipeline never runs on its own — show the blank
    // placeholder card whose "Generate ideas" button is the explicit trigger.
    if (_allEvents.isEmpty) {
      // Distinguish "haven't generated for these inputs yet" from "generated
      // and the pipeline genuinely returned nothing": only the latter shows
      // the widen-your-search nudge, so we don't cry "no ideas" before the
      // user has asked for any.
      final generatedAndEmpty = widget.locationService.hasLocation &&
          _loadedSignature == _feedSignature();
      return generatedAndEmpty
          ? _buildNoEventsCard()
          : _buildGeneratePlaceholder();
    }
    // Swiped through the whole deck: invite starting over or refreshing.
    if (_reachedEnd) {
      return _buildReachedEndCard();
    }

    final filters = widget.filterService.filters;
    return Padding(
      padding: const EdgeInsets.fromLTRB(20, 8, 20, 16),
      child: Column(
        children: [
          Align(
            alignment: Alignment.centerLeft,
            child: _FilterPill(
              label: '${filters.timeRangeSummary} · '
                  '${filters.maxDistanceKm.round()} km',
              onTap: _changeFilters,
            ),
          ),
          const SizedBox(height: 14),
          Expanded(
            child: SwipeCardStack(
              events: _deck,
              onSwipe: _swipe,
            ),
          ),
        ],
      ),
    );
  }
}

/// A soft, square icon button used for the feed's secondary actions. Renders
/// muted when disabled.
class _SoftIconButton extends StatelessWidget {
  const _SoftIconButton({
    required this.icon,
    required this.tooltip,
    required this.onPressed,
  });

  final IconData icon;
  final String tooltip;
  final VoidCallback? onPressed;

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    final enabled = onPressed != null;
    return Tooltip(
      message: tooltip,
      child: Material(
        color: scheme.surfaceContainerHighest,
        borderRadius: BorderRadius.circular(AppRadii.sm),
        child: InkWell(
          borderRadius: BorderRadius.circular(AppRadii.sm),
          onTap: onPressed,
          child: Padding(
            padding: const EdgeInsets.all(11),
            child: Icon(
              icon,
              size: 22,
              color: enabled ? scheme.primary : scheme.onSurfaceVariant,
            ),
          ),
        ),
      ),
    );
  }
}

/// The current-filters summary pill above the deck, tinted with the brand.
class _FilterPill extends StatelessWidget {
  const _FilterPill({required this.label, required this.onTap});

  final String label;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    const accent = AppColors.pink;
    return Material(
      color: accent.withValues(alpha: 0.1),
      borderRadius: BorderRadius.circular(AppRadii.pill),
      child: InkWell(
        borderRadius: BorderRadius.circular(AppRadii.pill),
        onTap: onTap,
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 9),
          child: Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              const Icon(Icons.tune_rounded, size: 16, color: accent),
              const SizedBox(width: 7),
              Text(
                label,
                style: Theme.of(context).textTheme.labelLarge?.copyWith(
                      color: accent,
                      fontWeight: FontWeight.w700,
                    ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

/// A skeleton placeholder for the deck while ideas are generated.
class _FeedLoading extends StatelessWidget {
  const _FeedLoading();

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.fromLTRB(20, 8, 20, 16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Shimmer(height: 36, width: 150, radius: AppRadii.pill),
          const SizedBox(height: 14),
          const Expanded(
              child: Shimmer(height: double.infinity, radius: AppRadii.lg)),
          const SizedBox(height: 16),
          Row(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              GradientText(
                'Conjuring ideas…',
                style: Theme.of(context).textTheme.titleMedium,
              ),
            ],
          ),
          const SizedBox(height: 8),
        ],
      ),
    );
  }
}

/// A centred empty/placeholder card: an icon badge, a title, a message, and
/// one or two actions, wrapped in a surface card. Scrolls if it can't fit
/// (e.g. with the keyboard up) so it never overflows. Animates in softly.
class _StateCard extends StatelessWidget {
  const _StateCard({
    required this.icon,
    required this.title,
    required this.message,
    required this.primaryLabel,
    required this.primaryIcon,
    required this.onPrimary,
    this.secondaryLabel,
    this.onSecondary,
  });

  final IconData icon;
  final String title;
  final String message;
  final String primaryLabel;
  final IconData primaryIcon;
  final VoidCallback onPrimary;
  final String? secondaryLabel;
  final VoidCallback? onSecondary;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return LayoutBuilder(
      builder: (context, constraints) => SingleChildScrollView(
        padding: const EdgeInsets.all(24),
        child: ConstrainedBox(
          // Fill the viewport so the card centres when there's room, but let
          // it scroll (rather than overflow) when the keyboard shrinks us.
          constraints: BoxConstraints(minHeight: constraints.maxHeight - 48),
          child: Center(
            child: FadeSlideIn(
              child: Container(
                width: double.infinity,
                padding:
                    const EdgeInsets.symmetric(horizontal: 24, vertical: 32),
                decoration: BoxDecoration(
                  color: theme.colorScheme.surface,
                  borderRadius: BorderRadius.circular(AppRadii.lg),
                  boxShadow: [
                    BoxShadow(
                      color: AppColors.blue.withValues(alpha: 0.1),
                      blurRadius: 30,
                      offset: const Offset(0, 14),
                    ),
                  ],
                ),
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Container(
                      height: 84,
                      width: 84,
                      decoration: BoxDecoration(
                        color: AppColors.blue.withValues(alpha: 0.12),
                        borderRadius: BorderRadius.circular(24),
                      ),
                      child: Icon(icon, size: 40, color: AppColors.blue),
                    ),
                    const SizedBox(height: 22),
                    Text(
                      title,
                      style: theme.textTheme.titleLarge,
                      textAlign: TextAlign.center,
                    ),
                    const SizedBox(height: 8),
                    Text(
                      message,
                      textAlign: TextAlign.center,
                      style: theme.textTheme.bodyMedium
                          ?.copyWith(color: theme.colorScheme.onSurfaceVariant),
                    ),
                    const SizedBox(height: 24),
                    PrimaryButton(
                      onPressed: onPrimary,
                      label: primaryLabel,
                      icon: primaryIcon,
                      expand: true,
                    ),
                    if (secondaryLabel != null) ...[
                      const SizedBox(height: 4),
                      TextButton(
                        onPressed: onSecondary,
                        child: Text(secondaryLabel!),
                      ),
                    ],
                  ],
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }
}
