from __future__ import annotations

import uuid

from sqlalchemy.dialects import postgresql

from app.persistence.models import Chunk, Repository, SourceFile
from app.rag.retrieval import RetrievalService, RetrievedChunk, fuse_ranked_chunks


def chunk(path: str, start: int, end: int, score: float = 0.9) -> RetrievedChunk:
    return RetrievedChunk(path, f"{path}:{start}", start, end, "commit-123", score)


def test_keyword_hit_surfaces_exact_file_missing_from_vector_results() -> None:
    semantic = [chunk("README.md", 1, 80), chunk("notes.md", 1, 80)]
    keyword = [chunk("src/authenticate_user.py", 1, 30)]

    result = fuse_ranked_chunks(semantic, keyword, limit=2)

    assert [item.path for item in result] == ["src/authenticate_user.py", "README.md"]


def test_chunk_found_by_both_searches_ranks_above_single_source_hits() -> None:
    shared = chunk("src/auth.py", 1, 80)
    semantic = [chunk("src/other.py", 1, 80), shared]
    keyword = [chunk("docs/auth.md", 1, 80), shared]

    result = fuse_ranked_chunks(semantic, keyword, limit=3)

    assert result[0].path == "src/auth.py"
    assert len(result) == 3


def test_different_files_are_preferred_before_third_chunk_from_same_file() -> None:
    semantic = [
        chunk("report.Rmd", 1, 80),
        chunk("report.Rmd", 71, 150),
        chunk("report.Rmd", 141, 220),
        chunk("src/model.py", 1, 80),
    ]

    result = fuse_ranked_chunks(semantic, [], limit=3)

    assert [item.path for item in result] == ["report.Rmd", "report.Rmd", "src/model.py"]


def test_fusion_deduplicates_same_source_span_and_returns_fewer_when_needed() -> None:
    shared = chunk("src/app.py", 1, 80)

    result = fuse_ranked_chunks([shared], [shared], limit=6)

    assert len(result) == 1
    assert result[0].path == "src/app.py"


def test_retrieve_combines_scoped_vector_and_keyword_candidates() -> None:
    repository_id = uuid.uuid4()
    version = uuid.uuid4()
    repository = Repository(id=repository_id, active_index_version=version)
    readme = SourceFile(path="README.md", commit_sha="commit-123")
    auth = SourceFile(path="src/authenticate_user.py", commit_sha="commit-123")
    vector_chunk = Chunk(text="overview", start_line=1, end_line=20)
    keyword_chunk = Chunk(text="authenticate_user", start_line=1, end_line=20)

    class Result:
        def __init__(self, rows: list[tuple[Chunk, SourceFile, float]]) -> None:
            self.rows = rows

        def all(self) -> list[tuple[Chunk, SourceFile, float]]:
            return self.rows

    class SessionStub:
        def __init__(self) -> None:
            self.queries = []

        def get(self, model, key):
            assert model is Repository and key == repository_id
            return repository

        def execute(self, statement):
            self.queries.append(statement)
            if len(self.queries) == 1:
                return Result([(vector_chunk, readme, 0.1)])
            return Result([(keyword_chunk, auth, 0.8)])

    class EmbeddingsStub:
        def embed(self, texts: list[str]) -> list[list[float]]:
            assert texts == ["Where is authenticate_user?"]
            return [[0.5] * 768]

    session = SessionStub()
    result = RetrievalService(session, EmbeddingsStub()).retrieve(
        repository_id, "Where is authenticate_user?", limit=2
    )

    assert [item.path for item in result] == ["src/authenticate_user.py", "README.md"]
    assert len(session.queries) == 2
    for query in session.queries:
        compiled = query.compile(dialect=postgresql.dialect())
        assert "repository_id" in str(compiled)
        assert "index_version" in str(compiled)
        assert repository_id in compiled.params.values()
        assert version in compiled.params.values()
    keyword_sql = str(session.queries[1].compile(dialect=postgresql.dialect()))
    assert "regexp_replace" in keyword_sql  # Separate path segments before tokenization.
    assert "setweight" in keyword_sql  # Give an exact filename more weight than incidental text.
    assert "'A'" in keyword_sql and "'D'" in keyword_sql  # PostgreSQL expects internal char literals.
