"""User HTTP controller.

Thin adapter: takes the identity already verified from the Firebase ID
token, upserts the user via the SyncUser use case, and serializes the
result. No business logic, no infrastructure access.
"""
from __future__ import annotations

from fastapi import APIRouter, Response, status

from src.application.dtos.user_dtos import SyncUserInput
from src.interfaces.http.dependencies import RequestScope, ScopeDep
from src.interfaces.http.schemas.user_schemas import UserResponse

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
        created_at=result.created_at,
    )
