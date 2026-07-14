from __future__ import annotations

import logging
import os
import tempfile
import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, Path, Query, UploadFile
from pydantic import UUID4
from sqlalchemy.orm import Session

from paperlens.core.config import settings
from paperlens.core.database import get_db
from paperlens.core.deps import get_current_user, get_current_user_id
from paperlens.core.enums import PaperStatus
from paperlens.core.errors import AppError
from paperlens.models.models import (
    Paper,
    PaperPage,
    PaperSection,
    PaperChunk,
    PaperTable,
    Evidence,
    User,
)
from paperlens.schemas.paper import (
    PaperUploadResponse,
    PaperListResponse,
    PaperListItem,
    PaperDetail,
    PageDetail,
    SectionListResponse,
    SectionItem,
    EvidenceListResponse,
    EvidenceItem,
)
from paperlens.services.pdf_parser import compute_file_hash, check_pdf_magic, parse_pdf
from paperlens.utils.storage import get_storage, _sanitize_filename

logger = logging.getLogger(__name__)

router = APIRouter()

_SAFE_ERROR_MAP = {
    "OCR_NOT_SUPPORTED": "扫描型 PDF 暂不支持，请上传可提取文本的 PDF",
}


def _safe_error_message(exc: Exception) -> str:
    msg = str(exc)
    for key, safe_msg in _SAFE_ERROR_MAP.items():
        if key in msg:
            return safe_msg
    if "页数超出限制" in msg:
        return "PDF 页数超过系统限制"
    return "论文解析失败，请稍后重试或重新上传"



def _check_paper_owner(paper: Paper | None, user_id: str) -> Paper:
    if paper is None:
        raise AppError("NOT_FOUND", "论文不存在", 404)
    if paper.user_id != user_id:
        raise AppError("FORBIDDEN", "无权访问该论文", 403)
    return paper


@router.post("/papers/upload", response_model=PaperUploadResponse, status_code=201)
async def upload_paper(
    file: UploadFile,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    tmp_path: str | None = None
    tmp_transferred = False
    storage = None
    storage_key: str | None = None
    storage_touched = False
    storage_transferred = False
    paper_added = False
    try:

        raw_filename = file.filename or "unknown.pdf"
        filename = _sanitize_filename(raw_filename)

        if not filename.lower().endswith(".pdf"):
            raise AppError("INVALID_FILE_TYPE", "仅支持 PDF 文件", 415)

        max_bytes = settings.max_pdf_size_mb * 1024 * 1024
        total = 0
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            tmp_path = tmp.name
            while True:
                chunk = await file.read(1024 * 1024)
                if not chunk:
                    break
                total += len(chunk)
                if total > max_bytes:
                    raise AppError("FILE_TOO_LARGE", f"文件超过 {settings.max_pdf_size_mb}MB 限制", 413)
                tmp.write(chunk)

        if not check_pdf_magic(tmp_path):
            raise AppError("INVALID_FILE_TYPE", "文件不是有效的 PDF", 415)

        file_hash = compute_file_hash(tmp_path)
        paper_id = str(uuid.uuid4())

        storage = get_storage()
        storage_key = storage.build_key("papers", paper_id, filename)
        storage_touched = True
        storage.save(storage_key, tmp_path)

        paper = Paper(
            id=paper_id,
            title=filename.rsplit(".", 1)[0],
            filename=filename,
            storage_key=storage_key,
            file_size=total,
            file_hash=file_hash,
            status=PaperStatus.PROCESSING,
            user_id=user_id,
        )
        db.add(paper)
        paper_added = True
        db.flush()
        db.refresh(paper)

        response = PaperUploadResponse(
            id=paper.id,
            title=paper.title,
            filename=paper.filename,
            file_size=paper.file_size,
            status=paper.status,
            created_at=paper.created_at,
        )

        background_tasks.add_task(_process_paper, paper_id, tmp_path)
        db.commit()

        tmp_transferred = True
        storage_transferred = True
        return response
    except AppError:
        raise
    except Exception:
        logger.exception("上传论文失败")
        raise AppError("UPLOAD_FAILED", "上传失败，请稍后重试", 500)
    finally:
        if paper_added and not storage_transferred:
            try:
                db.rollback()
            except Exception:
                logger.warning("Failed to roll back upload database transaction", exc_info=True)
        if storage_touched and not storage_transferred and storage is not None and storage_key:
            try:
                storage.delete(storage_key)
            except Exception:
                logger.warning("Failed to delete unowned storage object %s", storage_key, exc_info=True)
        if tmp_path and not tmp_transferred and os.path.exists(tmp_path):
            try:
                os.unlink(tmp_path)
            except Exception:
                logger.warning("Failed to delete upload temporary file %s", tmp_path, exc_info=True)
        try:
            await file.close()
        except Exception:
            logger.warning("Failed to close uploaded file", exc_info=True)


def _process_paper(paper_id: str, tmp_path: str):
    from paperlens.core.database import SessionLocal

    db = SessionLocal()
    try:
        paper = db.get(Paper, paper_id)
        if paper is None:
            return

        try:
            result = parse_pdf(paper_id, tmp_path)

            for p in result["pages"]:
                db.add(PaperPage(
                    paper_id=paper_id,
                    page_number=p["page_number"],
                    text_content=p["text_content"],
                    normalized_text_content=p.get("normalized_text_content"),
                    width=p["width"],
                    height=p["height"],
                ))

            section_id_map = {}
            for s in result["sections"]:
                sec = PaperSection(
                    paper_id=paper_id,
                    section_type=s["section_type"],
                    title=s["title"],
                    level=s["level"],
                    sequence=s["sequence"],
                    start_page=s["start_page"],
                    end_page=s["end_page"],
                    text_content=s.get("text_content", ""),
                )
                db.add(sec)
                db.flush()
                section_id_map[s["sequence"]] = sec.id

            chunk_id_map = {}
            for c in result["chunks"]:
                sec_id = section_id_map.get(c.get("section_sequence"))
                chunk = PaperChunk(
                    paper_id=paper_id,
                    section_id=sec_id,
                    chunk_index=c["chunk_index"],
                    content=c["content"],
                    char_count=c["char_count"],
                    page_numbers=c.get("page_numbers"),
                )
                db.add(chunk)
                db.flush()
                chunk_id_map[c["chunk_index"]] = chunk.id

            for t in result["tables"]:
                try:
                    table_obj = PaperTable(
                        paper_id=paper_id,
                        page_number=t["page_number"],
                        table_index=t["table_index"],
                        caption=t.get("caption"),
                        bbox_x0=t.get("bbox_x0"),
                        bbox_y0=t.get("bbox_y0"),
                        bbox_x1=t.get("bbox_x1"),
                        bbox_y1=t.get("bbox_y1"),
                        structured_data=t.get("structured_data"),
                        raw_text=t.get("raw_text"),
                    )
                    if table_obj.bbox_x0 is not None and table_obj.bbox_x1 is not None:
                        if table_obj.bbox_x1 < table_obj.bbox_x0:
                            table_obj.bbox_x1, table_obj.bbox_x0 = table_obj.bbox_x0, table_obj.bbox_x1
                    if table_obj.bbox_y0 is not None and table_obj.bbox_y1 is not None:
                        if table_obj.bbox_y1 < table_obj.bbox_y0:
                            table_obj.bbox_y1, table_obj.bbox_y0 = table_obj.bbox_y0, table_obj.bbox_y1
                    with db.begin_nested():
                        db.add(table_obj)
                        db.flush()
                except Exception:
                    logger.warning(
                        "表格提取异常 paper_id=%s page=%d table_idx=%d",
                        paper_id, t["page_number"], t["table_index"],
                        exc_info=True,
                    )

            for e in result["evidences"]:
                sec_id = None
                if e.get("chunk_index") is not None and e["chunk_index"] in chunk_id_map:
                    chunk_obj = db.get(PaperChunk, chunk_id_map[e["chunk_index"]])
                    if chunk_obj and chunk_obj.section_id:
                        sec_id = chunk_obj.section_id
                db.add(Evidence(
                    paper_id=paper_id,
                    chunk_id=chunk_id_map.get(e.get("chunk_index")),
                    section_id=sec_id,
                    quoted_text=e["quoted_text"],
                    page_number=e["page_number"],
                    bbox_x0=e.get("bbox_x0"),
                    bbox_y0=e.get("bbox_y0"),
                    bbox_x1=e.get("bbox_x1"),
                    bbox_y1=e.get("bbox_y1"),
                    char_start=e.get("char_start"),
                    char_end=e.get("char_end"),
                    evidence_type=e["evidence_type"],
                ))

            paper.page_count = len(result["pages"])
            paper.status = PaperStatus.PARSED
            paper.error_message = None
            db.commit()
        except Exception as e:
            logger.exception("解析论文失败 paper_id=%s", paper_id)
            db.rollback()
            paper.status = PaperStatus.FAILED
            paper.error_message = _safe_error_message(e)
            db.commit()
    finally:
        db.close()
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)


@router.get("/papers", response_model=PaperListResponse)
async def list_papers(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: PaperStatus | None = None,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):

    query = db.query(Paper).filter(Paper.user_id == user_id)
    if status:
        query = query.filter(Paper.status == status)
    total = query.count()
    items = query.order_by(Paper.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()
    return PaperListResponse(
        items=[PaperListItem(
            id=p.id, title=p.title, filename=p.filename,
            page_count=p.page_count, status=p.status, created_at=p.created_at,
        ) for p in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/papers/{paper_id}", response_model=PaperDetail)
async def get_paper(
    paper_id: UUID4 = Path(...),
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):

    paper = _check_paper_owner(db.get(Paper, str(paper_id)), user_id)
    return PaperDetail(
        id=paper.id, title=paper.title, filename=paper.filename,
        file_size=paper.file_size, page_count=paper.page_count,
        status=paper.status, error_message=paper.error_message,
        created_at=paper.created_at, updated_at=paper.updated_at,
    )


@router.get("/papers/{paper_id}/pages/{page_number}", response_model=PageDetail)
async def get_page(
    paper_id: UUID4 = Path(...),
    page_number: int = Path(..., ge=1),
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    _check_paper_owner(db.get(Paper, str(paper_id)), user_id)
    page = db.query(PaperPage).filter(
        PaperPage.paper_id == str(paper_id), PaperPage.page_number == page_number
    ).first()
    if page is None:
        raise AppError("NOT_FOUND", "页面不存在", 404)
    return PageDetail(
        id=page.id, page_number=page.page_number,
        text_content=page.text_content, normalized_text_content=page.normalized_text_content,
        width=page.width, height=page.height,
    )


@router.get("/papers/{paper_id}/sections", response_model=SectionListResponse)
async def list_sections(
    paper_id: UUID4 = Path(...),
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    _check_paper_owner(db.get(Paper, str(paper_id)), user_id)
    sections = db.query(PaperSection).filter(
        PaperSection.paper_id == str(paper_id)
    ).order_by(PaperSection.sequence).all()
    return SectionListResponse(
        sections=[SectionItem(
            id=s.id, section_type=s.section_type, title=s.title,
            level=s.level, sequence=s.sequence, start_page=s.start_page,
            end_page=s.end_page, text_content=s.text_content,
        ) for s in sections]
    )


@router.get("/papers/{paper_id}/evidences", response_model=EvidenceListResponse)
async def list_evidences(
    paper_id: UUID4 = Path(...),
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    _check_paper_owner(db.get(Paper, str(paper_id)), user_id)
    evidences = db.query(Evidence).filter(
        Evidence.paper_id == str(paper_id)
    ).order_by(Evidence.page_number, Evidence.created_at).all()
    return EvidenceListResponse(
        evidences=[EvidenceItem(
            id=e.id, quoted_text=e.quoted_text, page_number=e.page_number,
            bbox_x0=e.bbox_x0, bbox_y0=e.bbox_y0, bbox_x1=e.bbox_x1, bbox_y1=e.bbox_y1,
            char_start=e.char_start, char_end=e.char_end, evidence_type=e.evidence_type,
            section_id=e.section_id, chunk_id=e.chunk_id,
        ) for e in evidences]
    )


@router.get("/evidences/{evidence_id}", response_model=EvidenceItem)
async def get_evidence(
    evidence_id: UUID4 = Path(...),
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):

    evidence = db.get(Evidence, str(evidence_id))
    if evidence is None:
        raise AppError("NOT_FOUND", "证据不存在", 404)
    _check_paper_owner(db.get(Paper, evidence.paper_id), user_id)
    return EvidenceItem(
        id=evidence.id, quoted_text=evidence.quoted_text, page_number=evidence.page_number,
        bbox_x0=evidence.bbox_x0, bbox_y0=evidence.bbox_y0, bbox_x1=evidence.bbox_x1, bbox_y1=evidence.bbox_y1,
        char_start=evidence.char_start, char_end=evidence.char_end, evidence_type=evidence.evidence_type,
        section_id=evidence.section_id, chunk_id=evidence.chunk_id,
    )
