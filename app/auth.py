"""
Minimal API key authentication (bonus feature).

Design choice: a single shared API key via header, not JWT/sessions. This is
a single-user demo tool, not a multi-tenant product — JWT would add
infrastructure (issuing, expiry, refresh) with no real benefit here. The key
is read from an env var so it's never hardcoded, and auth is skipped
entirely if no key is configured (keeps local dev/testing frictionless).
"""
import os

from fastapi import Header, HTTPException, status

API_KEY = os.environ.get("SPEND_TRACKER_API_KEY")  # None => auth disabled


def require_api_key(x_api_key: str | None = Header(default=None)):
    if API_KEY is None:
        # No key configured (e.g. local dev) — auth is a no-op.
        return
    if x_api_key != API_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid API key. Provide it via the X-API-Key header.",
        )
