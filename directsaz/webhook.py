from __future__ import annotations

import hashlib
import hmac
import json
import time
from typing import Any, Optional, Union

HEADER_TOKEN = "X-Webhook-Token"
HEADER_TIMESTAMP = "X-Directsaz-Timestamp"
HEADER_SIGNATURE = "X-Directsaz-Signature"
HEADER_EVENT = "X-Directsaz-Event"


def handle_challenge(provided: Optional[str], expected: str) -> tuple[int, str]:
    """GET challenge: missing/wrong token → 401; ok → 200.

    An empty configured token fails closed: it would otherwise match anything
    an attacker chose to send."""
    if not expected or not provided or not hmac.compare_digest(
        provided.encode("utf-8"), expected.encode("utf-8")
    ):
        return 401, "unauthorized"
    return 200, "ok"


def extract_v1(signature_header: str) -> Optional[str]:
    for part in signature_header.split(","):
        part = part.strip()
        if part.startswith("v1="):
            return part[3:]
    return None


def verify_signature(
    webhook_token: str,
    raw_body: Union[str, bytes],
    timestamp: Optional[str],
    signature_header: Optional[str],
    max_skew_seconds: int = 300,
) -> bool:
    # An HMAC under an empty key can be computed by anyone: refuse it.
    if not webhook_token:
        return False
    if not timestamp or not signature_header:
        return False
    try:
        ts = int(timestamp)
    except (TypeError, ValueError):
        return False
    if ts <= 0:
        return False
    if abs(int(time.time()) - ts) > max_skew_seconds:
        return False

    v1 = extract_v1(signature_header)
    if not v1:
        return False

    body = raw_body.decode("utf-8") if isinstance(raw_body, (bytes, bytearray)) else raw_body
    expected = hmac.new(
        webhook_token.encode("utf-8"),
        f"{ts}.{body}".encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    # Compare bytes: compare_digest raises TypeError on a non-ASCII str.
    return hmac.compare_digest(expected.encode("ascii"), v1.encode("utf-8"))


def parse_events(body: Union[str, bytes, dict]) -> list[dict[str, Any]]:
    if isinstance(body, (bytes, bytearray)):
        body = body.decode("utf-8")
    if isinstance(body, str):
        data = json.loads(body)
    else:
        data = body
    events = data.get("events") if isinstance(data, dict) else None
    return list(events) if isinstance(events, list) else []
