from typing import Any

from app.modules.adapters.llm import llm_client
from app.modules.schemas.article_draft_schema import ArticleDraftOutput


def generate_article(payload: dict[str, Any]) -> ArticleDraftOutput:
    return llm_client.generate_article(payload)
