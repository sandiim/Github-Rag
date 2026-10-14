"""GitHub URL validation and authenticated API access."""

from urllib.parse import urlparse

import base64
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

import httpx

from app.github.models import GitHubFile, GitHubRepository, RepositoryReference
from app.rag.file_filter import MAX_FILE_BYTES, should_index


class InvalidRepositoryUrl(ValueError):
    """Raised when a value is not an HTTPS GitHub repository URL."""


class GitHubRateLimitError(Exception):
    """Raised when GitHub's API quota is exhausted."""


def parse_repository_url(url: str) -> RepositoryReference:
    """Extract a GitHub repository reference from a canonical HTTPS URL."""

    parsed = urlparse(url)
    parts = [part for part in parsed.path.split("/") if part]
    if parsed.scheme != "https" or parsed.netloc != "github.com" or len(parts) != 2:
        raise InvalidRepositoryUrl("Expected https://github.com/<owner>/<repository>")
    return RepositoryReference(owner=parts[0], name=parts[1].removesuffix(".git"))


class GitHubClient:
    """Small authenticated adapter for GitHub's repository API."""

    def __init__(self, token: str, transport: httpx.BaseTransport | None = None) -> None:
        self._client = httpx.Client(
            base_url="https://api.github.com",
            headers={"Accept": "application/vnd.github+json", "Authorization": f"Bearer {token}"},
            transport=transport,
            follow_redirects=True,
            timeout=httpx.Timeout(60.0, connect=10.0),
        )

    def resolve(self, url: str) -> GitHubRepository:
        """Resolve a URL to the current default-branch commit."""

        reference = parse_repository_url(url)
        repository_response = self._get(f"/repos/{reference.owner}/{reference.name}")
        repository_data = repository_response.json()
        full_name = repository_data.get("full_name", "")
        if full_name.count("/") == 1:
            owner, name = full_name.split("/", 1)
            reference = RepositoryReference(owner=owner, name=name)
        default_branch = repository_data["default_branch"]
        commit_response = self._get(
            f"/repos/{reference.owner}/{reference.name}/commits/{default_branch}"
        )
        return GitHubRepository(
            reference=reference,
            default_branch=default_branch,
            commit_sha=commit_response.json()["sha"],
        )

    def list_files(self, repository: GitHubRepository) -> list[GitHubFile]:
        """Download decoded blobs from a repository's indexed commit tree."""

        reference = repository.reference
        tree_response = self._get(
            f"/repos/{reference.owner}/{reference.name}/git/trees/{repository.commit_sha}",
            params={"recursive": "1"},
        )
        candidates = [
            item
            for item in tree_response.json()["tree"]
            if item["type"] == "blob"
            and item.get("size", 0) <= MAX_FILE_BYTES
            and should_index(item["path"], "")
        ]

        def download(item: dict[str, object]) -> GitHubFile | None:
            blob_response = self._get(
                f"/repos/{reference.owner}/{reference.name}/git/blobs/{item['sha']}"
            )
            blob = blob_response.json()
            if blob.get("encoding") != "base64":
                return None
            content = base64.b64decode(blob["content"]).decode("utf-8", errors="replace")
            return GitHubFile(path=str(item["path"]), content=content, sha=str(item["sha"]))

        files: list[GitHubFile] = []
        with ThreadPoolExecutor(max_workers=min(8, len(candidates) or 1)) as executor:
            for start in range(0, len(candidates), 8):
                files.extend(
                    file for file in executor.map(download, candidates[start:start + 8])
                    if file is not None
                )
        return files

    def _get(self, path: str, **kwargs: object) -> httpx.Response:
        response = self._client.get(path, **kwargs)
        if response.status_code in (403, 429) and response.headers.get("x-ratelimit-remaining") == "0":
            reset = response.headers.get("x-ratelimit-reset", "")
            retry = " after GitHub resets the quota"
            if reset.isdigit():
                retry += f" at {datetime.fromtimestamp(int(reset), timezone.utc):%Y-%m-%d %H:%M UTC}"
            raise GitHubRateLimitError(f"GitHub API rate limit reached; retry{retry}.")
        response.raise_for_status()
        return response
