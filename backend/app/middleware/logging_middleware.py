# app/middleware/logging_middleware.py
"""Request id + access logging, as a pure ASGI middleware.

Pure ASGI (not BaseHTTPMiddleware) so the request context is set in the same
context the endpoint runs in, and streaming responses (SSE, later) aren't buffered.

Per request:
  1. take X-Request-ID from the client if well-formed, else generate one;
  2. start the RequestContext (request_id; user_id is added by get_current_user);
  3. echo X-Request-ID and request-process-time on the response;
  4. log one "request.finished" line with method, path, status and duration.
"""

import time

from starlette.datastructures import Headers, MutableHeaders
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.core.logging import get_logger
from app.core.request_context import (
    REQUEST_ID_HEADER,
    end_request_context,
    new_request_id,
    start_request_context,
)

logger = get_logger("app.request")


class RequestLoggingMiddleware:
    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request_id = new_request_id(Headers(scope=scope).get(REQUEST_ID_HEADER))
        token = start_request_context(request_id)
        start_time = time.perf_counter()
        status_code = 500

        async def send_with_headers(message: Message) -> None:
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message["status"]
                headers = MutableHeaders(scope=message)
                headers[REQUEST_ID_HEADER] = request_id
                # To expose the timing in the api response
                duration_ms = (time.perf_counter() - start_time) * 1000
                headers["request-process-time"] = f"{duration_ms:.2f}"
            await send(message)

        try:
            await self.app(scope, receive, send_with_headers)
        except Exception:
            # Leave the context set: the outer ServerErrorMiddleware's handler logs the
            # traceback and needs the request_id. Each request runs in its own task context.
            self._log(scope, 500, start_time)
            raise
        self._log(scope, status_code, start_time)
        end_request_context(token)

    @staticmethod
    def _log(scope: Scope, status_code: int, start_time: float) -> None:
        logger.info(
            "request.finished",
            method=scope["method"],
            path=scope["path"],
            status_code=status_code,
            duration_ms=round((time.perf_counter() - start_time) * 1000, 2),
        )
