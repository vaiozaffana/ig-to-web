from app.modules.adapters.llm import llm_client
from app.modules.schemas.article_draft_schema import ArticleDraftOutput, SeoMetadataOutput


def enhance_seo(article: ArticleDraftOutput) -> SeoMetadataOutput:
    return llm_client.generate_seo_metadata(article)
