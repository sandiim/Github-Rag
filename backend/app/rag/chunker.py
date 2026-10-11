"""Line-preserving source chunk creation."""

from dataclasses import dataclass


@dataclass(frozen=True)
class ChunkDraft:
    """A text chunk with its inclusive source line range."""

    text: str
    start_line: int
    end_line: int


def chunk_file(content: str, max_lines: int = 80, overlap_lines: int = 10) -> list[ChunkDraft]:
    """Split source text into overlapping chunks without losing line positions."""

    if max_lines < 1:
        raise ValueError("max_lines must be at least one")
    if overlap_lines < 0 or overlap_lines >= max_lines:
        raise ValueError("overlap_lines must be non-negative and smaller than max_lines")
    if not content:
        return []

    lines = content.splitlines()
    step = max_lines - overlap_lines
    chunks: list[ChunkDraft] = []
    start = 0
    while start < len(lines):
        end = min(start + max_lines, len(lines))
        chunks.append(
            ChunkDraft(
                text="\n".join(lines[start:end]),
                start_line=start + 1,
                end_line=end,
            )
        )
        if end == len(lines):
            break
        start += step
    return chunks
