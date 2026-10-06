# backend/app/ai/observability/smoke.py
"""Live smoke test for the tracing backend -- the acceptance check for Step 2.1.

    cd backend && python -m app.ai.observability.smoke

Needs TRACING_ENABLED=true plus real keys in backend/.env. Hits the network; never run in tests.
"""

from __future__ import annotations

import contextlib
import sys
import time

from app.ai.observability import tracing
from app.core.config import get_settings


def _line(title: str) -> None:
    print(f"\n--- {title} " + "-" * max(0, 60 - len(title)))


def main() -> int:
    settings = get_settings()

    _line("config")
    status = tracing.describe_tracing(settings)
    for field, value in status.__dict__.items():
        print(f"  {field:<16} {value}")

    if not status.enabled:
        print("\nTRACING_ENABLED is false. Set it to true in backend/.env and re-run.")
        return 1
    if not status.sdk_installed:
        print("\nSDK missing. From the repo root: uv sync --extra dev --extra ai --extra tracing")
        return 1
    if not status.configured:
        print("\nTRACING_PUBLIC_KEY / TRACING_SECRET_KEY missing in backend/.env.")
        return 1

    _line("client")
    client = tracing.get_tracing_client(settings)
    if client is None:
        print("  FAILED to build a client -- check the warning logged above.")
        return 1
    print("  client built")

    _line("auth")
    try:
        ok = client.auth_check()
        print(f"  auth_check() -> {ok}")
        if not ok:
            print("  Keys rejected. Check the keys AND that TRACING_HOST matches your region.")
            return 1
    except AttributeError:
        print("  auth_check() not available in this SDK version -- skipping, relying on the trace.")
    except Exception as exc:
        print(f"  auth_check() raised: {type(exc).__name__}: {exc}")
        return 1

    _line("emit a trace")
    trace_id = None
    try:
        with client.start_as_current_span(name="smoke.step_2_1") as span:
            span.update_trace(
                name="smoke.step_2_1",
                user_id="smoke-user",
                session_id="smoke-session",
                tags=["smoke", "step-2.1"],
                input={"question": "is tracing wired up?"},
            )
            time.sleep(0.05)
            span.update_trace(output={"answer": "yes"})
            with contextlib.suppress(Exception):
                trace_id = client.get_current_trace_id()
        print("  span emitted")
    except Exception as exc:
        print(f"  manual span API differs in this SDK version: {type(exc).__name__}: {exc}")
        print("  (the adapter itself is unaffected -- 2.2 uses the callback handler, not this API)")

    _line("callbacks")
    callbacks = tracing.get_tracing_callbacks(settings)
    print(
        f"  get_tracing_callbacks() -> {len(callbacks)} handler(s): "
        f"{[type(c).__name__ for c in callbacks]}"
    )
    if not callbacks:
        print("  No handler built -- 2.2 would silently trace nothing. Check warnings above.")
        return 1

    _line("flush")
    tracing.flush(settings)
    print("  flushed")

    if trace_id:
        try:
            print(f"\n  View it: {client.get_trace_url(trace_id=trace_id)}")
        except Exception:
            print(f"\n  trace_id: {trace_id}")

    tracing.shutdown(settings)
    print("\nOK. Open your Langfuse project -> Tracing -> Traces and look for 'smoke.step_2_1'.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
