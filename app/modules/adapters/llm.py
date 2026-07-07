from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, ValidationError

from app.models.agent_run import AgentRun
from app.models.enums import AgentRunStatus, ComplianceVerdict
from app.modules.schemas.article_draft_schema import (
    ArticleDraftOutput,
    ComplianceCheckResult,
    SeoMetadataOutput,
)


def _slugify(value: str) -> str:
    allowed = []
    previous_dash = False
    for char in value.lower():
        if char.isalnum():
            allowed.append(char)
            previous_dash = False
        elif not previous_dash:
            allowed.append("-")
            previous_dash = True
    return "".join(allowed).strip("-") or "artikel-sekolah"


class LLMClient:
    def generate_article(self, payload: dict[str, Any]) -> ArticleDraftOutput:
        caption = str(payload.get("caption") or "Kegiatan sekolah")
        permalink = str(payload.get("permalink") or "")
        title = "Kegiatan Sekolah dari Instagram"
        if caption:
            title = caption.split(".")[0][:70].strip() or title
        markdown = (
            f"# {title}\n\n"
            f"{caption}\n\n"
            "Artikel ini disusun dari unggahan Instagram resmi sekolah dan "
            "tetap menunggu review admin.\n\n"
            f"Sumber: {permalink}"
        )
        return ArticleDraftOutput(
            title=title,
            slug=_slugify(title),
            summary=f"Ringkasan kegiatan: {caption[:120]}",
            content_markdown=markdown,
            meta_title=title[:70],
            meta_description=f"Berita sekolah berdasarkan unggahan Instagram: {caption[:120]}"[
                :180
            ],
            category="Berita Sekolah",
            tags=list(payload.get("hashtags") or ["sekolah"]),
            image_alt_text=f"Dokumentasi {title.lower()}",
            source_instagram_url=permalink,
        )

    def generate_seo_metadata(self, article: ArticleDraftOutput) -> SeoMetadataOutput:
        tags = article.tags or ["sekolah"]
        return SeoMetadataOutput(
            meta_title=article.meta_title[:70],
            meta_description=article.meta_description[:180],
            tags=tags,
            category=article.category,
        )

    def check_compliance(self, article: ArticleDraftOutput) -> ComplianceCheckResult:
        lowered = f"{article.title} {article.summary} {article.content_markdown}".lower()
        blocked_terms = ["nomor induk", "alamat rumah", "nik", "kartu keluarga"]
        flagged = [term for term in blocked_terms if term in lowered]
        if flagged:
            return ComplianceCheckResult(
                verdict=ComplianceVerdict.NEEDS_REVISION,
                reasons=[f"Konten mengandung data pribadi: {term}" for term in flagged],
                flagged_sections=flagged,
            )
        if article.source_instagram_url == "":
            return ComplianceCheckResult(
                verdict=ComplianceVerdict.FAIL,
                reasons=["Source Instagram URL wajib ada untuk audit."],
                flagged_sections=["source_instagram_url"],
            )
        return ComplianceCheckResult(verdict=ComplianceVerdict.PASS, reasons=[])


llm_client = LLMClient()


def run_agent_with_audit[SchemaT: BaseModel](
    session: Any,
    agent_name: str,
    input_json: dict[str, Any],
    call: Any,
    output_schema: type[SchemaT],
) -> SchemaT:
    started_at = datetime.now(UTC)
    run = AgentRun(
        agent_name=agent_name,
        input_json=input_json,
        output_json={},
        status=AgentRunStatus.SUCCESS,
        started_at=started_at,
    )
    session.add(run)
    session.commit()
    session.refresh(run)

    try:
        result = call()
        parsed = output_schema.model_validate(result)
        run.output_json = parsed.model_dump(mode="json")
        run.status = AgentRunStatus.SUCCESS
        run.finished_at = datetime.now(UTC)
        session.add(run)
        session.commit()
        return parsed
    except (ValidationError, Exception) as exc:
        run.status = AgentRunStatus.ERROR
        run.error_message = str(exc)
        run.finished_at = datetime.now(UTC)
        session.add(run)
        session.commit()
        raise
