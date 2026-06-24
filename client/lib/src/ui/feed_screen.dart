import 'package:flutter/material.dart';

import '../data/auth_service.dart';
import '../data/device_location_service.dart';
import '../data/event_api.dart';
import '../data/filter_service.dart';
import '../data/location_service.dart';
import '../models/event.dart';
import '../models/swipe_session.dart';
import 'filter_sheet.dart';
import 'history_screen.dart';
import 'results_screen.dart';
import 'swipe_card_stack.dart';

/// The interest the feed searches for. Combined with the session location to
/// form the backend query, e.g. "live music near Austin, Texas".
const String _interest = 'live music';

class FeedScreen extends StatefulWidget {
  const FeedScreen({
    super.key,
    required this.api,
    required this.authService,
    required this.locationService,
    required this.filterService,
  });

  final EventApi api;
  final AuthService authService;
  final LocationService locationService;
  final FilterService filterService;

  @override
  State<FeedScreen> createState() => _FeedScreenState();
}

class _FeedScreenState extends State<FeedScreen> {
  List<Event> _events = [];
  // Every swipe decision (yes/no) made this run, accumulated locally and sent
  // to the backend in one shot when the session ends.
  SwipeSession _session = SwipeSession();
  // Set once the session is saved (END SESSION tapped or the feed swiped
  // empty): the results view replaces the card stack. Distinct from an
  // empty-from-start feed, which never starts a session.
  bool _sessionEnded = false;
  // The compiled yes list shown on the results screen. Filled from the
  // backend's response when the session is saved.
  List<Event> _liked = [];
  // True while the session save is in flight, to disable END SESSION and show
  // progress.
  bool _saving = false;
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
  /// and adopt it as the session's search location. Does not fetch the feed —
  /// running the pipeline is an explicit action ("Generate events" / refresh),
  /// so this just updates the placeholder to invite generation.
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
            'Location set to ${resolved.displayName}. Tap Generate events.',
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
  /// the loaded feed reuses the cached events instead of re-running the ideas
  /// pipeline — avoiding a needless, credit-costing fetch. Explicit refresh
  /// passes [force] to always re-run.
  Future<void> _load({bool force = false}) async {
    // Can't search without somewhere to search around. The "Generate events"
    // button prompts for a location; this guards every other caller too.
    if (!widget.locationService.hasLocation) return;
    final signature = _feedSignature();
    if (!force && signature == _loadedSignature && _events.isNotEmpty) {
      // Same location + filters and we still hold a feed: just start a fresh
      // run over the cached events, no network/pipeline work.
      setState(() {
        _error = null;
        _session = SwipeSession();
        _sessionEnded = false;
        _liked = [];
        _saving = false;
      });
      return;
    }
    setState(() {
      _loading = true;
      _error = null;
      // Each load starts a fresh run: clear prior decisions and re-enter the
      // swipe view.
      _session = SwipeSession();
      _sessionEnded = false;
      _liked = [];
      _saving = false;
    });
    try {
      // Provision/refresh the user record on the backend before fetching.
      await widget.api.syncUser();
      // Search around the session location: the manual override if set,
      // otherwise "near me" (the device's GPS position).
      final query = '$_interest near ${widget.locationService.searchLabel}';
      // Apply the session filters: search radius and a time window resolved
      // from the chosen preset (tonight / this weekend / custom).
      final filters = widget.filterService.filters;
      final window = filters.resolveWindow(DateTime.now());
      final events = await widget.api.fetchFeed(
        query,
        radiusKm: filters.maxDistanceKm,
        startsAfter: window.start,
        startsBefore: window.end,
      );
      setState(() {
        _events = events;
        // Remember what these events were fetched for, so an unchanged reload
        // can reuse them.
        _loadedSignature = signature;
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
  /// filters. Guarded against credit waste by a [_refreshCooldown] debounce so
  /// rapid repeated taps don't fire repeated pipeline runs.
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

  Future<void> _signOut() async {
    try {
      // On success the auth-state stream emits null and routes back to
      // the sign-in screen automatically.
      await widget.authService.signOut();
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Sign-out failed: $e')),
        );
      }
    }
  }

  void _swipe(Event event, String direction) {
    setState(() {
      // Right/like is a yes, left/pass is a no. Record every decision in the
      // run's session state; nothing is persisted until the session ends.
      _session.record(
        event,
        direction == 'like' ? SwipeChoice.yes : SwipeChoice.no,
      );
      _events = _events.where((e) => e.id != event.id).toList();
    });
    // Running out of cards ends the session — save it and show the results.
    if (_events.isEmpty) _endSession();
  }

  /// Save the completed run to the backend and show the compiled results.
  ///
  /// The backend returns the canonical yes list (the cards swiped right). If
  /// the save can't be reached, fall back to the locally tracked likes so the
  /// user still sees their picks, and surface the error.
  Future<void> _endSession() async {
    if (_saving || _sessionEnded) return;
    setState(() => _saving = true);

    final filters = widget.filterService.filters;
    List<Event> liked;
    try {
      liked = await widget.api.saveSession(
        decisions: _session.decisions,
        location: widget.locationService.searchLabel,
        distance: filters.maxDistanceKm,
        timeRange: filters.timeRangeSummary,
      );
    } catch (e) {
      liked = _session.yes;
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text("Couldn't save your session: $e"),
          ),
        );
      }
    }

    if (!mounted) return;
    setState(() {
      _liked = liked;
      _sessionEnded = true;
      _saving = false;
    });
  }

  /// Leave the results view and start a fresh search for a new session.
  Future<void> _startNewSearch() async {
    await _load();
  }

  /// Open the history of past sessions, each tappable to view its yes list.
  void _openHistory() {
    Navigator.of(context).push(
      MaterialPageRoute<void>(
        builder: (_) => HistoryScreen(api: widget.api),
      ),
    );
  }

  /// Open the filter sheet and, if the user applies changes, store them on
  /// the session and reload the feed with the new distance/time window.
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
    // The session has ended (saved): show the compiled results.
    if (_sessionEnded) {
      return ResultsScreen(
        liked: _liked,
        onNewSearch: _startNewSearch,
        onSignOut: _signOut,
      );
    }
    return Scaffold(
      appBar: AppBar(
        title: const Text('Event Swiper'),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            tooltip: 'Refresh',
            // Disabled until a location is set — there's nothing to fetch yet.
            onPressed:
                widget.locationService.hasLocation ? _refresh : null,
          ),
          IconButton(
            icon: const Icon(Icons.tune),
            tooltip: 'Filters',
            onPressed: _changeFilters,
          ),
          IconButton(
            icon: const Icon(Icons.history),
            tooltip: 'History',
            onPressed: _openHistory,
          ),
          IconButton(
            icon: const Icon(Icons.logout),
            tooltip: 'Sign out',
            onPressed: _signOut,
          ),
        ],
      ),
      body: Column(
        children: [
          _buildLocationBar(),
          Expanded(child: _buildBody()),
        ],
      ),
    );
  }

  /// The top location bar: a searchbar that doubles as a "current location"
  /// shower. Empty by default with no auto-prompt; submitting a place resolves
  /// it and loads the feed. The trailing button captures the device's GPS
  /// position instead.
  Widget _buildLocationBar() {
    return Padding(
      padding: const EdgeInsets.fromLTRB(16, 12, 16, 4),
      child: TextField(
        controller: _locationController,
        textInputAction: TextInputAction.search,
        onSubmitted: _searchLocation,
        decoration: InputDecoration(
          isDense: true,
          prefixIcon: const Icon(Icons.search),
          suffixIcon: IconButton(
            icon: const Icon(Icons.my_location),
            tooltip: 'Use my location',
            onPressed: _useDeviceLocation,
          ),
          border: OutlineInputBorder(
            borderRadius: BorderRadius.circular(28),
          ),
        ),
      ),
    );
  }

  /// The blank placeholder shown when there's no feed yet. Its "Generate
  /// events" button is the explicit trigger for the ideas pipeline. With no
  /// location set, the copy points at the searchbar and tapping prompts the
  /// user to choose one first.
  Widget _buildGeneratePlaceholder() {
    final hasLocation = widget.locationService.hasLocation;
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: Card(
          child: Padding(
            padding: const EdgeInsets.all(32),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                Icon(
                  hasLocation ? Icons.auto_awesome : Icons.location_searching,
                  size: 48,
                ),
                const SizedBox(height: 16),
                Text(
                  hasLocation ? 'Ready to find events' : 'Set your location',
                  style: Theme.of(context).textTheme.titleMedium,
                ),
                const SizedBox(height: 8),
                Text(
                  hasLocation
                      ? 'Generate events near ${_locationLabel()} with your '
                          'current filters.'
                      : 'Search for a place in the bar above, then generate '
                          'events.',
                  textAlign: TextAlign.center,
                ),
                const SizedBox(height: 16),
                FilledButton.icon(
                  onPressed: _generateEvents,
                  icon: const Icon(Icons.auto_awesome),
                  label: const Text('Generate events'),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }

  /// Shown after a generation that genuinely came back empty: nudge the user
  /// to widen the search, with a one-tap way to run it again.
  Widget _buildNoEventsCard() {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Icon(Icons.event_busy, size: 48),
            const SizedBox(height: 12),
            Text(
              'No events found near here.',
              style: Theme.of(context).textTheme.titleMedium,
            ),
            const SizedBox(height: 8),
            const Text(
              'Try widening your distance or time range, '
              'or searching a different spot.',
              textAlign: TextAlign.center,
            ),
            const SizedBox(height: 16),
            FilledButton.icon(
              onPressed: _changeFilters,
              icon: const Icon(Icons.tune),
              label: const Text('Adjust filters'),
            ),
            const SizedBox(height: 8),
            TextButton.icon(
              onPressed: _generateEvents,
              icon: const Icon(Icons.refresh),
              label: const Text('Generate again'),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildBody() {
    if (_loading) {
      return const Center(child: CircularProgressIndicator());
    }
    if (_error != null) {
      return Center(child: Text('Error: $_error'));
    }
    // No feed yet. The pipeline never runs on its own — show the blank
    // placeholder card whose "Generate events" button is the explicit trigger.
    if (_events.isEmpty) {
      // Distinguish "haven't generated for these inputs yet" from "generated
      // and the pipeline genuinely returned nothing": only the latter shows
      // the widen-your-search nudge, so we don't cry "no events" before the
      // user has asked for any.
      final generatedAndEmpty = widget.locationService.hasLocation &&
          _loadedSignature == _feedSignature();
      return generatedAndEmpty
          ? _buildNoEventsCard()
          : _buildGeneratePlaceholder();
    }

    final filters = widget.filterService.filters;
    return Padding(
      padding: const EdgeInsets.all(16),
      child: Column(
        children: [
          Row(
            children: [
              Expanded(
                child: Align(
                  alignment: Alignment.centerLeft,
                  child: ActionChip(
                    avatar: const Icon(Icons.tune, size: 18),
                    label: Text(
                      '${filters.timeRangeSummary} · '
                      '${filters.maxDistanceKm.round()} km',
                    ),
                    onPressed: _changeFilters,
                  ),
                ),
              ),
              const SizedBox(width: 8),
              TextButton.icon(
                onPressed: _saving ? null : _endSession,
                icon: _saving
                    ? const SizedBox(
                        width: 16,
                        height: 16,
                        child: CircularProgressIndicator(strokeWidth: 2),
                      )
                    : const Icon(Icons.flag_outlined),
                label: const Text('End session'),
              ),
            ],
          ),
          const SizedBox(height: 12),
          Expanded(
            child: SwipeCardStack(
              events: _events,
              onSwipe: _swipe,
            ),
          ),
        ],
      ),
    );
  }
}
