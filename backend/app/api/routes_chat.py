"""Chat API routes."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import select

from app.api.routes_role_profiles import SessionDep
from app.api.schemas import (
    ChatConversationCreateRequest,
    ChatConversationListResponse,
    ChatConversationResponse,
    ChatMessageCreateRequest,
    ChatMessageCreateResponse,
    ChatMessageListResponse,
)
from app.db.models import ChatConversation, RoleProfile
from app.services.chat_service import ChatService


router = APIRouter(prefix="/chat", tags=["chat"])
chat_service = ChatService()


async def _require_profile(session: SessionDep, role_profile_id: str) -> None:
    result = await session.execute(
        select(RoleProfile.id).where(RoleProfile.id == role_profile_id).limit(1)
    )
    if result.scalar_one_or_none() is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="role profile not found",
        )


async def _require_conversation(
    session: SessionDep,
    conversation_id: str,
) -> ChatConversation:
    result = await session.execute(
        select(ChatConversation).where(ChatConversation.id == conversation_id).limit(1)
    )
    conversation = result.scalar_one_or_none()
    if conversation is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="conversation not found",
        )
    return conversation


@router.post(
    "/conversations",
    response_model=ChatConversationResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_conversation(
    request: ChatConversationCreateRequest,
    session: SessionDep,
) -> ChatConversation:
    role_profile_id = str(request.role_profile_id)
    await _require_profile(session, role_profile_id)
    return await chat_service.create_conversation(
        session,
        role_profile_id=role_profile_id,
        title=request.title,
    )


@router.get("/conversations", response_model=ChatConversationListResponse)
async def list_conversations(
    role_profile_id: UUID,
    session: SessionDep,
    limit: int = Query(default=50, ge=1, le=100),
) -> ChatConversationListResponse:
    conversations = await chat_service.list_conversations(
        session,
        role_profile_id=str(role_profile_id),
        limit=limit,
    )
    return ChatConversationListResponse(conversations=conversations)


@router.get(
    "/conversations/{conversation_id}/messages",
    response_model=ChatMessageListResponse,
)
async def list_messages(
    conversation_id: UUID,
    session: SessionDep,
    limit: int = Query(default=200, ge=1, le=500),
) -> ChatMessageListResponse:
    await _require_conversation(session, str(conversation_id))
    messages = await chat_service.list_messages(
        session,
        conversation_id=str(conversation_id),
        limit=limit,
    )
    return ChatMessageListResponse(messages=messages)


@router.post(
    "/conversations/{conversation_id}/messages",
    response_model=ChatMessageCreateResponse,
    status_code=status.HTTP_201_CREATED,
)
async def append_user_message(
    conversation_id: UUID,
    request: ChatMessageCreateRequest,
    session: SessionDep,
) -> ChatMessageCreateResponse:
    await _require_conversation(session, str(conversation_id))
    message = await chat_service.append_message(
        session,
        conversation_id=str(conversation_id),
        role="user",
        content=request.content,
        metadata={"source": "chat"},
    )
    return ChatMessageCreateResponse(
        message=message,
        stream_url=(
            f"/api/chat/conversations/{conversation_id}/stream"
            f"?after_message_id={message.id}"
        ),
    )
