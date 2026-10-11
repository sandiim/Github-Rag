from app.rag.citations import build_github_url


def test_citation_url_is_pinned_to_indexed_commit_and_lines() -> None:
    url = build_github_url("acme/widgets", "abc123", "src/app.py", 10, 14)

    assert url == "https://github.com/acme/widgets/blob/abc123/src/app.py#L10-L14"
