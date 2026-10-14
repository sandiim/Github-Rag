import threading
import time

import pytest
import httpx

from app.github.client import GitHubClient, GitHubRateLimitError, InvalidRepositoryUrl, parse_repository_url
from app.github.models import GitHubRepository, RepositoryReference


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


def test_resolve_follows_github_repository_redirects() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/repos/acme/widgets":
            return httpx.Response(301, headers={"location": "/repositories/42"})
        if request.url.path == "/repositories/42":
            return httpx.Response(200, json={"default_branch": "main", "full_name": "acme/renamed"})
        if request.url.path == "/repos/acme/renamed/commits/main":
            return httpx.Response(200, json={"sha": "abc123"})
        return httpx.Response(404)

    client = GitHubClient("token", transport=httpx.MockTransport(handler))

    repository = client.resolve("https://github.com/acme/widgets")

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


def test_list_files_skips_non_indexable_tree_entries_before_downloading_blobs() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/repos/acme/widgets/git/trees/abc123":
            return httpx.Response(
                200,
                json={
                    "tree": [
                        {"type": "blob", "path": "package-lock.json", "sha": "ignored"},
                        {"type": "blob", "path": "venv/Lib/site-packages/pkg/module.py", "sha": "venv"},
                        {"type": "blob", "path": "mlruns/1/metadata.json", "sha": "mlruns"},
                        {"type": "blob", "path": "data/round.json", "sha": "data"},
                        {"type": "blob", "path": "src/app.py", "sha": "included"},
                    ]
                },
            )
        if request.url.path == "/repos/acme/widgets/git/blobs/included":
            return httpx.Response(200, json={"encoding": "base64", "content": "cHJpbnQoMSk="})
        raise AssertionError(f"Unexpected blob request: {request.url.path}")

    client = GitHubClient("token", transport=httpx.MockTransport(handler))
    repository = GitHubRepository(
        reference=RepositoryReference(owner="acme", name="widgets"),
        default_branch="main",
        commit_sha="abc123",
    )

    candidates = client.list_candidates(repository)
    files = client.list_files(repository)

    assert [candidate.path for candidate in candidates] == ["src/app.py"]
    assert [file.path for file in files] == ["src/app.py"]


def test_list_files_downloads_candidate_blobs_concurrently() -> None:
    active = 0
    maximum_active = 0
    lock = threading.Lock()

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal active, maximum_active
        if request.url.path.endswith("/git/trees/abc123"):
            return httpx.Response(
                200,
                json={
                    "tree": [
                        {"type": "blob", "path": f"src/{number}.py", "sha": f"blob-{number}"}
                        for number in range(4)
                    ]
                },
            )
        with lock:
            active += 1
            maximum_active = max(maximum_active, active)
        time.sleep(0.05)
        with lock:
            active -= 1
        return httpx.Response(200, json={"encoding": "base64", "content": "b25l"})

    client = GitHubClient("token", transport=httpx.MockTransport(handler))
    repository = GitHubRepository(
        reference=RepositoryReference(owner="acme", name="widgets"),
        default_branch="main",
        commit_sha="abc123",
    )

    files = client.list_files(repository)

    assert len(files) == 4
    assert maximum_active > 1


def test_list_files_reports_exhausted_github_quota() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/git/trees/abc123"):
            return httpx.Response(
                200,
                json={"tree": [{"type": "blob", "path": "src/app.py", "sha": "blob-1"}]},
            )
        return httpx.Response(
            403,
            headers={"x-ratelimit-remaining": "0", "x-ratelimit-reset": "1792015200"},
            json={"message": "API rate limit exceeded"},
        )

    client = GitHubClient("token", transport=httpx.MockTransport(handler))
    repository = GitHubRepository(
        reference=RepositoryReference(owner="acme", name="widgets"),
        default_branch="main",
        commit_sha="abc123",
    )

    with pytest.raises(GitHubRateLimitError, match="GitHub API rate limit"):
        client.list_files(repository)


def test_list_files_stops_scheduling_blobs_after_rate_limit() -> None:
    requests = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal requests
        if request.url.path.endswith("/git/trees/abc123"):
            return httpx.Response(
                200,
                json={"tree": [
                    {"type": "blob", "path": f"src/{number}.py", "sha": f"blob-{number}"}
                    for number in range(20)
                ]},
            )
        requests += 1
        return httpx.Response(403, headers={"x-ratelimit-remaining": "0"})

    client = GitHubClient("token", transport=httpx.MockTransport(handler))
    repository = GitHubRepository(
        reference=RepositoryReference(owner="acme", name="widgets"),
        default_branch="main",
        commit_sha="abc123",
    )

    with pytest.raises(GitHubRateLimitError):
        client.list_files(repository)

    assert requests <= 8
