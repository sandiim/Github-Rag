from app.persistence.models import Chunk


def test_chunk_stores_a_768_dimension_embedding() -> None:
    embedding_type = Chunk.__table__.c.embedding.type

    assert embedding_type.dim == 768
