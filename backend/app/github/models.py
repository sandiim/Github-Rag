"""GitHub adapter value objects."""

from dataclasses import dataclass


@dataclass(frozen=True)
class RepositoryReference:
    """The owner and name of a GitHub repository."""

    owner: str
    name: str


@dataclass(frozen=True)
class GitHubRepository:
    """A repository resolved to its default branch and indexed commit."""

    reference: RepositoryReference
    default_branch: str
    commit_sha: str


@dataclass(frozen=True)
class GitHubFile:
    """A decoded GitHub blob ready for file filtering."""

    path: str
    content: str
    sha: str
