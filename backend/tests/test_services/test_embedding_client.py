import math
import pytest

from paperlens.services.embedding_client import (
    MockEmbeddingClient,
    EmbeddingError,
    validate_embeddings,
    cosine_similarity,
)


class TestMockEmbeddingClient:
    def test_same_text_same_vector(self):
        c = MockEmbeddingClient()
        r1 = c.embed(["hello world"])
        r2 = c.embed(["hello world"])
        assert r1 == r2

    def test_different_text_different_vector(self):
        c = MockEmbeddingClient()
        r1 = c.embed(["methodology approach"])
        r2 = c.embed(["novelty innovation"])
        assert r1 != r2

    def test_dimension_fixed(self):
        c = MockEmbeddingClient(dim=20)
        r = c.embed(["test"])
        assert len(r[0]) == 20

    def test_output_count_matches_input(self):
        c = MockEmbeddingClient()
        r = c.embed(["a", "b", "c"])
        assert len(r) == 3

    def test_vectors_finite(self):
        c = MockEmbeddingClient()
        r = c.embed(["test text"])
        for v in r[0]:
            assert math.isfinite(v)

    def test_vectors_nonzero_norm(self):
        c = MockEmbeddingClient()
        r = c.embed(["test"])
        norm = math.sqrt(sum(v * v for v in r[0]))
        assert norm > 0

    def test_vectors_normalized(self):
        c = MockEmbeddingClient()
        r = c.embed(["test"])
        norm = math.sqrt(sum(v * v for v in r[0]))
        assert abs(norm - 1.0) < 1e-10

    def test_cross_instance_stable(self):
        r1 = MockEmbeddingClient().embed(["methodology"])
        r2 = MockEmbeddingClient().embed(["methodology"])
        assert r1 == r2

    @pytest.mark.parametrize("dim", [0, -1, True, 1.5])
    def test_invalid_dimension_rejected(self, dim):
        with pytest.raises(EmbeddingError, match="positive integer"):
            MockEmbeddingClient(dim=dim)

    def test_empty_input_rejected(self):
        c = MockEmbeddingClient()
        with pytest.raises(EmbeddingError, match="non-empty"):
            c.embed([])

    def test_empty_text_rejected(self):
        c = MockEmbeddingClient()
        with pytest.raises(EmbeddingError, match="non-empty"):
            c.embed([""])

    def test_vocabulary_affects_ranking(self):
        c = MockEmbeddingClient()
        soundness_vec = c.embed(["soundness methodology reliability"])[0]
        novelty_vec = c.embed(["novelty innovation originality"])[0]
        soundness_query = c.embed(["methodology soundness reliability rigorous"])[0]
        novelty_query = c.embed(["novelty innovation originality new"])[0]

        sim_ss = cosine_similarity(soundness_query, soundness_vec)
        sim_sn = cosine_similarity(soundness_query, novelty_vec)
        assert sim_ss > sim_sn

        sim_nn = cosine_similarity(novelty_query, novelty_vec)
        sim_ns = cosine_similarity(novelty_query, soundness_vec)
        assert sim_nn > sim_ns

    def test_chinese_terms_affect_ranking(self):
        client = MockEmbeddingClient()
        query = client.embed(["方法论 可靠性 实验设置"])[0]
        relevant = client.embed(["本文详细说明方法论与实验设置，结果具有可靠性"])[0]
        unrelated = client.embed(["文章重点讨论写作表达和段落组织"])[0]
        assert cosine_similarity(query, relevant) > cosine_similarity(query, unrelated)


class TestValidateEmbeddings:
    def test_valid_passes(self):
        validate_embeddings([[1.0, 0.0], [0.0, 1.0]], 2)

    def test_count_mismatch_rejected(self):
        with pytest.raises(EmbeddingError, match="count mismatch"):
            validate_embeddings([[1.0]], 2)

    def test_dimension_mismatch_rejected(self):
        with pytest.raises(EmbeddingError, match="dimension mismatch"):
            validate_embeddings([[1.0], [1.0, 2.0]], 2)

    def test_empty_vector_rejected(self):
        with pytest.raises(EmbeddingError, match="empty"):
            validate_embeddings([[]], 1)

    def test_nan_rejected(self):
        with pytest.raises(EmbeddingError, match="NaN"):
            validate_embeddings([[float("nan")]], 1)

    def test_inf_rejected(self):
        with pytest.raises(EmbeddingError, match="Infinity"):
            validate_embeddings([[float("inf")]], 1)

    def test_boolean_rejected(self):
        with pytest.raises(EmbeddingError, match="boolean"):
            validate_embeddings([[True]], 1)

    def test_string_value_rejected(self):
        with pytest.raises(EmbeddingError, match="not a number"):
            validate_embeddings([["1.0"]], 1)

    def test_zero_norm_rejected(self):
        with pytest.raises(EmbeddingError, match="zero norm"):
            validate_embeddings([[0.0, 0.0]], 1)


class TestCosineSimilarity:
    def test_identical_vectors(self):
        v = [1.0, 0.0, 0.0]
        assert abs(cosine_similarity(v, v) - 1.0) < 1e-10

    def test_orthogonal_vectors(self):
        assert abs(cosine_similarity([1.0, 0.0], [0.0, 1.0])) < 1e-10

    def test_opposite_vectors(self):
        assert abs(cosine_similarity([1.0, 0.0], [-1.0, 0.0]) - (-1.0)) < 1e-10

    def test_dimension_mismatch_rejected(self):
        with pytest.raises(EmbeddingError, match="dimension mismatch"):
            cosine_similarity([1.0], [1.0, 2.0])

    def test_zero_norm_rejected(self):
        with pytest.raises(EmbeddingError, match="zero norm"):
            cosine_similarity([0.0], [1.0])

    def test_non_numeric_value_rejected(self):
        with pytest.raises(EmbeddingError, match="not a number"):
            cosine_similarity(["1.0"], [1.0])
