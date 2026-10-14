"""Public API request and response schemas."""

from pydantic import BaseModel, HttpUrl


class CreateRepositoryRequest(BaseModel):
    url: HttpUrl


class RepositoryResponse(BaseModel):
    id: str
    name: str
    status: str
    ingestion: "IngestionResponse | None" = None


class IngestionResponse(BaseModel):
    id: str
    state: str
    stage: str | None
    completed_files: int
    total_files: int | None
    error_message: str | None


class CitationResponse(BaseModel):
    path: str
    start_line: int
    end_line: int
    url: str


class MessageResponse(BaseModel):
    role: str
    content: str
    citations: list[CitationResponse]


class ConversationResponse(BaseModel):
    title: str
    messages: list[MessageResponse]


class ChatRequest(BaseModel):
    question: str


class ChatResponse(BaseModel):
    text: str
    citations: list[CitationResponse]
