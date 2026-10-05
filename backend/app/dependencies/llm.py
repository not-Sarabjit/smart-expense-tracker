from fastapi import Depends
from langchain_core.language_models.chat_models import BaseChatModel

from app.ai.llm.factory import get_chat_model
from app.core.config import Settings, get_settings


def get_llm(settings: Settings = Depends(get_settings)) -> BaseChatModel:
    """The configured primary chat model (cached across requests)."""
    return get_chat_model(settings=settings)
