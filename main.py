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

from src.application.use_cases.delete_liked_idea import DeleteLikedIdea
from src.application.use_cases.get_event_feed import GetEventFeed
from src.application.use_cases.get_user_profile import GetUserProfile
from src.application.use_cases.like_idea import LikeIdea
from src.application.use_cases.list_liked_ideas import ListLikedIdeas
from src.application.use_cases.resolve_location import ResolveLocation
from src.application.use_cases.search_locations import SearchLocations
from src.application.use_cases.sync_user import SyncUser
from src.application.use_cases.update_user_profile import UpdateUserProfile
from src.domain.services.card_filter import CardFilter
from src.domain.services.card_merger import CardMerger
from src.domain.services.recommendation_scorer import RecommendationScorer
from src.infrastructure.auth.firebase_auth import FirebaseAuthVerifier
from src.infrastructure.config.settings import get_settings
from src.infrastructure.discovery.tavily_event_discovery import (
    TavilyEventDiscovery,
)
from src.infrastructure.geocoding.nominatim_geocoding import (
    NominatimGeocoding,
)
from src.infrastructure.llm.anthropic_card_ranker import (
    AnthropicCardRanker,
)
from src.infrastructure.llm.anthropic_idea_generator import (
    AnthropicIdeaGenerator,
)
from src.infrastructure.llm.anthropic_idea_verifier import (
    AnthropicIdeaVerifier,
)
from src.infrastructure.persistence.database import SessionFactory
from src.infrastructure.persistence.sql_event_repository import (
    SqlEventRepository,
)
from src.infrastructure.persistence.sql_liked_idea_repository import (
    SqlLikedIdeaRepository,
)
from src.infrastructure.persistence.sql_user_repository import (
    SqlUserRepository,
)
from src.infrastructure.system.random_username_generator import (
    RandomUsernameGenerator,
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
_geocoder = NominatimGeocoding(settings.geocoding_user_agent, _http_client)
_idea_generator = AnthropicIdeaGenerator(
    settings.anthropic_api_key, settings.anthropic_model
)
_ranker = AnthropicCardRanker(
    settings.anthropic_api_key, settings.anthropic_model
)
_verifier = AnthropicIdeaVerifier(
    settings.anthropic_api_key, settings.anthropic_model
)
_merger = CardMerger()
_card_filter = CardFilter()
_scorer = RecommendationScorer()
_clock = SystemClock()
_ids = UuidIdGenerator()
_usernames = RandomUsernameGenerator()


async def use_case_factory(token: str) -> RequestScope:
    """Authenticate, open a DB session, and build request-scoped use cases."""
    try:
        identity = _auth.verify(token)
    except Exception as exc:  # noqa: BLE001 - translate to auth failure
        raise PermissionError("Invalid authentication token") from exc

    session = SessionFactory()

    users = SqlUserRepository(session)
    events = SqlEventRepository(session)
    liked_ideas = SqlLikedIdeaRepository(session)

    # User provisioning is owned by the explicit POST /users/sync endpoint
    # (the SyncUser use case), which clients call on login.
    sync_user = SyncUser(users=users, clock=_clock, usernames=_usernames)
    update_user_profile = UpdateUserProfile(users=users, clock=_clock)
    get_user_profile = GetUserProfile(
        users=users,
        liked_ideas=liked_ideas,
        clock=_clock,
    )

    get_event_feed = GetEventFeed(
        users=users,
        events=events,
        discovery=_discovery,
        idea_generator=_idea_generator,
        ranker=_ranker,
        verifier=_verifier,
        merger=_merger,
        card_filter=_card_filter,
        scorer=_scorer,
        clock=_clock,
    )
    like_idea = LikeIdea(
        users=users,
        liked_ideas=liked_ideas,
        ids=_ids,
        clock=_clock,
    )
    list_liked_ideas = ListLikedIdeas(liked_ideas=liked_ideas)
    delete_liked_idea = DeleteLikedIdea(liked_ideas=liked_ideas)
    resolve_location = ResolveLocation(geocoder=_geocoder)
    search_locations = SearchLocations(geocoder=_geocoder)

    async def commit() -> None:
        await session.commit()
        await session.close()

    return RequestScope(
        user_id=identity.uid,
        get_event_feed=get_event_feed,
        like_idea=like_idea,
        list_liked_ideas=list_liked_ideas,
        delete_liked_idea=delete_liked_idea,
        sync_user=sync_user,
        update_user_profile=update_user_profile,
        get_user_profile=get_user_profile,
        resolve_location=resolve_location,
        search_locations=search_locations,
        commit=commit,
        email=identity.email,
        display_name=identity.display_name,
    )


app = create_app(
    use_case_factory=use_case_factory,
    cors_origins=[o.strip() for o in settings.cors_origins.split(",")],
    title=settings.app_name,
)

# Note: the schema is provisioned out-of-band by Alembic (``make migrate``),
# not at startup. See src/infrastructure/persistence/database.py.
