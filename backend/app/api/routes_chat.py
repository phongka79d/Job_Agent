"""Chat API routes."""

from __future__ import annotations

import json
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select

from app.agents.chat_graph import run_chat_turn
from app.api.routes_role_profiles import SessionDep
from app.api.schemas import (
    AgentToolCallListResponse,
    ChatConversationCreateRequest,
    ChatConversationListResponse,
    ChatConversationResponse,
    ChatMessageCreateRequest,
    ChatMessageCreateResponse,
    ChatMessageListResponse,
)
from app.db.models import ChatConversation, ChatMessage, RoleProfile
from app.services.agent_event_service import AgentEventService
from app.services.chat_memory_service import ChatMemoryService
from app.services.chat_service import ChatService


router = APIRouter(prefix="/chat", tags=["chat"])
chat_service = ChatService()
agent_event_service = AgentEventService()
memory_service = ChatMemoryService()


def _sse_event(event_type: str, payload: dict[str, object]) -> str:
    return f"event: {event_type}\ndata: {json.dumps(payload, separators=(',', ':'))}\n\n"


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


async def _require_message_in_conversation(
    session: SessionDep,
    conversation_id: str,
    message_id: str,
) -> ChatMessage:
    result = await session.execute(
        select(ChatMessage)
        .where(
            ChatMessage.id == message_id,
            ChatMessage.conversation_id == conversation_id,
        )
        .limit(1)
    )
    message = result.scalar_one_or_none()
    if message is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="message not found",
        )
    return message


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


@router.get(
    "/conversations/{conversation_id}/tool-calls",
    response_model=AgentToolCallListResponse,
)
async def list_tool_calls(
    conversation_id: UUID,
    session: SessionDep,
) -> AgentToolCallListResponse:
    await _require_conversation(session, str(conversation_id))
    tool_calls = await agent_event_service.list_tool_calls(
        session,
        conversation_id=str(conversation_id),
    )
    return AgentToolCallListResponse(tool_calls=tool_calls)


@router.get("/conversations/{conversation_id}/stream")
async def stream_conversation_events(
    conversation_id: UUID,
    after_message_id: UUID,
    session: SessionDep,
) -> StreamingResponse:
    conversation = await _require_conversation(session, str(conversation_id))
    user_message = await _require_message_in_conversation(
        session,
        str(conversation_id),
        str(after_message_id),
    )

    async def event_generator():
        yield _sse_event(
            "message_started",
            {
                "conversation_id": str(conversation_id),
                "after_message_id": str(after_message_id),
            },
        )
        memory = await memory_service.assemble(
            session,
            conversation_id=str(conversation_id),
            current_user_message=user_message.content,
        )
        result = await run_chat_turn(
            {
                "conversation_id": str(conversation_id),
                "role_profile_id": conversation.role_profile_id,
                "user_message": user_message.content,
                "working_memory": memory.context_text,
                "tool_results": [],
            },
            llm_client=None,
            tool_registry=None,
        )
        assistant = await chat_service.append_message(
            session,
            conversation_id=str(conversation_id),
            role="assistant",
            content=result["final_answer"],
            metadata={
                "source": "chat_agent",
                "memory_tokens": memory.total_tokens,
                "dropped_memory_keys": memory.dropped_keys,
            },
        )
        yield _sse_event("assistant_delta", {"content": assistant.content})
        yield _sse_event(
            "message_completed",
            {
                "conversation_id": str(conversation_id),
                "after_message_id": str(after_message_id),
                "message_id": assistant.id,
            },
        )

    return StreamingResponse(event_generator(), media_type="text/event-stream")


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
