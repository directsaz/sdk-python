"""Optional FastAPI helpers."""

from __future__ import annotations

from typing import Awaitable, Callable, Optional

from fastapi import APIRouter, Header, Request, Response

from .webhook import handle_challenge, parse_events, verify_signature

EventHandler = Callable[[list, Request], Awaitable[None] | None]


def webhook_router(
    webhook_token: str,
    *,
    on_events: Optional[EventHandler] = None,
    verify: bool = True,
    path: str = "/hooks/directsaz",
) -> APIRouter:
    """
    Mount GET challenge + POST delivery on the same path.

    Example:
        app.include_router(webhook_router(os.environ["DIRECTSAZ_WEBHOOK_TOKEN"], on_events=...))
    """
    router = APIRouter()

    @router.api_route(path, methods=["GET", "POST"])
    async def handle(
        request: Request,
        x_webhook_token: Optional[str] = Header(default=None, alias="X-Webhook-Token"),
        x_directsaz_timestamp: Optional[str] = Header(default=None, alias="X-Directsaz-Timestamp"),
        x_directsaz_signature: Optional[str] = Header(default=None, alias="X-Directsaz-Signature"),
    ):
        if request.method == "GET":
            status, body = handle_challenge(x_webhook_token, webhook_token)
            return Response(content=body, status_code=status)

        raw = await request.body()
        if verify and not verify_signature(
            webhook_token, raw, x_directsaz_timestamp, x_directsaz_signature
        ):
            return Response(content="invalid signature", status_code=401)

        events = parse_events(raw)
        if on_events is not None:
            result = on_events(events, request)
            if hasattr(result, "__await__"):
                await result  # type: ignore[misc]
        return {"ok": True}

    return router
