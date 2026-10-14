"""Repository HTTP endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.dependencies import get_chat_service, get_repository_service
from app.github.client import GitHubRateLimitError, InvalidRepositoryUrl
from app.api.schemas import (
    ChatRequest, ChatResponse, CitationResponse, ConversationResponse, CreateRepositoryRequest,
    MessageResponse, RebuildResponse, RepositoryResponse,
)
from app.services.chat import ChatService
from app.services.repositories import RepositoryService, RepositorySummary

router = APIRouter(prefix="/repositories", tags=["repositories"])


@router.post("", response_model=RepositoryResponse, status_code=status.HTTP_201_CREATED)
def create_repository(
    request: CreateRepositoryRequest,
    service: RepositoryService = Depends(get_repository_service),
) -> RepositoryResponse:
    try:
        return _repository_response(service.create(str(request.url)))
    except GitHubRateLimitError as error:
        raise HTTPException(status_code=429, detail=str(error)) from error
    except InvalidRepositoryUrl as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


@router.get("", response_model=list[RepositoryResponse])
def list_repositories(
    service: RepositoryService = Depends(get_repository_service),
) -> list[RepositoryResponse]:
    return [_repository_response(repository) for repository in service.list()]


def _repository_response(repository: RepositorySummary) -> RepositoryResponse:
    return RepositoryResponse(id=repository.id, name=repository.name, status=repository.status)


@router.get("/{repository_id}", response_model=RepositoryResponse)
def get_repository(repository_id: str, service: RepositoryService = Depends(get_repository_service)) -> RepositoryResponse:
    try:
        return _repository_response(service.get(repository_id))
    except LookupError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@router.post("/{repository_id}/rebuild", response_model=RebuildResponse)
def rebuild_repository(repository_id: str, service: RepositoryService = Depends(get_repository_service)) -> RebuildResponse:
    try:
        result = service.rebuild(repository_id)
    except GitHubRateLimitError as error:
        raise HTTPException(status_code=429, detail=str(error)) from error
    except LookupError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    return RebuildResponse(changed=result.changed, status=result.status)


@router.get("/{repository_id}/conversation", response_model=ConversationResponse)
def get_conversation(repository_id: str, service: RepositoryService = Depends(get_repository_service)) -> ConversationResponse:
    try:
        conversation = service.conversation(repository_id)
    except LookupError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    return ConversationResponse(
        title=conversation.title,
        messages=[
            MessageResponse(
                role=message.role,
                content=message.content,
                citations=[CitationResponse(**citation.__dict__) for citation in message.citations],
            )
            for message in conversation.messages
        ],
    )


@router.post("/{repository_id}/chat", response_model=ChatResponse)
def ask_question(
    repository_id: str,
    request: ChatRequest,
    service: ChatService = Depends(get_chat_service),
) -> ChatResponse:
    try:
        answer = service.ask(repository_id, request.question)
    except LookupError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    return ChatResponse(
        text=answer.text,
        citations=[CitationResponse(**citation.__dict__) for citation in answer.citations],
    )
