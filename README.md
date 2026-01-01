# Directsaz Python SDK

Works with **FastAPI**, **Django**, Flask, or plain scripts. Uses `httpx`.

## Install

```bash
pip install directsaz
# with FastAPI extras:
pip install "directsaz[fastapi]"
# with Django extras:
pip install "directsaz[django]"
# or editable, from a local clone of this repo:
pip install -e "/path/to/sdk-python[fastapi]"
```

## Send API

```python
from directsaz import Client

with Client(api_key="ds_live_…") as ds:
    ds.send_dm(recipient_id, "Hello")
    ds.send_image(recipient_id, "https://cdn.example.com/a.jpg", buttons=[
        {"title": "Open", "url": "https://example.com"},
    ])
    ds.send_carousel(recipient_id, cards)
    ds.private_reply(comment_id, "Thanks!")
    ds.comment_reply(comment_id, "Public reply")
    ds.like(recipient_id, message_id)
    ds.list_posts(limit=30)
    ds.follow_status(user_id)
```

### `202` means queued, not sent

Sends are queued and delivered to Instagram asynchronously — a Meta failure *after* queueing never
reaches you. Every result carries the status it came back with:

```python
r = ds.send_dm(recipient_id, "Hello")
r.http_status   # 202 = accepted for delivery
```

The result is still an ordinary `dict`, so existing code is unaffected.

### Errors

Every failure — HTTP *and* transport — raises `ApiError`, so one `except` covers everything.

```python
from directsaz import ApiError

try:
    ds.send_dm(recipient_id, "x" * 1500)
except ApiError as e:
    e.status   # 422 — or 0 when the request never got a response
    e.errors   # [{"field": "text", "rule": "max_bytes", "msg": "…got 1500"}]
```

`e.errors` is always a list, empty when the response carried no field-level detail.

## FastAPI webhook

```python
import os
from fastapi import FastAPI
from directsaz import Client
from directsaz.fastapi_app import webhook_router

app = FastAPI()
ds = Client(api_key=os.environ["DIRECTSAZ_API_KEY"])

async def on_events(events, request):
    for event in events:
        if event.get("type") == "dm":
            rid = (event.get("actions") or {}).get("dm", {}).get("recipient_id")
            if rid:
                ds.send_dm(rid, "Got it")

app.include_router(
    webhook_router(os.environ["DIRECTSAZ_WEBHOOK_TOKEN"], on_events=on_events)
)
```

## Django webhook

```python
# urls.py
from directsaz.django_app import make_webhook_view

urlpatterns = [
    path("hooks/directsaz", make_webhook_view(on_events=my_handler)),
]
```

Set `DIRECTSAZ_WEBHOOK_TOKEN` in Django settings. An empty or unset webhook token fails closed: every challenge gets
401 and every delivery is rejected.
