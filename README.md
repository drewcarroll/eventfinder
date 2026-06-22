# Event Swiper

Swipe to discover events you'll love. Event Swiper presents a Tinder-style
feed of upcoming events; users swipe **like / pass / super-like**, and the
app learns their tastes to rank future events. Event candidates are
discovered live from the web via **Tavily**, enriched with personalized copy
by **Anthropic Claude**, persisted in **PostgreSQL**, and served by a
**FastAPI** backend. The mobile client is built with **Flutter**, with
authentication handled by **Firebase Auth + Google Sign-In**.

## Tech Stack

| Concern              | Technology                          |
| -------------------- | ----------------------------------- |
| Mobile client        | Flutter (Dart)                      |
| Authentication       | Firebase Auth + Google Sign-In      |
| Backend API          | Python · FastAPI                    |
| Database             | PostgreSQL (async SQLAlchemy)       |
| Event discovery      | Tavily Search API                   |
| AI enrichment        | Anthropic Claude                    |

---

## Architecture: Clean Architecture

The backend (`src/`) is organized into four concentric layers. **Dependencies
only ever point inward.** This keeps business rules independent of frameworks,
databases, and external APIs — and makes them trivially testable.

```
interfaces ─▶ application ─▶ domain
infrastructure ─▶ application ─▶ domain
domain imports NOTHING from outside itself
```

### `src/domain/` — the core
Pure business rules with zero outside dependencies.
- **Entities**: `Event`, `Swipe`, `User` — protect their own invariants.
- **Value Objects**: `SwipeDirection`, `GeoLocation` — immutable, validated.
- **Domain Services**: `RecommendationScorer` — ranking logic that spans entities.
- **Repository interfaces**: `EventRepository`, `SwipeRepository`, `UserRepository`
  describe *what* persistence is needed, never *how*.

### `src/application/` — use cases
Orchestrates the domain to fulfill application goals. Knows *what* to do, not *how*.
- **Use Cases**: `GetEventFeed`, `RecordSwipe`, `SyncUser` — each a single
  class with an `execute(dto)` method, receiving dependencies via constructor
  injection.
- **DTOs**: input/output contracts (`GetEventFeedInput`, `RecordSwipeOutput`, …).
- **Ports**: abstractions the infrastructure must satisfy
  (`EventDiscoveryPort`, `EventEnricherPort`, `ClockPort`, `IdGeneratorPort`).
- **Mappers**: domain ↔ DTO translation.

### `src/infrastructure/` — implementations (all I/O)
Implements the interfaces defined inward. The only layer that touches the
outside world.
- `persistence/` — async SQLAlchemy models + repository implementations
  (`SqlEventRepository`, `SqlSwipeRepository`, `SqlUserRepository`).
- `discovery/` — `TavilyEventDiscovery` implements `EventDiscoveryPort`.
- `llm/` — `AnthropicEventEnricher` implements `EventEnricherPort`.
- `auth/` — `FirebaseAuthVerifier` verifies Google Sign-In ID tokens.
- `config/` — environment settings (the only place that reads env vars).
- `system/` — `SystemClock`, `UuidIdGenerator`.

### `src/interfaces/` — entry points (adapters)
Thin adapters that translate HTTP ⇄ use cases. No business logic.
- `http/app.py` — FastAPI application factory.
- `http/controllers/` — `event_controller`, `user_controller`, `health_controller`.
- `http/schemas/` — Pydantic request/response models (shape validation only).
- `http/dependencies.py` — request-scoped use-case wiring helpers.

### Composition root — `main.py`
Sits **outside** the layers. It is the single place allowed to know about
every layer at once: it instantiates concrete infrastructure and injects it
into the application use cases, then hands a factory to the interfaces layer.
This preserves the dependency rule everywhere else.

> The layer rules are codified in `architecture.json` and each layer's
> `CLAUDE.md`. Please keep new code in the correct layer.

---

## Backend Setup

### Prerequisites
- Python 3.11+
- PostgreSQL 16 (or use the provided `docker-compose.yml`)
- API keys: Tavily, Anthropic, and a Firebase service account

### 1. Configure environment
```bash
cp .env.example .env
# Fill in DATABASE_URL, ANTHROPIC_API_KEY, TAVILY_API_KEY, FIREBASE_* values
```

### 2. Install dependencies
```bash
make install          # pip install -r requirements-dev.txt
```

### 3. Start PostgreSQL
```bash
make db-up            # docker compose up -d db
```

### 4. Run the API
```bash
make run              # uvicorn main:app --reload --port 8000
```
Visit http://localhost:8000/docs for interactive API docs.

### Run everything with Docker
```bash
docker compose up --build
```

### Tests, linting, formatting
```bash
make test             # pytest (domain + use-case unit tests, no DB needed)
make lint             # ruff + mypy
make format           # black + ruff --fix
```

---

## Flutter Client Setup

The mobile app lives in `client/`.

### 1. Configure Firebase
```bash
cd client
flutter pub get
# Generate firebase_options.dart and platform config:
flutterfire configure
```
Enable **Google** as a sign-in provider in the Firebase console, and place
`google-services.json` (Android) / `GoogleService-Info.plist` (iOS) per the
FlutterFire docs. (These files are git-ignored.)

### 2. Point the app at the backend
```bash
flutter run --dart-define=API_BASE_URL=http://10.0.2.2:8000
```
> `10.0.2.2` is the Android emulator's alias for your host machine. Use
> `http://localhost:8000` for iOS simulator / desktop.

---

## API Endpoints

| Method | Path             | Description                                  |
| ------ | ---------------- | -------------------------------------------- |
| GET    | `/health`        | Liveness check                               |
| POST   | `/users/sync`    | Verify the ID token and upsert the user      |
| GET    | `/api/v1/feed`   | Personalized, ranked event feed              |
| POST   | `/api/v1/swipes` | Record a like / pass / super-like decision   |

Every endpoint except `/health` requires an
`Authorization: Bearer <firebase-id-token>` header. The backend verifies the
token via the Firebase Admin SDK. Clients call `POST /users/sync` on login:
it inserts the user on first sight (`201`) and updates their profile on
return visits (`200`). The feed and swipe endpoints require an existing user
record, so sync runs first.

---

## Request Flow Example (record a swipe)

```
Flutter (Google Sign-In → ID token)
   │  POST /api/v1/swipes  Authorization: Bearer <token>
   ▼
interfaces/http/controllers/event_controller.record_swipe   (validate input)
   │  RecordSwipeInput(dto)
   ▼
application/use_cases/record_swipe.RecordSwipe.execute       (orchestrate)
   │  uses SwipeRepository / EventRepository (domain interfaces)
   │  uses Swipe / SwipeDirection (domain rules)
   ▼
infrastructure/persistence/SqlSwipeRepository                (PostgreSQL I/O)
```

The use case never knows it's talking to PostgreSQL, Tavily, or Claude — only
to abstractions. Swap any implementation without touching business logic.
