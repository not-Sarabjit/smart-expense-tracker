"""Structured JSON logs + request ids (Step 0.9)."""

import io
import json
import logging

import pytest
from fastapi.testclient import TestClient

from app.api.main import app
from app.api.transaction import get_transaction_service
from app.core.logging import build_formatter
from app.core.request_context import get_request_id


@pytest.fixture
def json_logs():
    """Captures every log line exactly as the app's JSON formatter renders it."""
    stream = io.StringIO()
    handler = logging.StreamHandler(stream)
    handler.setFormatter(build_formatter(json_logs=True))
    root = logging.getLogger()
    root.addHandler(handler)

    def lines() -> list[dict]:
        handler.flush()
        return [json.loads(line) for line in stream.getvalue().splitlines() if line.strip()]

    yield lines
    root.removeHandler(handler)


def lines_for(lines: list[dict], request_id: str) -> list[dict]:
    return [line for line in lines if line.get("request_id") == request_id]


def test_request_id_is_generated_and_returned(client):
    response = client.get("/health")

    request_id = response.headers["X-Request-ID"]
    assert len(request_id) == 32
    assert client.get("/health").headers["X-Request-ID"] != request_id


def test_incoming_request_id_is_propagated(client):
    response = client.get("/health", headers={"X-Request-ID": "client-abc-123"})
    assert response.headers["X-Request-ID"] == "client-abc-123"


@pytest.mark.parametrize("bad", ["has space", "x" * 200, "inject\\nnewline", "semi;colon"])
def test_malformed_incoming_request_id_is_replaced(client, bad):
    response = client.get("/health", headers={"X-Request-ID": bad})
    assert response.headers["X-Request-ID"] != bad
    assert len(response.headers["X-Request-ID"]) == 32


def test_one_requests_log_lines_can_be_filtered_by_request_id(client, user_a_headers, json_logs):
    """Done-when for 0.9: every line of a request carries its id (and the user's id)."""
    response = client.post(
        "/api/v1/transactions",
        json={"amount": 5, "type": "expense", "date": "2026-08-01"},
        headers={**user_a_headers, "X-Request-ID": "req-create-1"},
    )
    client.get("/api/v1/transactions", headers={**user_a_headers, "X-Request-ID": "req-list-2"})

    lines = json_logs()
    create_lines = lines_for(lines, "req-create-1")
    events = [line["event"] for line in create_lines]

    assert "transaction.created" in events
    assert "request.finished" in events
    assert all(line["user_id"] == 1 for line in create_lines)
    created = next(line for line in create_lines if line["event"] == "transaction.created")
    assert created["transaction_id"] == response.json()["id"]
    # the other request's lines don't leak in
    assert {line["event"] for line in lines_for(lines, "req-list-2")} == {"request.finished"}


def test_access_line_has_method_path_status_and_duration(client, json_logs):
    client.get("/health", headers={"X-Request-ID": "req-health"})

    [access] = [
        line for line in lines_for(json_logs(), "req-health") if line["event"] == "request.finished"
    ]
    assert access["method"] == "GET"
    assert access["path"] == "/health"
    assert access["status_code"] == 200
    assert access["duration_ms"] >= 0
    assert access["level"] == "info"
    assert access["timestamp"].endswith("Z")


def test_stdlib_loggers_also_get_the_request_id(client, user_a_headers, json_logs):
    """Plain logging.getLogger() calls (libraries, old modules) are enriched too."""

    def service_that_logs():
        logging.getLogger("some.library").warning("legacy %s", "message")
        raise RuntimeError("stop here")

    app.dependency_overrides[get_transaction_service] = service_that_logs
    try:
        TestClient(app, raise_server_exceptions=False).get(
            "/api/v1/transactions", headers={**user_a_headers, "X-Request-ID": "req-stdlib"}
        )
    finally:
        app.dependency_overrides.pop(get_transaction_service, None)

    legacy = [
        line for line in lines_for(json_logs(), "req-stdlib") if line["logger"] == "some.library"
    ]
    assert legacy[0]["event"] == "legacy message"
    assert legacy[0]["user_id"] == 1


def test_unhandled_error_keeps_the_request_id(client, user_a_headers, json_logs):
    def broken_service():
        raise RuntimeError("boom")

    app.dependency_overrides[get_transaction_service] = broken_service
    try:
        response = TestClient(app, raise_server_exceptions=False).get(
            "/api/v1/transactions", headers={**user_a_headers, "X-Request-ID": "req-boom"}
        )
    finally:
        app.dependency_overrides.pop(get_transaction_service, None)

    assert response.status_code == 500
    assert response.headers["X-Request-ID"] == "req-boom"
    [error] = [
        line
        for line in lines_for(json_logs(), "req-boom")
        if line["event"] == "request.unhandled_exception"
    ]
    assert "RuntimeError: boom" in error["exception"]


def test_no_request_context_outside_a_request(client):
    client.get("/health")
    assert get_request_id() is None
