from __future__ import annotations

import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, UUID4, field_validator

from paperlens.core.config import settings
from paperlens.core.enums import QATurnStatus


class CreateQAConversationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")


class CreateQATurnRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    question: str
    output_language: Literal["zh", "en"] = "zh"
    client_request_id: UUID4
    current_page: int | None = Field(default=None, ge=1)

    @field_validator("question", mode="before")
    @classmethod
    def validate_question(cls, value):
        if not isinstance(value, str):
            return value
        stripped = value.strip()
        if not stripped:
            raise ValueError("question must not be blank")
        if len(stripped) > settings.qa_question_max_chars:
            raise ValueError("question is too long")
        return stripped


class QACitationItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    evidence_id: UUID4
    sequence: int = Field(ge=1)
    page_number: int = Field(ge=1)
    evidence_type: str
    quoted_text: str
    char_start: int | None = Field(default=None, ge=0)
    char_end: int | None = Field(default=None, ge=0)


class QATurnResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID4
    conversation_id: UUID4
    sequence: int = Field(ge=1)
    question: str
    output_language: Literal["zh", "en"]
    status: QATurnStatus
    duplicate: bool = False
    answer: str | None
    grounded: bool | None
    error_message: Literal["论文问答生成失败，请稍后重试"] | None
    citations: list[QACitationItem] | None
    created_at: datetime.datetime
    completed_at: datetime.datetime | None


class QAConversationResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID4
    paper_id: UUID4
    created_at: datetime.datetime
    updated_at: datetime.datetime
    turns: list[QATurnResponse] | None = None
    total: int = Field(default=0, ge=0)
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)


class QAConversationListItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID4
    paper_id: UUID4
    created_at: datetime.datetime
    updated_at: datetime.datetime
    turn_count: int = Field(ge=0)
    last_question_preview: str | None
    last_status: QATurnStatus | None


class QAConversationListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[QAConversationListItem]
    total: int = Field(ge=0)
    page: int = Field(ge=1)
    page_size: int = Field(ge=1, le=100)
