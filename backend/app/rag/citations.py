"""Commit-pinned GitHub citation helpers."""


def build_github_url(
    full_name: str,
    commit_sha: str,
    path: str,
    start_line: int,
    end_line: int,
) -> str:
    """Build a stable GitHub blob URL for an inclusive source range."""

    return f"https://github.com/{full_name}/blob/{commit_sha}/{path}#L{start_line}-L{end_line}"
