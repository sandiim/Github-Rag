from app.rag.chunker import chunk_file


def test_chunks_preserve_inclusive_source_line_ranges() -> None:
    content = "\n".join(f"line {number}" for number in range(1, 6))

    chunks = chunk_file(content, max_lines=2, overlap_lines=0)

    assert [(chunk.start_line, chunk.end_line) for chunk in chunks] == [
        (1, 2),
        (3, 4),
        (5, 5),
    ]
    assert [chunk.text for chunk in chunks] == ["line 1\nline 2", "line 3\nline 4", "line 5"]


def test_chunks_overlap_without_changing_original_line_numbers() -> None:
    content = "\n".join(f"line {number}" for number in range(1, 6))

    chunks = chunk_file(content, max_lines=3, overlap_lines=1)

    assert [(chunk.start_line, chunk.end_line) for chunk in chunks] == [(1, 3), (3, 5)]
