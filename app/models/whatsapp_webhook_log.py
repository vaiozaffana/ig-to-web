"""
Model untuk mencatat webhook events dari WhatsApp.
Berguna untuk debugging dan audit trail.
"""
from datetime import UTC, datetime

from sqlalchemy import JSON
from sqlmodel import Column, Field, SQLModel


class WhatsAppWebhookLog(SQLModel, table=True):
    """Log semua webhook events dari WhatsApp Cloud API."""
    
    __tablename__ = "whatsapp_webhook_logs"
    
    id: int | None = Field(default=None, primary_key=True)
    
    # Metadata webhook
    webhook_type: str = Field(description="Type: verification | message | status | other")
    object_type: str | None = Field(default=None, description="object field dari payload")
    
    # Raw payload
    payload: dict[str, object] = Field(sa_column=Column(JSON), description="Full JSON payload")
    
    # Status processing
    processed: bool = Field(default=False, description="Sudah diproses atau belum")
    error_message: str | None = Field(default=None, description="Error jika processing gagal")
    
    # Timestamps
    received_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Waktu webhook diterima"
    )
    processed_at: datetime | None = Field(default=None, description="Waktu processing selesai")
