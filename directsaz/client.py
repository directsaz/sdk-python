from __future__ import annotations

from typing import Any, Optional
from urllib.parse import quote

import httpx


class ApiResult(dict):
    """
    API envelope with the HTTP status attached.

    ``/send`` answers **202** to mean *queued* — the Meta delivery happens
    asynchronously afterwards and its failures never reach the caller — so the
    status is worth keeping::

        r = ds.send_dm(rid, "hi")
        if r.http_status == 202:
            ...
    """

    http_status: int = 0


class ApiError(Exception):
    def __init__(self, message: str, status: int = 0, payload: Any = None):
        super().__init__(message)
        self.status = status
        self.payload = payload

    @property
    def errors(self) -> list:
        if isinstance(self.payload, dict):
            err = self.payload.get("errors")
            return err if isinstance(err, list) else []
        return []


class Client:
    """Client for Directsaz developer-worker REST API."""

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://developers.directsaz.com/api/v1",
        timeout: float = 15.0,
        client: Optional[httpx.Client] = None,
    ):
        if not api_key:
            raise ValueError("api_key is required")
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self._owns_client = client is None
        self._client = client or httpx.Client(timeout=timeout)

    def close(self) -> None:
        if self._owns_client:
            self._client.close()

    def __enter__(self) -> "Client":
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()

    def send(self, payload: dict) -> dict:
        return self._request("POST", "/send", json=payload)

    def send_dm(self, recipient_id: str, text: str, buttons: Optional[list] = None) -> dict:
        body: dict[str, Any] = {
            "action": "dm",
            "recipient_id": recipient_id,
            "type": "text",
            "text": text,
        }
        if buttons:
            body["buttons"] = buttons
        return self.send(body)

    def send_image(self, recipient_id: str, media_url: str, buttons: Optional[list] = None) -> dict:
        body: dict[str, Any] = {
            "action": "dm",
            "recipient_id": recipient_id,
            "type": "image",
            "media_url": media_url,
        }
        if buttons:
            body["buttons"] = buttons
        return self.send(body)

    def send_video(self, recipient_id: str, media_url: str) -> dict:
        return self.send(
            {
                "action": "dm",
                "recipient_id": recipient_id,
                "type": "video",
                "media_url": media_url,
            }
        )

    def send_carousel(self, recipient_id: str, cards: list) -> dict:
        return self.send(
            {
                "action": "dm",
                "recipient_id": recipient_id,
                "type": "carousel",
                "cards": cards,
            }
        )

    def private_reply(self, comment_id: str, text: str, **extra: Any) -> dict:
        body = {"action": "private_reply", "comment_id": comment_id, "text": text, **extra}
        return self.send(body)

    def comment_reply(self, comment_id: str, text: str) -> dict:
        return self.send(
            {"action": "comment_reply", "comment_id": comment_id, "text": text}
        )

    def like(self, recipient_id: str, message_id: str) -> dict:
        return self.send(
            {
                "action": "like",
                "recipient_id": recipient_id,
                "message_id": message_id,
            }
        )

    def list_posts(
        self,
        limit: int = 30,
        after: Optional[str] = None,
        before: Optional[str] = None,
    ) -> dict:
        params: dict[str, Any] = {"limit": limit}
        if after:
            params["after"] = after
        if before:
            params["before"] = before
        return self._request("GET", "/posts", params=params)

    def follow_status(self, user_id: str) -> dict:
        # quote() with safe="" — ids come from webhook payloads, and an
        # unescaped "/" would silently retarget the request at another route.
        return self._request("GET", f"/users/{quote(str(user_id), safe='')}/follow-status")

    def _request(
        self,
        method: str,
        path: str,
        *,
        json: Any = None,
        params: Optional[dict] = None,
        auth: bool = True,
    ) -> dict:
        headers = {"Accept": "application/json"}
        if auth:
            headers["Authorization"] = f"Bearer {self.api_key}"
        url = f"{self.base_url}/{path.lstrip('/')}"
        try:
            res = self._client.request(
                method, url, headers=headers, json=json, params=params
            )
        except httpx.HTTPError as e:
            raise ApiError(str(e)) from e

        try:
            data = res.json() if res.content else {}
        except Exception as e:
            raise ApiError("Invalid JSON response", res.status_code, res.text) from e

        ok = data.get("success") is True or (res.is_success and data.get("success") is not False)
        if not ok or res.status_code >= 400:
            raise ApiError(
                str(data.get("msg") or data.get("message") or "API error"),
                res.status_code,
                data,
            )
        result = ApiResult(data)
        result.http_status = res.status_code
        return result
