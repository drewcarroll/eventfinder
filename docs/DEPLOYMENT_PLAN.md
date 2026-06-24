# Event Swiper — TestFlight Deployment Plan

Goal: get the app into **TestFlight** so external testers can use it, with the
backend always-on, kept **as close to $0 as possible**, and managed from as few
places as possible.

This doc is structured as task-sized chunks so it can be split onto the Chiron
board. Each task notes **who** does it (👤 = Drew / account-owner action,
🤖 = code/config work Claude can do) and its **dependencies**.

---

## TL;DR — the honest cost & schedule picture

| Item | Cost | Notes |
| --- | --- | --- |
| Apple Developer Program | **$99/year** | **Unavoidable for TestFlight.** This is the only required cost. |
| Backend (Cloud Run) | **$0** at beta scale | Generous always-free tier; scales to zero when idle. |
| Database (Neon free tier) | **$0** | Standard Postgres, no code changes. Autosuspends when idle. |
| **Total** | **~$99/year** | Effectively free except the Apple membership. |

**"All in one place":** Backend + auth live in your existing **Google Cloud /
Firebase project** (same console). The only outside dashboard is the database.
If you want the DB in the Google console too, use **Cloud SQL** instead of Neon
— but Cloud SQL has **no free tier (~$9/mo minimum)**. Recommendation below
keeps it free; switch to Cloud SQL later if the extra dashboard annoys you.

> ⏰ **Schedule risk for "EOD today/tomorrow":** the long pole is **Apple
> Developer Program enrollment**, not the code. Enrollment is sometimes instant
> but can take **24–48h** for identity verification. If you don't already have
> an active Apple Developer account, *today* is unlikely; *tomorrow* is
> plausible only if enrollment clears quickly. The backend can be live today.

---

## Recommended stack

- **Backend API:** Google **Cloud Run** (runs the existing Docker container, HTTPS by default — which satisfies iOS App Transport Security).
- **Database:** **Neon** free-tier Postgres (or Cloud SQL if you prefer one console and accept ~$9/mo).
- **Auth:** **Firebase Auth** — already in place, no change.
- **No backend rewrite.** Current FastAPI + Postgres code ships as-is.

---

## Phase A — Deploy the backend (can finish today)

**A1. 🤖 Make the container Cloud Run-ready**
- Update `Dockerfile` CMD to bind Cloud Run's injected `$PORT` (currently hardcoded to 8000).
- Add a startup migration step (run `alembic upgrade head` on deploy) since the app does **not** migrate on startup.
- Acceptance: `docker build` + `docker run -e PORT=8080` serves `/health`.

**A2. 👤 Provision the database (Neon free tier)**
- Create a Neon project, copy the connection string, convert to async form: `postgresql+asyncpg://…`.
- Dependency: none. Output feeds A4.

**A3. 👤 Enable required Google Cloud APIs / install gcloud**
- In the **existing Firebase project**, enable Cloud Run + Artifact Registry. Install + `gcloud auth login`.
- (Drew runs the auth login; Claude can supply exact commands.)

**A4. 🤖+👤 Deploy to Cloud Run**
- Build & push the image, deploy the service, set env vars/secrets: `DATABASE_URL` (from A2), `ANTHROPIC_API_KEY`, `TAVILY_API_KEY`, Firebase service-account, `CORS_ORIGINS`.
- Store secrets in Secret Manager (not plain env).
- Acceptance: `curl https://<cloud-run-url>/health` returns 200.
- Dependencies: A1, A2, A3.

**A5. 🤖 Smoke-test the deployed API**
- Verify `/health`, and an authed call (`/users/sync`) with a real Firebase token.
- Dependency: A4.

---

## Phase B — iOS app prep for TestFlight

**B1. 👤 Enroll in / confirm Apple Developer Program** ⏰ *(start FIRST — long pole)*
- $99/year. Needed before any TestFlight upload. Dependency for B4–B6.

**B2. 🤖 Add the Google Sign-In URL scheme to iOS**
- `ios/Runner/Info.plist` is missing the `CFBundleURLSchemes` / `REVERSED_CLIENT_ID` entry → Google sign-in won't return to the app on iOS. Add it from `GoogleService-Info.plist`.
- Acceptance: Google Sign-In completes on an iOS simulator/device.
- Dependency: none.

**B3. 👤 Create the app record in App Store Connect**
- New app using bundle id **`com.chiron.eventSwiper`** (already set in the Xcode project).
- In Firebase, confirm an **iOS app** exists for that bundle id and `GoogleService-Info.plist` matches.
- Dependency: B1.

**B4. 🤖+👤 Configure signing & build the release IPA**
- Set the team in Xcode (automatic signing), bump build number, `flutter build ipa --dart-define=API_BASE_URL=https://<cloud-run-url>` (the prod URL from A4).
- Dependencies: A4 (URL), B1, B3.

**B5. 👤 Upload to TestFlight**
- Upload via Xcode Organizer / Transporter; complete export-compliance questionnaire.
- Dependency: B4.

**B6. 👤 Add testers & ship**
- Internal testers (instant) or external testers (requires a short Beta App Review).
- Dependency: B5.

---

## Phase C — Verify end-to-end

**C1. 🤖+👤 Full flow on a TestFlight build**
- Install from TestFlight → Google Sign-In → feed loads from Cloud Run → record a swipe → session persists in Neon.
- Dependencies: A5, B6.

---

## Suggested ordering for the deadline

1. **Now:** B1 (Apple enrollment — clock starts) ‖ A1, A2 in parallel.
2. **Then:** A3 → A4 → A5 (backend live).
3. **Then:** B2, B3 → B4 → B5 → B6.
4. **Finally:** C1.

Backend (Phase A) realistically completes **today**. TestFlight (Phase B/C)
gates on Apple enrollment (B1) and, for external testers, Beta App Review.

---

## Open decisions for Drew

- **DB:** Neon free tier (recommended, $0) vs Cloud SQL (one console, ~$9/mo)?
- **Testers:** internal only (instant, up to 100, must be on your team) vs external (needs Beta App Review, up to 10k)?
