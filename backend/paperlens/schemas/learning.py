from __future__ import annotations

import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, UUID4, field_validator, model_validator

from paperlens.core.enums import LearningMode, LearningScopeType, LearningStatus


class CreateLearningExplanationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    mode: LearningMode
    scope_type: LearningScopeType
    output_language: Literal["zh", "en"] = "zh"
    section_id: UUID4 | None = None
    page_number: int | None = Field(default=None, ge=1)
    evidence_id: UUID4 | None = None
    selection_text: str | None = Field(default=None, max_length=5000)
    selection_start: int | None = Field(default=None, ge=0)
    selection_end: int | None = Field(default=None, ge=1)

    @field_validator("selection_text", mode="before")
    @classmethod
    def normalize_selection_text(cls, value):
        return value.strip() if isinstance(value, str) else value

    @model_validator(mode="after")
    def validate_scope(self):
        values = {
            LearningScopeType.SECTION: self.section_id,
            LearningScopeType.PAGE: self.page_number,
            LearningScopeType.EVIDENCE: self.evidence_id,
        }
        if values[self.scope_type] is None:
            raise ValueError(f"{self.scope_type.value} scope requires its matching identifier")
        populated = sum(value is not None for value in values.values())
        if populated != 1:
            raise ValueError("scope identifier must be strictly exclusive")
        if self.mode == LearningMode.EXPLAIN:
            if (
                self.scope_type != LearningScopeType.PAGE
                or not self.selection_text
                or self.selection_start is None
                or self.selection_end is None
                or self.selection_end <= self.selection_start
            ):
                raise ValueError("通俗解释必须包含当前页选中的文字")
        elif any(
            value is not None
            for value in (self.selection_text, self.selection_start, self.selection_end)
        ):
            raise ValueError("只有通俗解释可以提交选中文字")
        return self


class LearningTermItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    term: str
    explanation: str


class LearningCitationItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    evidence_id: UUID4
    sequence: int = Field(ge=1)
    page_number: int = Field(ge=1)
    evidence_type: str
    quoted_text: str
    char_start: int | None = Field(default=None, ge=0)
    char_end: int | None = Field(default=None, ge=0)


class LearningExplanationResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID4
    paper_id: UUID4
    mode: LearningMode
    scope_type: LearningScopeType
    output_language: Literal["zh", "en"]
    section_id: UUID4 | None
    page_number: int | None
    evidence_id: UUID4 | None
    selection_text: str | None
    selection_start: int | None
    selection_end: int | None
    status: LearningStatus
    duplicate: bool
    answer: str | None
    key_points: list[str] | None
    terms: list[LearningTermItem] | None
    error_message: Literal["学习解释生成失败，请稍后重试"] | None
    citations: list[LearningCitationItem] | None
    created_at: datetime.datetime
    completed_at: datetime.datetime | None


class LearningExplanationListItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID4
    paper_id: UUID4
    mode: LearningMode
    scope_type: LearningScopeType
    output_language: Literal["zh", "en"]
    section_id: UUID4 | None
    page_number: int | None
    evidence_id: UUID4 | None
    selection_start: int | None
    selection_end: int | None
    status: LearningStatus
    error_message: Literal["学习解释生成失败，请稍后重试"] | None
    created_at: datetime.datetime
    completed_at: datetime.datetime | None


class LearningExplanationListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[LearningExplanationListItem]
    total: int = Field(ge=0)
    page: int = Field(ge=1)
    page_size: int = Field(ge=1, le=100)
