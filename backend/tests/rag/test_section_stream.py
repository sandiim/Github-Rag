from app.rag.section_stream import CompletedSection, DraftDelta, SectionStream


def test_section_stream_emits_readable_text_before_section_is_complete() -> None:
    parser = SectionStream()

    first = parser.feed('{"sections":[{"text":"Hel')
    second = parser.feed('lo\\nworld","source_ids":[1]}]}')

    assert first == [DraftDelta("Hel")]
    assert second == [
        DraftDelta("lo\nworld"),
        CompletedSection({"text": "Hello\nworld", "source_ids": [1]}),
    ]
    assert parser.raw == '{"sections":[{"text":"Hello\\nworld","source_ids":[1]}]}'


def test_section_stream_handles_escaped_quotes_and_split_unicode_escape() -> None:
    parser = SectionStream()

    first = parser.feed('{"sections":[{"text":"A \\')
    second = parser.feed('"quote\\" and caf\\u00')
    third = parser.feed('e9","source_ids":[1]}]}')

    assert first == [DraftDelta("A ")]
    assert DraftDelta('"quote" and caf') in second
    assert third == [
        DraftDelta("é"),
        CompletedSection({"text": 'A "quote" and café', "source_ids": [1]}),
    ]


def test_section_stream_emits_each_paragraph_checkpoint() -> None:
    parser = SectionStream()

    events = parser.feed(
        '{"sections":[{"text":"First","source_ids":[1]},'
        '{"text":"Second","source_ids":[2]}]}'
    )

    assert [event.section["text"] for event in events if isinstance(event, CompletedSection)] == [
        "First", "Second"
    ]


def test_section_stream_waits_for_complete_unicode_surrogate_pair() -> None:
    parser = SectionStream()

    first = parser.feed('{"sections":[{"text":"Smile \\ud83d')
    second = parser.feed('\\ude00","source_ids":[1]}]}')

    assert first == [DraftDelta("Smile ")]
    assert second == [
        DraftDelta("😀"),
        CompletedSection({"text": "Smile 😀", "source_ids": [1]}),
    ]
