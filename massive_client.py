"""Minimal Massive.com REST client using a secret-injected API key."""

from __future__ import annotations

import os
from typing import Any

import requests


class MassiveApiError(RuntimeError):
    """Raised when the Massive API cannot be reached or rejects a request."""


def is_massive_configured() -> bool:
    """Return True when the Massive API key was injected into the app."""
    return bool(os.getenv("MASSIVE_API_KEY", "").strip())


def test_massive_connection(symbol: str = "AAPL") -> dict[str, Any]:
    """Make one small authenticated request without exposing the API key."""
    api_key = os.getenv("MASSIVE_API_KEY", "").strip()
    if not api_key:
        raise MassiveApiError(
            "MASSIVE_API_KEY is missing. Add the Massive secret as an App "
            "resource with key 'massive_api_key_secret', then redeploy."
        )

    base_url = os.getenv("MASSIVE_API_BASE_URL", "https://api.massive.com").rstrip("/")
    ticker = symbol.strip().upper() or "AAPL"
    url = f"{base_url}/v2/aggs/ticker/{ticker}/prev"

    try:
        response = requests.get(
            url,
            headers={"Authorization": f"Bearer {api_key}"},
            params={"adjusted": "true"},
            timeout=20,
        )
    except requests.RequestException as exc:
        raise MassiveApiError(f"Could not reach Massive: {exc}") from exc

    if response.status_code >= 400:
        detail = ""
        try:
            payload = response.json()
            detail = payload.get("error") or payload.get("message") or payload.get("status") or ""
        except ValueError:
            detail = response.text[:200]
        suffix = f" — {detail}" if detail else ""
        raise MassiveApiError(
            f"Massive returned HTTP {response.status_code}{suffix}. "
            "Check the API key and your Massive plan access."
        )

    payload = response.json()
    results = payload.get("results") or []
    latest = results[0] if results else {}
    return {
        "status": payload.get("status", "OK"),
        "symbol": ticker,
        "previous_close": latest.get("c"),
        "request_id": payload.get("request_id"),
    }
