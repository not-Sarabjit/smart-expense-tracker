"""Feature-flag dependencies.

Flags are enforced at the HTTP boundary, not inside services. Put
``Depends(require_ai_enabled)`` on the AI routers (from Phase 1 on) so that
flipping AI_ENABLED=false returns a clean 503 instead of a half-working feature.
"""

from fastapi import Depends

from app.core.config import Settings, get_settings
from app.core.exceptions import FeatureDisabledException


def require_ai_enabled(settings: Settings = Depends(get_settings)) -> Settings:
    """Block the request unless the AI assistant is switched on."""
    if not settings.ai.enabled:
        raise FeatureDisabledException("AI Assistant is currently disabled")
    return settings