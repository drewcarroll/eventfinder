#!/usr/bin/env bash
#
# One command to run the whole Event Swiper stack against an emulator:
#   Postgres  ->  migrations  ->  FastAPI backend  ->  Flutter app on the emulator
#
# Usage:
#   make emulator                       # Android emulator (default)
#   make emulator EMULATOR_ID=apple_ios_simulator API_HOST=localhost
#
# Env overrides:
#   EMULATOR_ID  flutter emulator id (see `flutter emulators`)
#   API_PORT     backend port                       (default 8000)
#   API_HOST     host the app reaches the API on    (default 10.0.2.2 — the
#                Android emulator's alias for the host; use localhost for iOS)
#
# The backend (and Postgres, if this script started it) is shut down when you
# quit Flutter with `q` or Ctrl-C.

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

EMULATOR_ID="${EMULATOR_ID:-Pixel_3a_API_34_extension_level_7_arm64-v8a}"
API_PORT="${API_PORT:-8000}"
API_HOST="${API_HOST:-10.0.2.2}"
API_BASE_URL="http://${API_HOST}:${API_PORT}"

# Prefer the project venv's tools if present, so this works without an
# activated virtualenv.
BIN=""
[[ -x ".venv/bin/uvicorn" ]] && BIN=".venv/bin/"

BACKEND_PID=""
STARTED_DB=0
cleanup() {
  if [[ -n "$BACKEND_PID" ]] && kill -0 "$BACKEND_PID" 2>/dev/null; then
    echo "==> Stopping backend (pid $BACKEND_PID)"
    kill "$BACKEND_PID" 2>/dev/null || true
    wait "$BACKEND_PID" 2>/dev/null || true
  fi
}
trap cleanup EXIT INT TERM

# --- 1. PostgreSQL -----------------------------------------------------------
echo "==> Starting PostgreSQL (docker compose up -d db)"
docker compose up -d db

echo "==> Waiting for PostgreSQL to accept connections"
for _ in $(seq 1 30); do
  if docker compose exec -T db pg_isready -U postgres >/dev/null 2>&1; then
    echo "    PostgreSQL is ready ✅"
    break
  fi
  sleep 1
done

# --- 2. Migrations -----------------------------------------------------------
echo "==> Applying database migrations (alembic upgrade head)"
"${BIN}alembic" upgrade head

# --- 3. Backend --------------------------------------------------------------
if curl -sf "http://localhost:${API_PORT}/health" >/dev/null 2>&1; then
  echo "==> Backend already running on port ${API_PORT}; reusing it"
else
  echo "==> Starting FastAPI backend on port ${API_PORT}"
  "${BIN}uvicorn" main:app --reload --port "${API_PORT}" &
  BACKEND_PID=$!

  echo "==> Waiting for backend health check"
  for _ in $(seq 1 30); do
    if curl -sf "http://localhost:${API_PORT}/health" >/dev/null 2>&1; then
      echo "    Backend is healthy ✅  ($(curl -sf "http://localhost:${API_PORT}/health"))"
      break
    fi
    if ! kill -0 "$BACKEND_PID" 2>/dev/null; then
      echo "!! Backend exited before becoming healthy — see output above." >&2
      exit 1
    fi
    sleep 1
  done
fi

# --- 4. Emulator + Flutter ---------------------------------------------------
# Which platform are we targeting? Derived from EMULATOR_ID so we can pick the
# right booted device and never fall back to web or a physical phone.
PLATFORM="android"
[[ "$EMULATOR_ID" == apple_ios* ]] && PLATFORM="ios"

# Print the id of a booted emulator/simulator for $PLATFORM (empty if none).
# Only matches devices flutter reports as emulators, so a plugged-in physical
# iPhone is never auto-selected.
find_device_id() {
  flutter devices --machine 2>/dev/null | "${BIN}python" -c '
import json, sys
plat = sys.argv[1]
try:
    devices = json.load(sys.stdin)
except Exception:
    sys.exit(0)
for d in devices:
    if d.get("emulator") and str(d.get("targetPlatform", "")).startswith(plat):
        print(d["id"])
        break
' "$PLATFORM"
}

echo "==> Launching '${EMULATOR_ID}' (skipped if already running)"
flutter emulators --launch "${EMULATOR_ID}" >/dev/null 2>&1 || \
  echo "    (could not auto-launch; will wait for an already-running device)"

echo "==> Waiting for a booted ${PLATFORM} emulator/simulator"
DEVICE_ID="${DEVICE_ID:-}"
if [[ -z "$DEVICE_ID" ]]; then
  for _ in $(seq 1 60); do
    DEVICE_ID="$(find_device_id)"
    [[ -n "$DEVICE_ID" ]] && break
    sleep 2
  done
fi
if [[ -z "$DEVICE_ID" ]]; then
  echo "!! No booted ${PLATFORM} emulator found. Start one with:" >&2
  echo "     flutter emulators --launch ${EMULATOR_ID}" >&2
  echo "   or pass a device explicitly: make emulator DEVICE_ID=<id>" >&2
  exit 1
fi
echo "    Using device ${DEVICE_ID} ✅"

cd client
echo "==> flutter pub get"
flutter pub get

echo "==> Running app on ${DEVICE_ID}  (API_BASE_URL=${API_BASE_URL})"
echo "    Press 'r' to hot reload, 'R' to hot restart, 'q' to quit (stops the backend)."
flutter run -d "${DEVICE_ID}" --dart-define=API_BASE_URL="${API_BASE_URL}"
