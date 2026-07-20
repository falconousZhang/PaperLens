from __future__ import annotations

from datetime import datetime
from pydantic import BaseModel, Field


class PaperUploadResponse(BaseModel):
    id: str
    title: str
    filename: str
    file_size: int
    status: str
    created_at: datetime


class PaperListItem(BaseModel):
    id: str
    title: str
    filename: str
    page_count: int | None
    status: str
    created_at: datetime


class PaperListResponse(BaseModel):
    items: list[PaperListItem]
    total: int
    page: int
    page_size: int


class PaperDetail(BaseModel):
    id: str
    title: str
    filename: str
    file_size: int
    page_count: int | None
    status: str
    error_message: str | None = None
    created_at: datetime
    updated_at: datetime


class PageDetail(BaseModel):
    id: str
    page_number: int
    text_content: str | None
    normalized_text_content: str | None = None
    width: float | None
    height: float | None


class PageTextWord(BaseModel):
    text: str
    x0: float
    y0: float
    x1: float
    y1: float
    char_start: int = Field(ge=0)
    char_end: int = Field(ge=1)


class PageTextLayerResponse(BaseModel):
    page_number: int = Field(ge=1)
    width: float = Field(gt=0)
    height: float = Field(gt=0)
    words: list[PageTextWord]


class SectionItem(BaseModel):
    id: str
    section_type: str
    title: str | None
    level: int
    sequence: int
    start_page: int | None
    end_page: int | None
    text_content: str | None


class SectionListResponse(BaseModel):
    sections: list[SectionItem]


class PaperOutlineItem(BaseModel):
    title: str
    level: int
    page_number: int


class PaperOutlineResponse(BaseModel):
    items: list[PaperOutlineItem]


class EvidenceItem(BaseModel):
    id: str
    quoted_text: str
    page_number: int
    bbox_x0: float | None
    bbox_y0: float | None
    bbox_x1: float | None
    bbox_y1: float | None
    char_start: int | None
    char_end: int | None
    evidence_type: str
    section_id: str | None
    chunk_id: str | None


class EvidenceListResponse(BaseModel):
    evidences: list[EvidenceItem]
