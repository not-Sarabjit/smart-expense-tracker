"""Server-Sent Events: the wire format for the chat stream.

The event names and payload keys below are a **contract with the frontend**
(frozen in Step 1.6). Add new event types freely; never rename or repurpose an
existing one without changing the frontend in the same PR.

Wire format (one record):

    event: token\\n
    data: {"text":"Hi"}\\n
    \\n

The blank line terminates the record. Payloads are always single-line JSON, so
one `data:` line per record is enough.
"""

from __future__ import annotations

import json
from enum import StrEnum
from typing import Any


class SSEEvent(StrEnum):
    """Every event the chat stream may emit. Phase noted where not yet used."""

    message_start = "message_start"  # always first
    token = "token"  # 0..n
    tool_start = "tool_start"  # Phase 3 (3.8)
    tool_end = "tool_end"  # Phase 3 (3.8)
    clarification = "clarification"  # Phase 3 (3.9)
    confirm_required = "confirm_required"  # Phase 4 (4.4)
    error = "error"  # terminal
    message_end = "message_end"  # terminal, success


#: Headers that go with every SSE response.
#: - no-cache/no-transform: stop browsers and proxies caching or rewriting it
#: - X-Accel-Buffering: tells nginx not to buffer the body (it would otherwise
#:   hold chunks back and destroy the streaming effect)
SSE_HEADERS: dict[str, str] = {
    "Cache-Control": "no-cache, no-transform",
    "Connection": "keep-alive",
    "X-Accel-Buffering": "no",
}


def format_sse(event: SSEEvent | str, data: dict[str, Any]) -> str:
    """Render one SSE record. `default=str` keeps UUIDs/dates serialisable."""
    payload = json.dumps(data, separators=(",", ":"), default=str)
    return f"event: {event}\ndata: {payload}\n\n"


def sse_comment(text: str = "") -> str:
    """A comment line. Ignored by clients; useful as a keep-alive ping later."""
    return f": {text}\n\n"
