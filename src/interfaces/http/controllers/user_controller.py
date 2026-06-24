"""User HTTP controller.

Thin adapter: takes the identity already verified from the Firebase ID
token, upserts the user via the SyncUser use case, exposes the editable
profile and account stats, and serializes results. No business logic, no
infrastructure access.
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Response, status

from src.application.dtos.user_dtos import (
    GetUserProfileInput,
    SyncUserInput,
    UpdateUserProfileInput,
)
from src.application.exceptions import ResourceNotFoundError
from src.interfaces.http.dependencies import RequestScope, ScopeDep
from src.interfaces.http.schemas.user_schemas import (
    UpdateProfileRequest,
    UserAccountResponse,
    UserResponse,
    UserStatsResponse,
)

router = APIRouter(prefix="/users", tags=["users"])


@router.post("/sync", response_model=UserResponse)
async def sync_user(
    response: Response,
    scope: RequestScope = ScopeDep,
) -> UserResponse:
    """Upsert the authenticated user on login.

    The Firebase ID token is verified while the request scope is built;
    a missing or invalid token never reaches this handler (401 instead).
    """
    # Some identity providers omit the email claim; fall back to a stable
    # placeholder so the user record can still be created.
    email = scope.email or f"{scope.user_id}@unknown.local"

    result = await scope.sync_user.execute(
        SyncUserInput(
            uid=scope.user_id,
            email=email,
            display_name=scope.display_name,
        )
    )
    await scope.commit()

    response.status_code = (
        status.HTTP_201_CREATED if result.is_new else status.HTTP_200_OK
    )
    return UserResponse(
        uid=result.uid,
        email=result.email,
        display_name=result.display_name,
        username=result.username,
        preferred_activities=result.preferred_activities,
        created_at=result.created_at,
    )


@router.get("/me", response_model=UserAccountResponse)
async def get_me(
    scope: RequestScope = ScopeDep,
) -> UserAccountResponse:
    """Return the authenticated user's profile and activity stats.

    Scoped to the caller: the identity comes from the verified token, never
    from the request, so a user can only ever read their own account.
    """
    try:
        result = await scope.get_user_profile.execute(
            GetUserProfileInput(uid=scope.user_id)
        )
    except ResourceNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc

    return UserAccountResponse(
        uid=result.uid,
        email=result.email,
        username=result.username,
        name=result.name,
        preferred_activities=result.preferred_activities,
        created_at=result.created_at,
        stats=UserStatsResponse(liked_ideas=result.stats.liked_ideas),
    )


@router.put("/me", response_model=UserResponse)
async def update_profile(
    body: UpdateProfileRequest,
    scope: RequestScope = ScopeDep,
) -> UserResponse:
    """Persist edits to the authenticated user's handle, name, activities."""
    try:
        result = await scope.update_user_profile.execute(
            UpdateUserProfileInput(
                uid=scope.user_id,
                username=body.username,
                preferred_activities=body.preferred_activities,
                name=body.name,
            )
        )
        await scope.commit()
    except ResourceNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc

    return UserResponse(
        uid=result.uid,
        email=result.email,
        username=result.username,
        name=result.name,
        preferred_activities=result.preferred_activities,
        created_at=result.created_at,
    )
