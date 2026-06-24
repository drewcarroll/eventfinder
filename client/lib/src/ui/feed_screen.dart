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

  /// Capture the device's GPS position and load the feed around it. Invoked
  /// only by an explicit user action (the searchbar's "use my location"
  /// button) — never on launch. Requesting the position triggers the OS
  /// permission prompt on first use. When permission is denied or location
  /// services are off, surface a message and leave the searchbar for manual
  /// entry.
  Future<void> _initLocationAndLoad() async {
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
    location.clearOverride();
    _locationController.text = _locationLabel();
    await _load();
  }

  /// Resolve the text typed into the searchbar to coordinates on the backend,
  /// adopt it as the session's search location, and load the feed around it.
  Future<void> _searchLocation(String query) async {
    final trimmed = query.trim();
    if (trimmed.isEmpty) return;
    try {
      final resolved = await widget.api.resolveLocation(trimmed);
      widget.locationService.setManualOverride(resolved);
      _locationController.text = resolved.displayName;
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Searching near ${resolved.displayName}')),
      );
      await _load();
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('$e')),
      );
    }
  }

  Future<void> _load() async {
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
        _loading = false;
      });
    } catch (e) {
      setState(() {
        _error = '$e';
        _loading = false;
      });
    }
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
            onPressed: _initLocationAndLoad,
          ),
          border: OutlineInputBorder(
            borderRadius: BorderRadius.circular(28),
          ),
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
    // The landing state: no location set yet (the app no longer auto-captures
    // one on launch). Show a placeholder card in the swipe area pointing the
    // user at the searchbar above, rather than fetching anything on open.
    if (!widget.locationService.hasLocation) {
      return Center(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Card(
            child: Padding(
              padding: const EdgeInsets.all(32),
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  const Icon(Icons.location_searching, size: 48),
                  const SizedBox(height: 16),
                  Text(
                    'Set your location',
                    style: Theme.of(context).textTheme.titleMedium,
                  ),
                  const SizedBox(height: 8),
                  const Text(
                    'Search for a place in the bar above to find events '
                    'near you.',
                    textAlign: TextAlign.center,
                  ),
                ],
              ),
            ),
          ),
        ),
      );
    }
    // Reached only when the very first load came back empty (a session that
    // runs out of cards routes to the results view instead). Show a friendly
    // nudge to widen the search rather than a dead end.
    if (_events.isEmpty) {
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
            ],
          ),
        ),
      );
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
