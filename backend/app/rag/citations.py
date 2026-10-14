"""Commit-pinned GitHub citation helpers."""

import re

from app.rag.retrieval import RetrievedChunk


MARKER = re.compile(r"\[(\d+)\]")


def build_github_url(
    full_name: str,
    commit_sha: str,
    path: str,
    start_line: int,
    end_line: int,
) -> str:
    """Build a stable GitHub blob URL for an inclusive source range."""

    return f"https://github.com/{full_name}/blob/{commit_sha}/{path}#L{start_line}-L{end_line}"


def resolve_citation_markers(answer: str, context: list[RetrievedChunk]) -> tuple[str, list[int]]:
    """Replace valid model markers with stable file spans and report the used chunks."""

    used: list[int] = []

    def replace(match: re.Match[str]) -> str:
        index = int(match.group(1)) - 1
        if not 0 <= index < len(context):
            return match.group(0)
        if index not in used:
            used.append(index)
        chunk = context[index]
        return f"[{chunk.path}:{chunk.start_line}-{chunk.end_line}]"

    return MARKER.sub(replace, answer), used
