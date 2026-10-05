"""Load and render versioned prompt files.

A "version" is the stem of a markdown file in this directory (e.g. ``system_v1``
-> ``system_v1.md``). Shipped versions are never edited in place: change
behaviour by adding ``system_v2.md`` and bumping ``SYSTEM_PROMPT_VERSION``, so
that stored ``prompt_version`` values keep pointing at the text that actually ran.

Placeholders use :class:`string.Template` syntax (``${name}``) so that braces in
JSON examples need no escaping. A literal dollar sign must be written ``$$``.
"""

from __future__ import annotations

import datetime as dt
import re
from collections.abc import Mapping
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from string import Template
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from app.core.logging import get_logger
from app.utils.date_utils import utcnow

logger = get_logger(__name__)

PROMPTS_DIR = Path(__file__).resolve().parent

#: The system prompt the agent currently ships with. Bump, never edit in place.
SYSTEM_PROMPT_VERSION = "system_v1"

_VERSION_RE = re.compile(r"^[a-z0-9]+(?:_[a-z0-9]+)*$")

_FALLBACK_TIMEZONE = "UTC"
_FALLBACK_CURRENCY = "INR"
_FALLBACK_NAME = "there"


class PromptError(Exception):
    """Base class for prompt loading/rendering failures.

    Deliberately not an ``AppException``: no client request can cause these, so
    they are deployment bugs and must surface as a generic 500, not a 4xx.
    """


class PromptNotFoundError(PromptError):
    """The requested prompt version does not exist."""


class PromptRenderError(PromptError):
    """The template could not be filled (missing variable or bad placeholder)."""


@dataclass(frozen=True, slots=True)
class RenderedPrompt:
    """A prompt ready to send, paired with the version that produced it."""

    version: str
    text: str


@dataclass(frozen=True, slots=True)
class PromptContext:
    """Everything the system prompt needs about the user, ORM-free.

    Built from a ``User`` via :meth:`from_user`, but holds no ORM object, so
    rendering is unit-testable without a database session.
    """

    user_first_name: str
    today: dt.date
    timezone: str
    currency: str

    @classmethod
    def from_user(cls, user: Any, *, now: dt.datetime | None = None) -> PromptContext:
        """Adapt a ``User`` row into a prompt context.

        ``now`` is for tests; it defaults to the current UTC instant. "Today" is
        resolved in the *user's* timezone, never the server's.
        """
        moment = now if now is not None else utcnow()
        if moment.tzinfo is None:
            moment = moment.replace(tzinfo=dt.UTC)

        tz_name = (getattr(user, "timezone", None) or _FALLBACK_TIMEZONE).strip()
        try:
            tzinfo: dt.tzinfo = ZoneInfo(tz_name)
        except (ZoneInfoNotFoundError, ValueError):
            logger.warning(
                "prompt.timezone_invalid",
                timezone=tz_name,
                fallback=_FALLBACK_TIMEZONE,
            )
            tz_name = _FALLBACK_TIMEZONE
            tzinfo = dt.UTC

        first_name = (getattr(user, "first_name", None) or "").strip()
        currency = (getattr(user, "currency", None) or _FALLBACK_CURRENCY).strip().upper()

        return cls(
            user_first_name=first_name or _FALLBACK_NAME,
            today=moment.astimezone(tzinfo).date(),
            timezone=tz_name,
            currency=currency or _FALLBACK_CURRENCY,
        )

    def as_variables(self) -> dict[str, str]:
        """The template variables this context supplies."""
        return {
            "user_first_name": self.user_first_name,
            "today": self.today.isoformat(),
            "today_human": self.today.strftime("%A, %d %B %Y"),
            "timezone": self.timezone,
            "currency": self.currency,
        }


def list_prompt_versions() -> list[str]:
    """Every prompt version present on disk, sorted."""
    return sorted(path.stem for path in PROMPTS_DIR.glob("*.md"))


@lru_cache(maxsize=32)
def load_prompt(version: str) -> str:
    """Return the raw text of a prompt version.

    Cached: prompt files are immutable once shipped, and ``--reload`` restarts
    the process during development.
    """
    if not _VERSION_RE.match(version):
        raise PromptNotFoundError(
            f"Invalid prompt version {version!r}: expected lowercase "
            "letters, digits and underscores"
        )

    path = PROMPTS_DIR / f"{version}.md"
    if not path.is_file():
        raise PromptNotFoundError(
            f"Prompt version {version!r} not found in {PROMPTS_DIR}. "
            f"Available: {', '.join(list_prompt_versions()) or 'none'}"
        )

    return path.read_text(encoding="utf-8").strip()


def required_variables(text: str) -> set[str]:
    """The placeholder names a template references."""
    return _identifiers(Template(text))


def render_text(text: str, variables: Mapping[str, Any]) -> str:
    """Fill ``${...}`` placeholders, failing loudly on a missing variable."""
    template = Template(text)
    missing = sorted(_identifiers(template) - set(variables))
    if missing:
        raise PromptRenderError(f"Missing prompt variable(s): {', '.join(missing)}")
    try:
        return template.substitute(variables)
    except ValueError as exc:  # a bare or malformed "$" in the file
        raise PromptRenderError(
            f"Invalid placeholder in prompt template: {exc}. Write a literal dollar sign as '$$'."
        ) from exc


def render_system_prompt(
    context: PromptContext,
    *,
    version: str = SYSTEM_PROMPT_VERSION,
) -> RenderedPrompt:
    """Render the system prompt for one chat turn."""
    text = render_text(load_prompt(version), context.as_variables())
    logger.debug("prompt.rendered", prompt_version=version, length=len(text))
    return RenderedPrompt(version=version, text=text)


def _identifiers(template: Template) -> set[str]:
    """Placeholder names in a template (``Template.get_identifiers`` is 3.11+)."""
    getter = getattr(template, "get_identifiers", None)
    if getter is not None:
        return set(getter())
    return {
        match.group("named") or match.group("braced")
        for match in template.pattern.finditer(template.template)
        if match.group("named") or match.group("braced")
    }
