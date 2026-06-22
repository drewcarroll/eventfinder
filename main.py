"""Composition root for the Event Swiper API.

This module sits OUTSIDE the clean architecture layers. It is the only
place permitted to know about every layer at once: it wires concrete
infrastructure implementations to the ports/repositories the application
layer depends on, then hands a use-case factory to the interfaces layer.

Run with:
    uvicorn main:app --reload
"""
from __future__ import annotations

import httpx

from src.application.use_cases.get_event_feed import GetEventFeed
from src.application.use_cases.record_swipe import RecordSwipe
from src.application.use_cases.sync_user import SyncUser
from src.domain.services.recommendation_scorer import RecommendationScorer
from src.infrastructure.auth.firebase_auth import FirebaseAuthVerifier
from src.infrastructure.config.settings import get_settings
from src.infrastructure.discovery.tavily_event_discovery import (
    TavilyEventDiscovery,
)
from src.infrastructure.llm.anthropic_event_enricher import (
    AnthropicEventEnricher,
)
from src.infrastructure.persistence.database import SessionFactory, init_db
from src.infrastructure.persistence.sql_event_repository import (
    SqlEventRepository,
)
from src.infrastructure.persistence.sql_swipe_repository import (
    SqlSwipeRepository,
)
from src.infrastructure.persistence.sql_user_repository import (
    SqlUserRepository,
)
from src.infrastructure.system.system_clock import SystemClock
from src.infrastructure.system.uuid_id_generator import UuidIdGenerator
from src.interfaces.http.app import create_app
from src.interfaces.http.dependencies import RequestScope

settings = get_settings()

# Singletons that are safe to share across requests.
_http_client = httpx.AsyncClient(timeout=20.0)
_auth = FirebaseAuthVerifier(settings)
_discovery = TavilyEventDiscovery(settings.tavily_api_key, _http_client)
_enricher = AnthropicEventEnricher(
    settings.anthropic_api_key, settings.anthropic_model
)
_scorer = RecommendationScorer()
_clock = SystemClock()
_ids = UuidIdGenerator()


async def use_case_factory(token: str) -> RequestScope:
    """Authenticate, open a DB session, and build request-scoped use cases."""
    try:
        identity = _auth.verify(token)
    except Exception as exc:  # noqa: BLE001 - translate to auth failure
        raise PermissionError("Invalid authentication token") from exc

    session = SessionFactory()

    users = SqlUserRepository(session)
    events = SqlEventRepository(session)
    swipes = SqlSwipeRepository(session)

    # User provisioning is owned by the explicit POST /users/sync endpoint
    # (the SyncUser use case), which clients call on login.
    sync_user = SyncUser(users=users, clock=_clock)

    get_event_feed = GetEventFeed(
        users=users,
        events=events,
        swipes=swipes,
        discovery=_discovery,
        enricher=_enricher,
        scorer=_scorer,
        clock=_clock,
    )
    record_swipe = RecordSwipe(
        users=users,
        events=events,
        swipes=swipes,
        ids=_ids,
        clock=_clock,
    )

    async def commit() -> None:
        await session.commit()
        await session.close()

    return RequestScope(
        user_id=identity.uid,
        get_event_feed=get_event_feed,
        record_swipe=record_swipe,
        sync_user=sync_user,
        commit=commit,
        email=identity.email,
        display_name=identity.display_name,
    )


app = create_app(
    use_case_factory=use_case_factory,
    cors_origins=[o.strip() for o in settings.cors_origins.split(",")],
    title=settings.app_name,
)


@app.on_event("startup")
async def _startup() -> None:
    await init_db()
