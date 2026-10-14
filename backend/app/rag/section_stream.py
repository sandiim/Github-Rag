"""Extract readable section text from a streamed structured JSON answer."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass


@dataclass(frozen=True)
class DraftDelta:
    text: str


@dataclass(frozen=True)
class CompletedSection:
    section: dict[str, object]


class SectionStream:
    """Scan JSON fragments without exposing structural tokens to the browser."""

    def __init__(self) -> None:
        self.raw = ""
        self._depth = 0
        self._in_string = False
        self._escaped = False
        self._section_start: int | None = None
        self._emitted_chars = 0

    def feed(self, fragment: str) -> list[DraftDelta | CompletedSection]:
        events: list[DraftDelta | CompletedSection] = []
        for char in fragment:
            index = len(self.raw)
            self.raw += char
            if self._in_string:
                if self._escaped:
                    self._escaped = False
                elif char == "\\":
                    self._escaped = True
                elif char == '"':
                    self._in_string = False
                continue
            if char == '"':
                self._in_string = True
            elif char == "{":
                if self._depth == 1:
                    self._section_start = index
                    self._emitted_chars = 0
                self._depth += 1
            elif char == "}":
                if self._depth == 2 and self._section_start is not None:
                    events.extend(self._draft_delta())
                    section = json.loads(self.raw[self._section_start:index + 1])
                    if isinstance(section, dict):
                        events.append(CompletedSection(section))
                    self._section_start = None
                self._depth -= 1
        events.extend(self._draft_delta())
        return events

    def _draft_delta(self) -> list[DraftDelta]:
        if self._section_start is None:
            return []
        match = re.search(r'"text"\s*:\s*"', self.raw[self._section_start:])
        if match is None:
            return []
        start = self._section_start + match.end()
        end = len(self.raw)
        escaped = False
        for index in range(start, len(self.raw)):
            char = self.raw[index]
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                end = index
                break
        encoded = self.raw[start:end]
        for removed in range(min(6, len(encoded)) + 1):
            candidate = encoded[:len(encoded) - removed] if removed else encoded
            try:
                decoded = json.loads('"' + candidate + '"')
            except json.JSONDecodeError:
                continue
            if any(0xD800 <= ord(char) <= 0xDFFF for char in decoded):
                continue
            delta = decoded[self._emitted_chars:]
            self._emitted_chars = len(decoded)
            return [DraftDelta(delta)] if delta else []
        return []
