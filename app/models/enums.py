from enum import StrEnum


class WorkflowStatus(StrEnum):
    INSTAGRAM_COLLECTED = "instagram_collected"
    ASSET_DOWNLOADED = "asset_downloaded"
    DRAFT_GENERATING = "draft_generating"
    DRAFT_GENERATED = "draft_generated"
    WAITING_REVIEW = "waiting_review"
    APPROVED = "approved"
    PUBLISHING = "publishing"
    PUBLISHED = "published"
    REJECTED = "rejected"
    NEEDS_REVISION = "needs_revision"
    FETCH_FAILED = "fetch_failed"
    GENERATION_FAILED = "generation_failed"
    NOTIFICATION_FAILED = "notification_failed"
    PUBLISH_FAILED = "publish_failed"


class ReviewAction(StrEnum):
    APPROVE = "approve"
    REJECT = "reject"
    REVISE = "revise"
    EDIT_MANUAL = "edit_manual"
    PUBLISH = "publish"


class AgentRunStatus(StrEnum):
    SUCCESS = "success"
    ERROR = "error"


class NotificationChannel(StrEnum):
    WHATSAPP = "whatsapp"
    TELEGRAM = "telegram"


class NotificationStatus(StrEnum):
    PENDING = "pending"
    SENT = "sent"
    FAILED = "failed"


class PublishLogStatus(StrEnum):
    SUCCESS = "success"
    FAILED = "failed"


class ComplianceVerdict(StrEnum):
    PASS = "pass"
    NEEDS_REVISION = "needs_revision"
    FAIL = "fail"
