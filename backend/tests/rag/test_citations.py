from app.rag.citations import build_github_url, resolve_citation_markers
from app.rag.retrieval import RetrievedChunk


def test_citation_url_is_pinned_to_indexed_commit_and_lines() -> None:
    url = build_github_url("acme/widgets", "abc123", "src/app.py", 10, 14)

    assert url == "https://github.com/acme/widgets/blob/abc123/src/app.py#L10-L14"


def test_marker_resolution_uses_only_valid_referenced_chunks_in_first_use_order() -> None:
    chunks = [
        RetrievedChunk("src/app.py", "app = FastAPI()", 10, 14, "abc123", 0.9),
        RetrievedChunk("README.md", "Overview", 1, 8, "abc123", 0.8),
    ]

    text, used = resolve_citation_markers("Overview [2]. App [1][2]. Unknown [99].", chunks)

    assert text == "Overview [README.md:1-8]. App [src/app.py:10-14][README.md:1-8]. Unknown [99]."
    assert used == [1, 0]


def test_marker_resolution_leaves_an_unmarked_answer_unchanged_for_legacy_fallback() -> None:
    chunks = [RetrievedChunk("README.md", "Overview", 1, 8, "abc123", 0.8)]

    assert resolve_citation_markers("An overview without markers.", chunks) == (
        "An overview without markers.", []
    )
