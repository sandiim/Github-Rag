import pytest
import httpx

from app.github.client import GitHubClient, InvalidRepositoryUrl, parse_repository_url


def test_parse_repository_url_extracts_owner_and_name() -> None:
    reference = parse_repository_url("https://github.com/acme/widgets")

    assert reference.owner == "acme"
    assert reference.name == "widgets"


@pytest.mark.parametrize("url", ["https://gitlab.com/acme/widgets", "https://github.com/acme", "not-a-url"])
def test_parse_repository_url_rejects_non_github_repository_urls(url: str) -> None:
    with pytest.raises(InvalidRepositoryUrl):
        parse_repository_url(url)


def test_resolve_reads_default_branch_and_commit_sha() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/repos/acme/widgets":
            return httpx.Response(200, json={"default_branch": "main"})
        if request.url.path == "/repos/acme/widgets/commits/main":
            return httpx.Response(200, json={"sha": "abc123"})
        return httpx.Response(404)

    client = GitHubClient("token", transport=httpx.MockTransport(handler))
    repository = client.resolve("https://github.com/acme/widgets")

    assert repository.default_branch == "main"
    assert repository.commit_sha == "abc123"


def test_list_files_downloads_repository_text_blobs() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/repos/acme/widgets":
            return httpx.Response(200, json={"default_branch": "main"})
        if request.url.path == "/repos/acme/widgets/commits/main":
            return httpx.Response(200, json={"sha": "abc123"})
        if request.url.path == "/repos/acme/widgets/git/trees/abc123":
            return httpx.Response(
                200,
                json={"tree": [{"type": "blob", "path": "src/app.py", "sha": "blob-sha"}]},
            )
        if request.url.path == "/repos/acme/widgets/git/blobs/blob-sha":
            return httpx.Response(200, json={"encoding": "base64", "content": "cHJpbnQoJ2hpJyk="})
        return httpx.Response(404)

    client = GitHubClient("token", transport=httpx.MockTransport(handler))
    repository = client.resolve("https://github.com/acme/widgets")
    files = client.list_files(repository)

    assert [(file.path, file.content, file.sha) for file in files] == [
        ("src/app.py", "print('hi')", "blob-sha")
    ]
