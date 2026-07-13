"""
Pydantic schemas untuk WhatsApp webhook payload.
Dokumentasi: https://developers.facebook.com/docs/whatsapp/cloud-api/webhooks/components
"""
from pydantic import BaseModel, Field


class WhatsAppMessageValue(BaseModel):
    """Struktur value dari webhook message."""
    messaging_product: str
    metadata: dict[str, object]
    contacts: list[dict[str, object]] | None = None
    messages: list[dict[str, object]] | None = None
    statuses: list[dict[str, object]] | None = None


class WhatsAppWebhookChange(BaseModel):
    """Struktur change dari webhook."""
    value: WhatsAppMessageValue
    field: str


class WhatsAppWebhookEntry(BaseModel):
    """Struktur entry dari webhook."""
    id: str
    changes: list[WhatsAppWebhookChange]


class WhatsAppWebhookPayload(BaseModel):
    """Root payload dari WhatsApp webhook."""
    object_type: str = Field(alias="object")
    entry: list[WhatsAppWebhookEntry]


class WebhookVerificationResponse(BaseModel):
    """Response untuk webhook verification (mode=subscribe)."""
    hub_mode: str = Field(alias="hub.mode")
    hub_verify_token: str = Field(alias="hub.verify_token")
    hub_challenge: str = Field(alias="hub.challenge")
