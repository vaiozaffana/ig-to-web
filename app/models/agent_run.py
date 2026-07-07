from datetime import UTC, datetime
from typing import Any

from sqlalchemy import JSON, Column
from sqlmodel import Field, SQLModel

from app.models.enums import AgentRunStatus


class AgentRun(SQLModel, table=True):
    __tablename__ = "agent_runs"

    id: int | None = Field(default=None, primary_key=True)
    agent_name: str = Field(index=True)
    input_json: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))
    output_json: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))
    status: AgentRunStatus
    error_message: str | None = None
    started_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    finished_at: datetime | None = None
