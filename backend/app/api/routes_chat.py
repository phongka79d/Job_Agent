"""Chat API routes."""

from __future__ import annotations

import json
import logging
import asyncio
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
from app.services.chat_llm_client import ChatLLMProviderError, OpenAIChatLLMClient
from app.services.chat_memory_service import ChatMemoryService
from app.services.chat_service import ChatService
from app.services.tool_registry import (
    ToolRegistry,
    ToolRequest,
    build_extract_job_from_text_handler,
    build_search_jobs_handler,
)


logger = logging.getLogger(__name__)
router = APIRouter(prefix="/chat", tags=["chat"])
chat_service = ChatService()
agent_event_service = AgentEventService()
memory_service = ChatMemoryService()
chat_llm_client = OpenAIChatLLMClient()


def build_tool_registry(session: SessionDep) -> ToolRegistry:
    return ToolRegistry(
        overrides={
            "search_jobs": build_search_jobs_handler(session),
            "extract_job_from_text": build_extract_job_from_text_handler(session),
        }
    )


def _is_search_jobs_intent(content: str) -> bool:
    normalized = content.casefold()
    search_terms = ("find", "search", "tìm", "tim", "kiếm", "kiem")
    job_terms = ("job", "jobs", "việc", "viec", "role", "position")
    return any(term in normalized for term in search_terms) and any(
        term in normalized for term in job_terms
    )


PASTED_JOB_MIN_LENGTH = 240
PASTED_JOB_SIGNALS = (
    "responsibilities",
    "requirements",
    "qualifications",
    "skills",
    "company",
    "location",
    "salary",
    "benefits",
    "apply",
    "job description",
    "about the role",
    "what you will do",
)


def _is_pasted_job_text_intent(content: str) -> bool:
    normalized = content.casefold()
    if len(normalized) < PASTED_JOB_MIN_LENGTH:
        return False
    signal_count = sum(1 for signal in PASTED_JOB_SIGNALS if signal in normalized)
    return signal_count >= 3


def _sse_event(event_type: str, payload: dict[str, object]) -> str:
    data = json.dumps(payload, separators=(",", ":"), ensure_ascii=False)
    return f"event: {event_type}\ndata: {data}\n\n"


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


@router.delete(
    "/conversations/{conversation_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_conversation(
    conversation_id: UUID,
    session: SessionDep,
) -> None:
    deleted = await chat_service.delete_conversation(
        session,
        conversation_id=str(conversation_id),
    )
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="conversation not found",
        )


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

    async def _run_tool_with_progress(
        *,
        session: SessionDep,
        tool_call,
        request: ToolRequest,
    ):
        queue = asyncio.Queue()

        async def progress_callback(message: str):
            await queue.put(
                _sse_event(
                    "tool_call_progress",
                    {
                        "tool_call_id": tool_call.id,
                        "tool_name": tool_call.tool_name,
                        "message": message,
                    },
                )
            )

        request.context["on_progress"] = progress_callback

        async def run_tool():
            try:
                result = await build_tool_registry(session).execute(request)
                await queue.put(result)
            except Exception as exc:
                await queue.put(exc)

        task = asyncio.create_task(run_tool())
        tool_result = None
        while not task.done() or not queue.empty():
            try:
                item = await asyncio.wait_for(queue.get(), timeout=0.1)
                if isinstance(item, str):
                    yield item
                elif isinstance(item, Exception):
                    raise item
                else:
                    tool_result = item
            except asyncio.TimeoutError:
                continue

        if tool_result is None:
            raise RuntimeError(f"{request.name} failed without returning result")
        yield tool_result

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
        if _is_search_jobs_intent(user_message.content):
            tool_call = await agent_event_service.create_tool_call(
                session,
                conversation_id=str(conversation_id),
                tool_name="search_jobs",
                input_summary=f"Job search: {user_message.content}",
                safe_payload={"query": user_message.content},
            )
            tool_call = await agent_event_service.mark_running(session, tool_call.id)
            yield _sse_event(
                "tool_call_started",
                {
                    "tool_call_id": tool_call.id,
                    "tool_name": tool_call.tool_name,
                    "status": tool_call.status,
                    "input_summary": tool_call.input_summary,
                },
            )
            try:
                result_stream = _run_tool_with_progress(
                    session=session,
                    tool_call=tool_call,
                    request=ToolRequest(
                        name="search_jobs",
                        arguments={
                            "query": user_message.content,
                            "max_urls": None,
                        },
                        context={
                            "role_profile_id": conversation.role_profile_id,
                            "conversation_id": str(conversation_id),
                        },
                    ),
                )
                tool_result = None
                async for item in result_stream:
                    if isinstance(item, str):
                        yield item
                    else:
                        tool_result = item
                if tool_result is None:
                    raise RuntimeError("Search tool failed without returning result")
            except Exception:
                logger.exception("search_jobs tool failed")
                tool_call = await agent_event_service.mark_failed(
                    session,
                    tool_call.id,
                    error_message="Search tool failed. Check search, extraction, and provider settings.",
                )
                assistant_content = (
                    "Called 1 tool: Job search, but the tool failed. "
                    "Check Tavily/OpenAI/Qdrant configuration and try again."
                )
                agent_metadata_source = "chat_agent_tool_error"
                yield _sse_event(
                    "tool_call_failed",
                    {
                        "tool_call_id": tool_call.id,
                        "tool_name": tool_call.tool_name,
                        "status": tool_call.status,
                        "error_message": tool_call.error_message,
                    },
                )
            else:
                tool_call = await agent_event_service.mark_success(
                    session,
                    tool_call.id,
                    result_summary=tool_result.result_summary,
                    safe_payload=tool_result.safe_payload,
                )
                assistant_content = (
                    "Called 1 tool: Job search. "
                    f"{tool_result.result_summary} Open Review Queue to review jobs."
                )
                agent_metadata_source = "chat_agent_tool"
                yield _sse_event(
                    "tool_call_completed",
                    {
                        "tool_call_id": tool_call.id,
                        "tool_name": tool_call.tool_name,
                        "status": tool_call.status,
                        "result_summary": tool_call.result_summary,
                        "safe_payload": tool_result.safe_payload,
                    },
                )
        elif _is_pasted_job_text_intent(user_message.content):
            tool_call = await agent_event_service.create_tool_call(
                session,
                conversation_id=str(conversation_id),
                tool_name="extract_job_from_text",
                input_summary=f"Pasted job text, {len(user_message.content)} characters",
                safe_payload={"character_count": len(user_message.content)},
            )
            tool_call = await agent_event_service.mark_running(session, tool_call.id)
            yield _sse_event(
                "tool_call_started",
                {
                    "tool_call_id": tool_call.id,
                    "tool_name": tool_call.tool_name,
                    "status": tool_call.status,
                    "input_summary": tool_call.input_summary,
                },
            )
            try:
                result_stream = _run_tool_with_progress(
                    session=session,
                    tool_call=tool_call,
                    request=ToolRequest(
                        name="extract_job_from_text",
                        arguments={"raw_text": user_message.content},
                        context={
                            "role_profile_id": conversation.role_profile_id,
                            "conversation_id": str(conversation_id),
                        },
                    ),
                )
                tool_result = None
                async for item in result_stream:
                    if isinstance(item, str):
                        yield item
                    else:
                        tool_result = item
                if tool_result is None:
                    raise RuntimeError("extract_job_from_text failed without returning result")
            except Exception:
                logger.exception("extract_job_from_text tool failed")
                tool_call = await agent_event_service.mark_failed(
                    session,
                    tool_call.id,
                    error_message="Job text extraction failed. Check the pasted text and provider settings.",
                )
                assistant_content = (
                    "Called 1 tool: Extract job from text, but extraction failed. "
                    "Check that the pasted text contains a real job description and try again."
                )
                agent_metadata_source = "chat_agent_tool_error"
                yield _sse_event(
                    "tool_call_failed",
                    {
                        "tool_call_id": tool_call.id,
                        "tool_name": tool_call.tool_name,
                        "status": tool_call.status,
                        "error_message": tool_call.error_message,
                    },
                )
            else:
                tool_call = await agent_event_service.mark_success(
                    session,
                    tool_call.id,
                    result_summary=tool_result.result_summary,
                    safe_payload=tool_result.safe_payload,
                )
                assistant_content = (
                    "Called 1 tool: Extract job from text. "
                    f"{tool_result.result_summary} Open Review Queue to inspect and approve it."
                )
                agent_metadata_source = "chat_agent_tool"
                yield _sse_event(
                    "tool_call_completed",
                    {
                        "tool_call_id": tool_call.id,
                        "tool_name": tool_call.tool_name,
                        "status": tool_call.status,
                        "result_summary": tool_call.result_summary,
                        "safe_payload": tool_result.safe_payload,
                    },
                )
        else:
            agent_metadata_source = "chat_agent"
            try:
                result = await run_chat_turn(
                    {
                        "conversation_id": str(conversation_id),
                        "role_profile_id": conversation.role_profile_id,
                        "user_message": user_message.content,
                        "working_memory": memory.context_text,
                        "tool_results": [],
                    },
                    llm_client=chat_llm_client,
                    tool_registry=None,
                )
                assistant_content = result["final_answer"]
            except ChatLLMProviderError:
                logger.exception("Chat LLM is unavailable")
                agent_metadata_source = "chat_agent_error"
                assistant_content = (
                    "Chat LLM is unavailable. Check OPENAI_API_KEY and provider settings, "
                    "then try again."
                )
        assistant = await chat_service.append_message(
            session,
            conversation_id=str(conversation_id),
            role="assistant",
            content=assistant_content,
            metadata={
                "source": agent_metadata_source,
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
