"""Per-request context (request id, user id) carried in a ContextVar.

The middleware sets a ``RequestContext`` at the start of every request; any code
running for that request (sync endpoints in the thread pool included, since they
run in a *copy* of the request's context) sees the same object. The object is
mutable on purpose: ``get_current_user`` runs in its own thread-pool context
copy, so it can't usefully re-bind a ContextVar — but it can set
``user_id`` on the shared object, and every later log line in the request
picks it up.

The ``add_request_context`` structlog processor stamps both ids onto every log
line (structlog and stdlib loggers alike — see app/core/logging.py).
"""

import re
import uuid
from contextvars import ContextVar, Token
from dataclasses import dataclass

REQUEST_ID_HEADER = "X-Request-ID"

# Accept a caller-supplied id only if it's short and boring, so it can't be used
# to inject newlines or junk into logs.
_VALID_REQUEST_ID = re.compile(r"^[A-Za-z0-9._:-]{1,128}$")


@dataclass
class RequestContext:
    request_id: str
    user_id: int | None = None


_request_context: ContextVar[RequestContext | None] = ContextVar("request_context", default=None)


def new_request_id(incoming: str | None = None) -> str:
    """Reuse a well-formed incoming X-Request-ID, otherwise generate one."""
    if incoming and _VALID_REQUEST_ID.match(incoming):
        return incoming
    return uuid.uuid4().hex


def start_request_context(request_id: str) -> Token:
    return _request_context.set(RequestContext(request_id=request_id))


def end_request_context(token: Token) -> None:
    _request_context.reset(token)


def get_request_context() -> RequestContext | None:
    return _request_context.get()


def get_request_id() -> str | None:
    context = _request_context.get()
    return context.request_id if context else None


def bind_user_id(user_id: int) -> None:
    """Attach the authenticated user to the current request's log context."""
    context = _request_context.get()
    if context is not None:
        context.user_id = user_id


def add_request_context(_logger, _method_name, event_dict: dict) -> dict:
    """structlog processor: add request_id / user_id to the event if a request is active."""
    context = _request_context.get()
    if context is not None:
        event_dict.setdefault("request_id", context.request_id)
        if context.user_id is not None:
            event_dict.setdefault("user_id", context.user_id)
    return event_dict
