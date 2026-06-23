# Unified Card Schema

Every item in the swipe feed is a **card**, regardless of where it came
from. Two sources feed the pipeline:

- **Web-sourced events** — discovered live (Tavily), then normalized.
- **AI-generated activities** — suggested by the LLM to complement the
  events.

Both are normalized into the *same* shape so the rest of the pipeline —
merging, dedup, ranking, time/distance filtering, and serialization to the
client — never has to care which source a card came from. This document is
the contract for that shape.

## Canonical JSON

This is what the client receives for a single card (`GET /api/v1/feed`
returns `{ "events": [ <card>, ... ] }`):

```json
{
  "id": "evt_8f3c1a2b",
  "card_type": "event",
  "title": "Live Jazz at The Blue Room",
  "description": "An intimate evening of standards and improv.",
  "category": "music",
  "latitude": 30.2672,
  "longitude": -97.7431,
  "distance_km": 3.4,
  "source_url": "https://example.com/events/blue-room-jazz",
  "image_url": "https://example.com/img/blue-room.jpg",
  "starts_at": "2030-06-15T20:00:00",
  "availability_times": [
    { "starts_at": "2030-06-15T18:00:00", "ends_at": "2030-06-15T22:00:00" },
    { "starts_at": "2030-06-16T18:00:00", "ends_at": "2030-06-16T22:00:00" }
  ]
}
```

## Fields

| Field                | Type                | Required | Notes                                                                                  |
| -------------------- | ------------------- | -------- | -------------------------------------------------------------------------------------- |
| `id`                 | string              | yes      | Stable unique identifier for the card.                                                 |
| `card_type`          | `"event"` \| `"activity"` | yes | The acceptance-criteria **type**. Web-sourced → `event`; AI-generated → `activity`.    |
| `title`              | string              | yes      | Non-empty, trimmed.                                                                    |
| `description`        | string              | yes      | May be empty (`""`).                                                                    |
| `category`           | string              | yes      | Free-form tag, e.g. `music`, `art`, `food`. Defaults to `general`.                     |
| `latitude`           | float \| null       | no       | Part of **lat/lng**. `null` when location is unknown (common for activities).          |
| `longitude`          | float \| null       | no       | Part of **lat/lng**.                                                                   |
| `distance_km`        | float \| null       | no       | The **distance** field, in kilometers from the user's search origin. Derived per request — see below. |
| `source_url`         | string              | yes      | Origin URL for events; may be empty (`""`) for AI-generated activities.                |
| `image_url`          | string \| null      | no       | Optional thumbnail.                                                                    |
| `starts_at`          | ISO-8601 datetime   | yes      | Primary occurrence time. Naive UTC (no offset suffix).                                 |
| `availability_times` | array of windows    | yes      | Possibly empty. Structured for time-range filtering — see below.                       |

### `availability_times` (time-range filtering)

`availability_times` is a JSON array of **windows**, each an object with two
naive-UTC ISO-8601 datetimes:

```json
{ "starts_at": "2030-06-15T18:00:00", "ends_at": "2030-06-15T22:00:00" }
```

Invariant: `ends_at >= starts_at` (enforced by the
`AvailabilityWindow` value object).

A card can carry **multiple** windows — e.g. a class that runs on several
evenings. This is what makes the feed filterable by time range: a card is
"available within `[range_start, range_end]`" when **any** of its windows
**overlaps** that range. The overlap rule lives in
`AvailabilityWindow.overlaps(start, end)`:

```
window overlaps [start, end]  ⟺  window.starts_at <= end AND window.ends_at >= start
```

> `starts_at` (the single primary time) and `availability_times` (the set
> of bookable windows) are complementary. The current feed time filter
> narrows on `starts_at` (`Event.starts_within`); `availability_times` is
> the structured basis for richer overlap-based filtering across all of a
> card's windows. All times are **naive UTC** — callers passing tz-aware
> bounds are normalized to naive UTC before comparison.

### `distance_km` (per-request, not stored)

Distance is **relative to the user's search origin**, so it is *not* an
intrinsic property of a card and is *not* persisted. It is computed when a
card is mapped for a response, using the great-circle (haversine) distance
`GeoLocation.distance_km_to`. It is `null` when either the search origin or
the card's own location is unknown.

## Where the schema lives (per layer)

The same card is represented once per layer, each translation staying
within the Clean Architecture dependency rule:

| Layer            | Representation                                              | File                                                      |
| ---------------- | ---------------------------------------------------------- | --------------------------------------------------------- |
| `domain`         | `Event` entity + `AvailabilityWindow` / `GeoLocation` VOs  | `src/domain/entities/event.py`, `src/domain/value_objects/` |
| `application`    | `EventDTO` + `AvailabilityWindowDTO`                       | `src/application/dtos/event_dtos.py`                      |
| `application`    | `EventMapper.to_dto(event, origin=None)` (entity → DTO; computes `distance_km`) | `src/application/mappers/event_mapper.py`                 |
| `interfaces`     | `EventResponse` + `AvailabilityWindowResponse` (Pydantic)  | `src/interfaces/http/schemas/event_schemas.py`            |
| `infrastructure` | `EventModel` row; `availability_times` as a JSON-encoded `TEXT` column | `src/infrastructure/persistence/models.py`                |

Notes on the persistence representation:

- `latitude` / `longitude` are stored as nullable `Float` columns; the
  domain reassembles them into a `GeoLocation`.
- `availability_times` is stored as a JSON-encoded array of
  `{starts_at, ends_at}` ISO-8601 strings in a single `TEXT` column.
- `distance_km` is **not** a column — it is derived per request.

## Pipeline contract

Anyone producing cards (the normalizer turning web results into events, and
the generator producing activities) **must** emit this shape:

1. Set `card_type` correctly (`event` vs `activity`).
2. Provide a non-empty `title` and a stable `id`.
3. Populate `availability_times` whenever times are known, so the feed can
   be filtered by time range.
4. Leave `latitude` / `longitude` `null` rather than guessing when location
   is unknown; never set `distance_km` at the source (it is derived).

Producers that honor this contract can be merged and deduplicated by
`CardMerger` (which collapses cards sharing an identity key and folds their
`availability_times` together) and ranked without any source-specific code.
