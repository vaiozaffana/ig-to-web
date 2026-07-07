"""initial schema

Revision ID: 0001_initial_schema
Revises:
Create Date: 2026-07-02 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
import sqlmodel
from alembic import op

revision: str = "0001_initial_schema"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "agent_runs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("agent_name", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("input_json", sa.JSON(), nullable=True),
        sa.Column("output_json", sa.JSON(), nullable=True),
        sa.Column("status", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("error_message", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("started_at", sa.DateTime(), nullable=False),
        sa.Column("finished_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_agent_runs_agent_name", "agent_runs", ["agent_name"], unique=False)

    op.create_table(
        "instagram_posts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("instagram_media_id", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("permalink", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("caption", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("hashtags", sa.JSON(), nullable=True),
        sa.Column("media_url", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("media_type", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("local_media_url", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("posted_at", sa.DateTime(), nullable=False),
        sa.Column("fetched_at", sa.DateTime(), nullable=False),
        sa.Column("status", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("raw_payload_json", sa.JSON(), nullable=True),
        sa.Column("error_message", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("retry_count", sa.Integer(), nullable=False),
        sa.Column("max_retries", sa.Integer(), nullable=False),
        sa.Column("next_retry_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_instagram_posts_instagram_media_id",
        "instagram_posts",
        ["instagram_media_id"],
        unique=True,
    )
    op.create_index("ix_instagram_posts_status", "instagram_posts", ["status"], unique=False)

    op.create_table(
        "article_drafts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("instagram_post_id", sa.Integer(), nullable=False),
        sa.Column("title", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("slug", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("summary", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("content_markdown", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("content_html", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("meta_title", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("meta_description", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("category", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("tags", sa.JSON(), nullable=True),
        sa.Column("image_alt_text", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("source_instagram_url", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("status", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("approved_by", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("approved_at", sa.DateTime(), nullable=True),
        sa.Column("published_at", sa.DateTime(), nullable=True),
        sa.Column("error_message", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("retry_count", sa.Integer(), nullable=False),
        sa.Column("max_retries", sa.Integer(), nullable=False),
        sa.Column("next_retry_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["instagram_post_id"], ["instagram_posts.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_article_drafts_instagram_post_id", "article_drafts", ["instagram_post_id"])
    op.create_index("ix_article_drafts_slug", "article_drafts", ["slug"])
    op.create_index("ix_article_drafts_status", "article_drafts", ["status"])

    op.create_table(
        "article_reviews",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("article_draft_id", sa.Integer(), nullable=False),
        sa.Column("admin_id", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("action", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("comment", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["article_draft_id"], ["article_drafts.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_article_reviews_article_draft_id", "article_reviews", ["article_draft_id"])

    op.create_table(
        "notifications",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("article_draft_id", sa.Integer(), nullable=False),
        sa.Column("channel", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("recipient", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("message", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("status", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("sent_at", sa.DateTime(), nullable=True),
        sa.Column("error_message", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["article_draft_id"], ["article_drafts.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_notifications_article_draft_id", "notifications", ["article_draft_id"])
    op.create_index("ix_notifications_status", "notifications", ["status"])

    op.create_table(
        "publish_logs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("article_draft_id", sa.Integer(), nullable=False),
        sa.Column("target_url", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("status", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("response_payload", sa.JSON(), nullable=True),
        sa.Column("published_at", sa.DateTime(), nullable=False),
        sa.Column("error_message", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.ForeignKeyConstraint(["article_draft_id"], ["article_drafts.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_publish_logs_article_draft_id", "publish_logs", ["article_draft_id"])


def downgrade() -> None:
    op.drop_index("ix_publish_logs_article_draft_id", table_name="publish_logs")
    op.drop_table("publish_logs")
    op.drop_index("ix_notifications_status", table_name="notifications")
    op.drop_index("ix_notifications_article_draft_id", table_name="notifications")
    op.drop_table("notifications")
    op.drop_index("ix_article_reviews_article_draft_id", table_name="article_reviews")
    op.drop_table("article_reviews")
    op.drop_index("ix_article_drafts_status", table_name="article_drafts")
    op.drop_index("ix_article_drafts_slug", table_name="article_drafts")
    op.drop_index("ix_article_drafts_instagram_post_id", table_name="article_drafts")
    op.drop_table("article_drafts")
    op.drop_index("ix_instagram_posts_status", table_name="instagram_posts")
    op.drop_index("ix_instagram_posts_instagram_media_id", table_name="instagram_posts")
    op.drop_table("instagram_posts")
    op.drop_index("ix_agent_runs_agent_name", table_name="agent_runs")
    op.drop_table("agent_runs")
