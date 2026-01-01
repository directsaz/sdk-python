"""Optional Django view helpers."""

from __future__ import annotations

import json
from typing import Callable, Optional

from django.conf import settings
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from .webhook import handle_challenge, parse_events, verify_signature


def make_webhook_view(
    *,
    webhook_token: Optional[str] = None,
    on_events: Optional[Callable[[list, HttpRequest], None]] = None,
    verify: bool = True,
):
    """
    urls.py:
        path("hooks/directsaz", make_webhook_view(on_events=my_handler))
    """

    @csrf_exempt
    @require_http_methods(["GET", "POST"])
    def view(request: HttpRequest) -> HttpResponse:
        token = webhook_token or getattr(settings, "DIRECTSAZ_WEBHOOK_TOKEN", "")
        if request.method == "GET":
            status, body = handle_challenge(request.headers.get("X-Webhook-Token"), token)
            return HttpResponse(body, status=status)

        raw = request.body
        if verify and not verify_signature(
            token,
            raw,
            request.headers.get("X-Directsaz-Timestamp"),
            request.headers.get("X-Directsaz-Signature"),
        ):
            return HttpResponse("invalid signature", status=401)

        events = parse_events(raw)
        if on_events is not None:
            on_events(events, request)
        return JsonResponse({"ok": True})

    return view
