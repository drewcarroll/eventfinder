"""Firebase token verification adapter.

Verifies Firebase ID tokens (issued after Google Sign-In on the Flutter
client) and returns the authenticated identity. This is infrastructure:
it speaks to the Firebase Admin SDK.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import firebase_admin
from firebase_admin import auth, credentials

from src.infrastructure.config.settings import Settings


@dataclass(frozen=True)
class AuthenticatedIdentity:
    """The verified identity extracted from a Firebase ID token."""

    uid: str
    email: str
    display_name: Optional[str]


class FirebaseAuthVerifier:
    """Verifies Firebase ID tokens via the Admin SDK."""

    def __init__(self, settings: Settings) -> None:
        if not firebase_admin._apps:  # noqa: SLF001 - SDK idiom
            if settings.firebase_credentials_path:
                cred = credentials.Certificate(
                    settings.firebase_credentials_path
                )
                firebase_admin.initialize_app(cred)
            else:
                # Uses Application Default Credentials when path is unset.
                firebase_admin.initialize_app()

    def verify(self, id_token: str) -> AuthenticatedIdentity:
        """Verify a Firebase ID token and return the identity."""
        decoded = auth.verify_id_token(id_token)
        return AuthenticatedIdentity(
            uid=decoded["uid"],
            email=decoded.get("email", ""),
            display_name=decoded.get("name"),
        )
