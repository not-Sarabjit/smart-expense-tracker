"""Step 1.4 — prompt loading and rendering."""

import datetime as dt
from types import SimpleNamespace

import pytest

from app.ai.prompts import (
    SYSTEM_PROMPT_VERSION,
    PromptContext,
    PromptNotFoundError,
    PromptRenderError,
    list_prompt_versions,
    load_prompt,
    render_system_prompt,
    render_text,
)
from app.ai.prompts.loader import required_variables


def make_user(timezone="Asia/Kolkata", currency="INR", first_name="Sarabjit"):
    return SimpleNamespace(timezone=timezone, currency=currency, first_name=first_name)


# --- loading ---------------------------------------------------------------

def test_shipped_version_exists():
    assert SYSTEM_PROMPT_VERSION in list_prompt_versions()
    assert load_prompt(SYSTEM_PROMPT_VERSION).strip()


def test_unknown_version_raises():
    with pytest.raises(PromptNotFoundError):
        load_prompt("system_v999")


@pytest.mark.parametrize("version", ["../../../etc/passwd", "system v1", "System_V1", ""])
def test_version_names_are_validated(version):
    """A version is never used to build a path until it matches the whitelist."""
    with pytest.raises(PromptNotFoundError):
        load_prompt(version)


# --- rendering -------------------------------------------------------------

def test_missing_variable_is_an_error_not_silent():
    with pytest.raises(PromptRenderError) as exc:
        render_text("Hello ${who}, today is ${today}", {"today": "2026-10-05"})
    assert "who" in str(exc.value)


def test_braces_are_left_alone():
    """JSON examples must survive templating untouched."""
    rendered = render_text('{"type": "expense"} for ${name}', {"name": "A"})
    assert rendered == '{"type": "expense"} for A'


def test_extra_variables_are_ignored():
    assert render_text("Hi ${name}", {"name": "A", "unused": "B"}) == "Hi A"


# --- context ---------------------------------------------------------------

def test_today_is_resolved_in_the_users_timezone():
    """20:00 UTC is already the next day in Kolkata (UTC+05:30)."""
    now = dt.datetime(2026, 10, 5, 20, 0, tzinfo=dt.timezone.utc)
    context = PromptContext.from_user(make_user(), now=now)
    assert context.today == dt.date(2026, 10, 6)


def test_other_timezones_give_a_different_today():
    now = dt.datetime(2026, 10, 5, 20, 0, tzinfo=dt.timezone.utc)
    context = PromptContext.from_user(make_user(timezone="America/New_York"), now=now)
    assert context.today == dt.date(2026, 10, 5)


def test_naive_now_is_treated_as_utc():
    naive = dt.datetime(2026, 10, 5, 20, 0)
    aware = dt.datetime(2026, 10, 5, 20, 0, tzinfo=dt.timezone.utc)
    assert (
        PromptContext.from_user(make_user(), now=naive).today
        == PromptContext.from_user(make_user(), now=aware).today
    )


def test_bad_timezone_falls_back_to_utc():
    now = dt.datetime(2026, 10, 5, 20, 0, tzinfo=dt.timezone.utc)
    context = PromptContext.from_user(make_user(timezone="Mars/Olympus"), now=now)
    assert context.timezone == "UTC"
    assert context.today == dt.date(2026, 10, 5)


def test_missing_fields_fall_back():
    context = PromptContext.from_user(
        SimpleNamespace(timezone=None, currency=None, first_name=None)
    )
    assert context.timezone == "UTC"
    assert context.currency == "INR"
    assert context.user_first_name == "there"


def test_currency_is_upper_cased():
    assert PromptContext.from_user(make_user(currency="usd")).currency == "USD"


# --- the shipped prompt ----------------------------------------------------

def test_shipped_prompt_needs_only_what_the_context_supplies():
    """Guards against adding a ${placeholder} with nothing to fill it."""
    context = PromptContext.from_user(make_user())
    assert required_variables(load_prompt(SYSTEM_PROMPT_VERSION)) <= set(
        context.as_variables()
    )


def test_render_system_prompt_substitutes_everything():
    now = dt.datetime(2026, 10, 5, 6, 0, tzinfo=dt.timezone.utc)
    context = PromptContext.from_user(make_user(), now=now)
    rendered = render_system_prompt(context)

    assert rendered.version == SYSTEM_PROMPT_VERSION
    assert "${" not in rendered.text
    assert "Sarabjit" in rendered.text
    assert "2026-10-05" in rendered.text
    assert "Monday, 05 October 2026" in rendered.text
    assert "Asia/Kolkata" in rendered.text
    assert "INR" in rendered.text


def test_render_system_prompt_rejects_unknown_version():
    with pytest.raises(PromptNotFoundError):
        render_system_prompt(PromptContext.from_user(make_user()), version="system_v42")