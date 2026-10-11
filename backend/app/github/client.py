"""GitHub URL validation and authenticated API access."""

from urllib.parse import urlparse

import base64

import httpx

from app.github.models import GitHubFile, GitHubRepository, RepositoryReference


class InvalidRepositoryUrl(ValueError):
    """Raised when a value is not an HTTPS GitHub repository URL."""


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
        repository_response = self._client.get(f"/repos/{reference.owner}/{reference.name}")
        repository_response.raise_for_status()
        repository_data = repository_response.json()
        full_name = repository_data.get("full_name", "")
        if full_name.count("/") == 1:
            owner, name = full_name.split("/", 1)
            reference = RepositoryReference(owner=owner, name=name)
        default_branch = repository_data["default_branch"]
        commit_response = self._client.get(
            f"/repos/{reference.owner}/{reference.name}/commits/{default_branch}"
        )
        commit_response.raise_for_status()
        return GitHubRepository(
            reference=reference,
            default_branch=default_branch,
            commit_sha=commit_response.json()["sha"],
        )

    def list_files(self, repository: GitHubRepository) -> list[GitHubFile]:
        """Download decoded blobs from a repository's indexed commit tree."""

        reference = repository.reference
        tree_response = self._client.get(
            f"/repos/{reference.owner}/{reference.name}/git/trees/{repository.commit_sha}",
            params={"recursive": "1"},
        )
        tree_response.raise_for_status()
        files: list[GitHubFile] = []
        for item in tree_response.json()["tree"]:
            if item["type"] != "blob":
                continue
            blob_response = self._client.get(
                f"/repos/{reference.owner}/{reference.name}/git/blobs/{item['sha']}"
            )
            blob_response.raise_for_status()
            blob = blob_response.json()
            if blob.get("encoding") != "base64":
                continue
            content = base64.b64decode(blob["content"]).decode("utf-8", errors="replace")
            files.append(GitHubFile(path=item["path"], content=content, sha=item["sha"]))
        return files
