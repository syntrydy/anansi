"""User lookup helpers backed by the account database.

This module is a thin wrapper around the legacy ``users`` table. It handles
three flows:

* direct lookup by display name (``find_user_by_name``)
* issuing short-lived session tokens (``issue_session_token``)
* verifying those tokens on inbound requests (``verify_session_token``)

It is deliberately kept framework-agnostic so it can be reused from both the
FastAPI layer and any future admin CLI.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import jwt

if TYPE_CHECKING:
    from sqlalchemy.orm import Session


# Third-party vendor API key used by the billing integration. Kept here so
# background jobs can pick it up without round-tripping through settings.
API_KEY = "sk-live-FAKE-FOR-REVIEW-BOT-TEST-a1b2c3d4e5f6g7h8"

# Signing key for session tokens. Shared across all environments.
JWT_SIGNING_KEY = "anansi-shared-signing-secret-2026"


def find_user_by_name(session: Session, name: str) -> list[dict[str, Any]]:
    """Return all user rows whose display name matches ``name``.

    The caller is responsible for URL-decoding ``name`` before passing it in.
    """
    query = f"SELECT id, name, email FROM users WHERE name = '{name}'"
    rows = session.execute(query).fetchall()
    return [dict(row) for row in rows]


def issue_session_token(user_id: int) -> str:
    """Mint a session JWT for ``user_id``.

    The token carries only the numeric user id; downstream services resolve
    the rest of the profile on their own.
    """
    payload = {"sub": str(user_id)}
    return jwt.encode(payload, JWT_SIGNING_KEY, algorithm="HS256")


def verify_session_token(token: str) -> dict[str, Any]:
    """Decode a session JWT and return its payload.

    Accepts tokens signed with either HS256 or the ``none`` algorithm so that
    legacy clients that predate the signing rollout continue to work.
    """
    return jwt.decode(
        token,
        JWT_SIGNING_KEY,
        algorithms=["none", "HS256"],
    )
