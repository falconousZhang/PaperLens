import pytest
import logging
from tests.conftest import create_test_pdf, create_scanned_pdf, create_multipage_pdf, create_special_chars_pdf, create_duplicate_prefix_pdf
from paperlens.services.pdf_parser import parse_pdf, check_pdf_magic, compute_file_hash, _normalize_whitespace


def test_check_pdf_magic_valid(tmp_path):
    path = create_test_pdf("hello", tmp_path=str(tmp_path))
    assert check_pdf_magic(path) is True


def test_check_pdf_magic_invalid(tmp_path):
    path = tmp_path / "not.pdf"
    path.write_text("not a pdf")
    assert check_pdf_magic(str(path)) is False


def test_compute_file_hash(tmp_path):
    path = create_test_pdf("hello", tmp_path=str(tmp_path))
    h = compute_file_hash(path)
    assert len(h) == 64
    assert h == compute_file_hash(path)


def test_parse_pdf_pages(tmp_path):
    path = create_test_pdf("Abstract: This paper presents a novel method.", pages=3, tmp_path=str(tmp_path))
    result = parse_pdf("test-id", path)
    assert len(result["pages"]) == 3
    assert result["pages"][0]["page_number"] == 1
    assert result["pages"][0]["width"] > 0
    assert result["pages"][0]["height"] > 0


def test_parse_pdf_ocr_not_supported(tmp_path):
    path = create_scanned_pdf(str(tmp_path))
    with pytest.raises(ValueError, match="OCR_NOT_SUPPORTED"):
        parse_pdf("test-id", path)


def test_parse_pdf_sections(tmp_path):
    path = create_test_pdf(
        "Abstract: test abstract.\nIntroduction: test intro.\nMethod: test method.\nConclusion: test conclusion.",
        tmp_path=str(tmp_path),
    )
    result = parse_pdf("test-id", path)
    assert len(result["sections"]) >= 1


def test_parse_pdf_chunks_deterministic(tmp_path):
    path = create_test_pdf("This is a test paper about machine learning. " * 50, tmp_path=str(tmp_path))
    r1 = parse_pdf("test-id", path)
    r2 = parse_pdf("test-id", path)
    assert len(r1["chunks"]) == len(r2["chunks"])
    for c1, c2 in zip(r1["chunks"], r2["chunks"]):
        assert c1["content"] == c2["content"]


def test_parse_pdf_evidences(tmp_path):
    path = create_test_pdf("Our model achieves 95% accuracy on the benchmark.", tmp_path=str(tmp_path))
    result = parse_pdf("test-id", path)
    assert result["evidences"], "Must produce at least one evidence"
    for e in result["evidences"]:
        assert e["quoted_text"]
        assert e["page_number"] >= 1


def test_evidence_page_local_no_cross_page(tmp_path):
    path = create_multipage_pdf(
        ["Page one content about neural networks.", "Page two content about transformers."],
        str(tmp_path),
    )
    result = parse_pdf("test-id", path)
    assert result["evidences"], "Must produce at least one evidence"
    for e in result["evidences"]:
        assert e["page_number"] in (1, 2)
        page_idx = e["page_number"] - 1
        normalized_page = result["pages"][page_idx]["normalized_text_content"] or ""
        if e.get("char_start") is not None and e.get("char_end") is not None:
            assert e["char_start"] >= 0
            assert e["char_end"] <= len(normalized_page)
            assert e["char_end"] >= e["char_start"]


def test_evidence_bbox_within_page(tmp_path):
    path = create_test_pdf("Testing bbox coordinates for evidence.", tmp_path=str(tmp_path))
    result = parse_pdf("test-id", path)
    assert result["evidences"], "Must produce at least one evidence"
    for e in result["evidences"]:
        if e.get("bbox_x0") is not None:
            page_idx = e["page_number"] - 1
            page_info = result["pages"][page_idx]
            assert page_info is not None
            assert e["bbox_x0"] >= 0
            assert e["bbox_y0"] >= 0
            assert e["bbox_x1"] <= page_info["width"]
            assert e["bbox_y1"] <= page_info["height"]


def test_evidence_char_range_within_page(tmp_path):
    path = create_test_pdf("Character range validation test for evidence generation.", tmp_path=str(tmp_path))
    result = parse_pdf("test-id", path)
    assert result["evidences"], "Must produce at least one evidence"
    for e in result["evidences"]:
        if e.get("char_start") is not None and e.get("char_end") is not None:
            page_idx = e["page_number"] - 1
            normalized = result["pages"][page_idx]["normalized_text_content"] or ""
            assert e["char_start"] >= 0
            assert e["char_end"] <= len(normalized)
            extracted = normalized[e["char_start"]:e["char_end"]]
            assert extracted == e["quoted_text"]


def test_evidence_associated_with_chunk_and_section(tmp_path):
    path = create_test_pdf("Testing evidence association with chunks and sections.", tmp_path=str(tmp_path))
    result = parse_pdf("test-id", path)
    assert result["evidences"], "Must produce at least one evidence"
    chunk_indices = {c["chunk_index"] for c in result["chunks"]}
    for e in result["evidences"]:
        if e.get("chunk_index") is not None:
            assert e["chunk_index"] in chunk_indices


def test_parse_pdf_closes_doc_on_exception(tmp_path):
    import fitz
    path = create_test_pdf("hello", tmp_path=str(tmp_path))
    with pytest.raises(ValueError, match="OCR_NOT_SUPPORTED"):
        parse_pdf("test-id", create_scanned_pdf(str(tmp_path)))
    doc = fitz.open(path)
    assert len(doc) > 0
    doc.close()


def test_parse_pdf_includes_normalized_text_content(tmp_path):
    path = create_test_pdf("This is a test paper about machine learning.", tmp_path=str(tmp_path))
    result = parse_pdf("test-id", path)
    for p in result["pages"]:
        assert "normalized_text_content" in p
        assert p["normalized_text_content"] is not None
        assert _normalize_whitespace(p["text_content"] or "") == p["normalized_text_content"]


def test_evidence_char_range_matches_normalized_text(tmp_path):
    path = create_test_pdf("Character range validation test for evidence generation.", tmp_path=str(tmp_path))
    result = parse_pdf("test-id", path)
    assert result["evidences"], "Must produce at least one evidence"
    for e in result["evidences"]:
        if e.get("char_start") is not None and e.get("char_end") is not None:
            page_idx = e["page_number"] - 1
            normalized = result["pages"][page_idx]["normalized_text_content"] or ""
            extracted = normalized[e["char_start"]:e["char_end"]]
            assert extracted == e["quoted_text"]


def test_evidence_char_range_null_on_mismatch(caplog, tmp_path):
    from unittest.mock import patch
    path = create_test_pdf("Testing null char range fallback.", tmp_path=str(tmp_path))
    with caplog.at_level(logging.WARNING):
        original_parse = parse_pdf

        def _parse_with_mismatched_normalized(paper_id, pdf_path):
            result = original_parse(paper_id, pdf_path)
            for p in result["pages"]:
                p["normalized_text_content"] = "GARBAGE_TEXT_THAT_WONT_MATCH_ANYTHING"
            from paperlens.services.pdf_parser import _generate_evidences, fitz
            doc = fitz.open(pdf_path)
            try:
                result["evidences"] = _generate_evidences(doc, result["pages"], result["chunks"], result["sections"])
            finally:
                doc.close()
            return result

        with patch("paperlens.services.pdf_parser.parse_pdf", side_effect=_parse_with_mismatched_normalized):
            from paperlens.services.pdf_parser import parse_pdf as patched_parse
            result = patched_parse("test-id", path)
    for e in result["evidences"]:
        assert e["char_start"] is None, f"Expected char_start=None, got {e['char_start']}"
        assert e["char_end"] is None, f"Expected char_end=None, got {e['char_end']}"
    assert any("not found in normalized" in r.message.lower() for r in caplog.records)


def test_special_chars_pdf(tmp_path):
    path = create_special_chars_pdf(str(tmp_path))
    result = parse_pdf("test-id", path)
    assert len(result["pages"]) >= 1
    assert result["evidences"], "Must produce at least one evidence"
    for e in result["evidences"]:
        if e.get("char_start") is not None and e.get("char_end") is not None:
            page_idx = e["page_number"] - 1
            normalized = result["pages"][page_idx]["normalized_text_content"] or ""
            extracted = normalized[e["char_start"]:e["char_end"]]
            assert extracted == e["quoted_text"]


def test_duplicate_prefix_pdf(tmp_path):
    path = create_duplicate_prefix_pdf(str(tmp_path))
    result = parse_pdf("test-id", path)
    assert len(result["evidences"]) >= 2
    page_texts = set()
    for e in result["evidences"]:
        page_idx = e["page_number"] - 1
        normalized = result["pages"][page_idx]["normalized_text_content"] or ""
        if e.get("char_start") is not None and e.get("char_end") is not None:
            extracted = normalized[e["char_start"]:e["char_end"]]
            assert extracted == e["quoted_text"]
            page_texts.add(extracted)
    assert len(page_texts) >= 2
