from __future__ import annotations

import datetime
import unicodedata

from pydantic import BaseModel, ConfigDict, Field, UUID4, field_validator, model_validator

from paperlens.core.enums import AnchorType, HighlightColor, MasteryStatus, ReadingStatus


def _clean_text(value, *, field_name: str, maximum: int, blank_to_none: bool = False, multiline: bool = True):
    if value is None:
        return None
    if not isinstance(value, str):
        return value
    cleaned = value.strip()
    if not cleaned:
        if blank_to_none:
            return None
        raise ValueError(f"{field_name} must not be blank")
    if len(cleaned) > maximum:
        raise ValueError(f"{field_name} exceeds {maximum} characters")
    allowed = {"\n", "\r", "\t"} if multiline else set()
    if any(unicodedata.category(char) == "Cc" and char not in allowed for char in cleaned):
        raise ValueError(f"{field_name} contains control characters")
    return cleaned


class PatchLibraryEntryRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reading_status: ReadingStatus | None = None
    favorite: bool | None = None
    collection_name: str | None = None

    @field_validator("collection_name", mode="before")
    @classmethod
    def clean_collection_name(cls, value):
        return _clean_text(value, field_name="collection_name", maximum=100, blank_to_none=True, multiline=False)

    @model_validator(mode="after")
    def validate_patch(self):
        if not self.model_fields_set:
            raise ValueError("at least one field is required")
        for field_name in ("reading_status", "favorite"):
            if field_name in self.model_fields_set and getattr(self, field_name) is None:
                raise ValueError(f"{field_name} must not be null")
        return self


class PatchReadingProgressRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    page_number: int = Field(ge=1)


class LibraryPaperItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    paper_id: UUID4
    title: str
    filename: str
    page_count: int | None
    status: str
    created_at: datetime.datetime
    reading_status: ReadingStatus
    favorite: bool
    collection_name: str | None
    last_page: int | None
    furthest_page: int | None
    progress_percent: int = Field(ge=0, le=100)
    last_read_at: datetime.datetime | None
    completed_at: datetime.datetime | None
    updated_at: datetime.datetime
    highlight_count: int = Field(ge=0)
    bookmark_count: int = Field(ge=0)
    note_count: int = Field(ge=0)
    card_count: int = Field(ge=0)


class LibraryPaperListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[LibraryPaperItem]
    total: int = Field(ge=0)
    page: int = Field(ge=1)
    page_size: int = Field(ge=1, le=100)


class LibraryEntryResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    paper_id: UUID4
    reading_status: ReadingStatus
    favorite: bool
    collection_name: str | None
    last_page: int | None
    furthest_page: int | None
    last_read_at: datetime.datetime | None
    completed_at: datetime.datetime | None
    updated_at: datetime.datetime


class ReadingProgressResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    paper_id: UUID4
    reading_status: ReadingStatus
    last_page: int | None
    furthest_page: int | None
    progress_percent: int = Field(ge=0, le=100)
    last_read_at: datetime.datetime | None
    updated_at: datetime.datetime


class CreateHighlightRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    page_number: int = Field(ge=1)
    char_start: int = Field(ge=0)
    char_end: int = Field(gt=0)
    color: HighlightColor = HighlightColor.YELLOW

    @model_validator(mode="after")
    def validate_range(self):
        if self.char_end <= self.char_start:
            raise ValueError("char_end must be greater than char_start")
        return self


class HighlightResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID4
    paper_id: UUID4
    page_number: int = Field(ge=1)
    char_start: int = Field(ge=0)
    char_end: int = Field(gt=0)
    quoted_text: str
    color: HighlightColor
    created_at: datetime.datetime
    updated_at: datetime.datetime
    duplicate: bool = False


class HighlightListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[HighlightResponse]
    total: int = Field(ge=0)
    page: int = Field(ge=1)
    page_size: int = Field(ge=1, le=100)


class CreateBookmarkRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    page_number: int = Field(ge=1)
    label: str | None = None

    @field_validator("label", mode="before")
    @classmethod
    def clean_label(cls, value):
        return _clean_text(value, field_name="label", maximum=100, blank_to_none=True, multiline=False)


class BookmarkResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID4
    paper_id: UUID4
    page_number: int = Field(ge=1)
    label: str | None
    created_at: datetime.datetime
    duplicate: bool = False


class BookmarkListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[BookmarkResponse]
    total: int = Field(ge=0)
    page: int = Field(ge=1)
    page_size: int = Field(ge=1, le=100)


class CreateNoteRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    anchor_type: AnchorType
    page_number: int | None = Field(default=None, ge=1)
    highlight_id: UUID4 | None = None
    content: str

    @field_validator("content", mode="before")
    @classmethod
    def clean_content(cls, value):
        return _clean_text(value, field_name="content", maximum=20000)

    @model_validator(mode="after")
    def validate_anchor(self):
        valid = (
            self.anchor_type == AnchorType.PAPER and self.page_number is None and self.highlight_id is None
        ) or (
            self.anchor_type == AnchorType.PAGE and self.page_number is not None and self.highlight_id is None
        ) or (
            self.anchor_type == AnchorType.HIGHLIGHT and self.page_number is None and self.highlight_id is not None
        )
        if not valid:
            raise ValueError("anchor fields do not match anchor_type")
        return self


class PatchNoteRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    content: str

    @field_validator("content", mode="before")
    @classmethod
    def clean_content(cls, value):
        return _clean_text(value, field_name="content", maximum=20000)


class NoteResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID4
    paper_id: UUID4
    anchor_type: AnchorType
    page_number: int | None
    highlight_id: UUID4 | None
    content: str
    created_at: datetime.datetime
    updated_at: datetime.datetime


class NoteListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[NoteResponse]
    total: int = Field(ge=0)
    page: int = Field(ge=1)
    page_size: int = Field(ge=1, le=100)


class CreateKnowledgeCardRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_note_id: UUID4 | None = None
    source_highlight_id: UUID4 | None = None
    front: str
    back: str

    @field_validator("front", mode="before")
    @classmethod
    def clean_front(cls, value):
        return _clean_text(value, field_name="front", maximum=2000)

    @field_validator("back", mode="before")
    @classmethod
    def clean_back(cls, value):
        return _clean_text(value, field_name="back", maximum=10000)

    @model_validator(mode="after")
    def validate_source(self):
        if self.source_note_id is not None and self.source_highlight_id is not None:
            raise ValueError("only one card source is allowed")
        return self


class PatchKnowledgeCardRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    front: str | None = None
    back: str | None = None
    mastery_status: MasteryStatus | None = None
    archived: bool | None = None

    @field_validator("front", mode="before")
    @classmethod
    def clean_front(cls, value):
        return _clean_text(value, field_name="front", maximum=2000)

    @field_validator("back", mode="before")
    @classmethod
    def clean_back(cls, value):
        return _clean_text(value, field_name="back", maximum=10000)

    @model_validator(mode="after")
    def validate_patch(self):
        if not self.model_fields_set:
            raise ValueError("at least one field is required")
        for field_name in self.model_fields_set:
            if getattr(self, field_name) is None:
                raise ValueError(f"{field_name} must not be null")
        return self


class KnowledgeCardResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID4
    paper_id: UUID4
    source_note_id: UUID4 | None
    source_highlight_id: UUID4 | None
    front: str
    back: str
    mastery_status: MasteryStatus
    last_reviewed_at: datetime.datetime | None
    archived: bool
    created_at: datetime.datetime
    updated_at: datetime.datetime


class KnowledgeCardListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[KnowledgeCardResponse]
    total: int = Field(ge=0)
    page: int = Field(ge=1)
    page_size: int = Field(ge=1, le=100)
