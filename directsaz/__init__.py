"""Directsaz Developer API SDK."""

from .client import Client, ApiError, ApiResult
from .webhook import (
    handle_challenge,
    verify_signature,
    parse_events,
    extract_v1,
    HEADER_TOKEN,
    HEADER_TIMESTAMP,
    HEADER_SIGNATURE,
    HEADER_EVENT,
)

__all__ = [
    "Client",
    "ApiError",
    "ApiResult",
    "handle_challenge",
    "verify_signature",
    "parse_events",
    "extract_v1",
    "HEADER_TOKEN",
    "HEADER_TIMESTAMP",
    "HEADER_SIGNATURE",
    "HEADER_EVENT",
]


def _detect_version() -> str:
    # Single source of truth is pyproject.toml. Reading the installed metadata
    # keeps __version__ from drifting behind the published release.
    try:
        from importlib.metadata import PackageNotFoundError, version

        return version("directsaz")
    except Exception:  # not installed (running from a source tree)
        return "1.1.0"


__version__ = _detect_version()
