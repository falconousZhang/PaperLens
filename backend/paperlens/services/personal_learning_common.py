from __future__ import annotations

import logging
import unicodedata

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from paperlens.core.enums import PaperStatus
from paperlens.core.errors import AppError
from paperlens.models.models import Paper, PaperPage


logger = logging.getLogger(__name__)


def owned_paper(db: Session, paper_id: str, user_id: str, *, require_parsed: bool = False) -> Paper:
    paper = db.query(Paper).filter(Paper.id == paper_id, Paper.user_id == user_id).one_or_none()
    if paper is None:
        raise AppError("NOT_FOUND", "论文不存在", 404)
    if require_parsed and paper.status != PaperStatus.PARSED:
        raise AppError("PAPER_NOT_READY", "论文尚未解析完成", 409)
    return paper


def owned_page(db: Session, paper: Paper, page_number: int) -> PaperPage:
    if not paper.page_count or page_number < 1 or page_number > paper.page_count:
        raise AppError("VALIDATION_ERROR", "页码超出范围", 422)
    page = db.query(PaperPage).filter(PaperPage.paper_id == paper.id, PaperPage.page_number == page_number).one_or_none()
    if page is None:
        raise AppError("NOT_FOUND", "页面不存在", 404)
    return page


def clean_user_text(value: str, field_name: str, maximum: int) -> str:
    cleaned = value.strip()
    if not cleaned:
        raise AppError("VALIDATION_ERROR", f"{field_name}不能为空白", 422)
    if len(cleaned) > maximum:
        raise AppError("VALIDATION_ERROR", f"{field_name}超过长度限制", 422)
    if any(unicodedata.category(char) == "Cc" and char not in {"\n", "\r", "\t"} for char in cleaned):
        raise AppError("VALIDATION_ERROR", f"{field_name}包含控制字符", 422)
    return cleaned


def commit_or_conflict(db: Session, *, stage: str, paper_id: str) -> None:
    try:
        db.commit()
    except SQLAlchemyError as exc:
        db.rollback()
        logger.error("personal_learning_write_failed stage=%s paper_id=%s error_type=%s", stage, paper_id, type(exc).__name__)
        raise AppError("WRITE_CONFLICT", "学习记录保存冲突，请重试", 409) from None
