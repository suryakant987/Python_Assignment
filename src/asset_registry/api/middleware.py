from __future__ import annotations

import json
import logging
import time
from collections import defaultdict, deque

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from asset_registry.config import get_settings

logger = logging.getLogger("asset_registry.requests")


class ProcessTimeMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start = time.perf_counter()
        response = await call_next(request)
        duration_ms = round((time.perf_counter() - start) * 1000, 2)
        request.state.duration_ms = duration_ms
        response.headers["X-Process-Time-Ms"] = str(duration_ms)

        user = "-"
        auth = request.headers.get("authorization")
        if auth:
            user = "signed-in"
        logger.info(
            "method=%s path=%s status=%s duration_ms=%s caller=%s",
            request.method,
            request.url.path,
            response.status_code,
            duration_ms,
            user,
        )

        content_type = response.headers.get("content-type", "")
        if not content_type.startswith("application/json"):
            return response

        body = b""
        async for chunk in response.body_iterator:
            body += chunk
        try:
            payload = json.loads(body)
            if isinstance(payload, dict) and "duration_ms" not in payload:
                payload["duration_ms"] = duration_ms
                body = json.dumps(payload).encode("utf-8")
        except (json.JSONDecodeError, UnicodeDecodeError, TypeError, ValueError):
            pass

        headers = dict(response.headers)
        headers["content-length"] = str(len(body))
        return Response(
            content=body,
            status_code=response.status_code,
            headers=headers,
            media_type="application/json",
        )


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, exempt_paths: set[str] | None = None) -> None:
        super().__init__(app)
        self.exempt_paths = exempt_paths or {"/status"}
        self._hits: dict[str, deque[float]] = defaultdict(deque)

    def _caller_key(self, request: Request) -> str:
        auth = request.headers.get("authorization")
        if auth:
            return f"token:{auth[-24:]}"
        client = request.client.host if request.client else "unknown"
        return f"ip:{client}"

    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        if path in self.exempt_paths or path.rstrip("/") in self.exempt_paths:
            return await call_next(request)

        settings = get_settings()
        limit = settings.rate_limit_per_minute
        if limit <= 0:
            return await call_next(request)

        key = self._caller_key(request)
        now = time.monotonic()
        window = self._hits[key]
        cutoff = now - 60
        while window and window[0] <= cutoff:
            window.popleft()
        if len(window) >= limit:
            retry = max(1, int(60 - (now - window[0])) + 1)
            body = {
                "error": "rate_limited",
                "message": "Too many requests. Try again shortly.",
                "details": [
                    {
                        "field": "rate_limit",
                        "reason": f"limit is {limit} requests per minute; retry after {retry} seconds",
                    }
                ],
            }
            return JSONResponse(
                status_code=429,
                content=body,
                headers={"Retry-After": str(retry)},
            )
        window.append(now)
        return await call_next(request)
