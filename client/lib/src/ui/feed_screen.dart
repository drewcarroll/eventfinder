import 'dart:async';

import 'package:flutter/material.dart';

import '../data/device_location_service.dart';
import '../data/event_api.dart';
import '../data/filter_service.dart';
import '../data/location_service.dart';
import '../models/event.dart';
import 'filter_sheet.dart';
import 'swipe_card_stack.dart';

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
      appBar: AppBar(
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            tooltip: 'New ideas',
            // Disabled until a location is set — there's nothing to fetch yet.
            onPressed: widget.locationService.hasLocation ? _refresh : null,
          ),
          IconButton(
            icon: const Icon(Icons.tune),
            tooltip: 'Filters',
            onPressed: _changeFilters,
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
  /// it. The trailing button captures the device's GPS position instead.
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
  /// ideas" button is the explicit trigger for the ideas pipeline. With no
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
                  hasLocation ? 'Ready to find ideas' : 'Set your location',
                  style: Theme.of(context).textTheme.titleMedium,
                ),
                const SizedBox(height: 8),
                Text(
                  hasLocation
                      ? 'Generate ideas near ${_locationLabel()} with your '
                          'current filters.'
                      : 'Search for a place in the bar above, then generate '
                          'ideas.',
                  textAlign: TextAlign.center,
                ),
                const SizedBox(height: 16),
                FilledButton.icon(
                  onPressed: _generateEvents,
                  icon: const Icon(Icons.auto_awesome),
                  label: const Text('Generate ideas'),
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
              'No ideas found near here.',
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

  /// Shown when the user has swiped through every idea in the deck. Offers to
  /// run back through the same ideas, or to generate a brand-new set.
  Widget _buildReachedEndCard() {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Icon(Icons.replay, size: 48),
            const SizedBox(height: 12),
            Text(
              'Reached the end!',
              style: Theme.of(context).textTheme.titleMedium,
            ),
            const SizedBox(height: 8),
            const Text(
              "You've seen every idea in this batch. Start again from the "
              'top, or refresh for a fresh set.',
              textAlign: TextAlign.center,
            ),
            const SizedBox(height: 16),
            FilledButton.icon(
              onPressed: _startOver,
              icon: const Icon(Icons.replay),
              label: const Text('Start again'),
            ),
            const SizedBox(height: 8),
            TextButton.icon(
              onPressed: _refresh,
              icon: const Icon(Icons.auto_awesome),
              label: const Text('Generate new ideas'),
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
      padding: const EdgeInsets.all(16),
      child: Column(
        children: [
          Align(
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
          const SizedBox(height: 12),
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
