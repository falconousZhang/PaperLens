from paperlens.services.highlight_service import _compute_source_hash


def test_compute_source_hash_deterministic():
    h1 = _compute_source_hash("pid1", 1, "pagehash1", 0, 10, "hello")
    h2 = _compute_source_hash("pid1", 1, "pagehash1", 0, 10, "hello")
    assert h1 == h2
    assert len(h1) == 64


def test_compute_source_hash_different_inputs():
    h1 = _compute_source_hash("pid1", 1, "pagehash1", 0, 10, "hello")
    h2 = _compute_source_hash("pid2", 1, "pagehash1", 0, 10, "hello")
    h3 = _compute_source_hash("pid1", 2, "pagehash1", 0, 10, "hello")
    h4 = _compute_source_hash("pid1", 1, "pagehash2", 0, 10, "hello")
    h5 = _compute_source_hash("pid1", 1, "pagehash1", 5, 10, "hello")
    h6 = _compute_source_hash("pid1", 1, "pagehash1", 0, 15, "hello")
    h7 = _compute_source_hash("pid1", 1, "pagehash1", 0, 10, "world")
    assert len({h1, h2, h3, h4, h5, h6, h7}) == 7


def test_compute_source_hash_hex_format():
    h = _compute_source_hash("p", 1, "ph", 0, 1, "a")
    assert all(c in "0123456789abcdef" for c in h)


def test_compute_source_hash_unicode():
    h = _compute_source_hash("pid1", 1, "ph1", 0, 3, "你好")
    assert len(h) == 64
    h2 = _compute_source_hash("pid1", 1, "ph1", 0, 3, "你好")
    assert h == h2