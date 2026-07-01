"""Chat conversation and message persistence service."""

from __future__ import annotations

import json
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import ChatConversation, ChatMessage, utc_now


VALID_MESSAGE_ROLES = frozenset({"user", "assistant", "system", "tool"})
VALID_CONVERSATION_STATUSES = frozenset({"active", "archived"})


class ChatService:
    async def create_conversation(
        self,
        session: AsyncSession,
        *,
        role_profile_id: str,
        title: str | None = None,
    ) -> ChatConversation:
        conversation = ChatConversation(
            role_profile_id=role_profile_id,
            title=title,
            status="active",
        )
        session.add(conversation)
        await session.commit()
        await session.refresh(conversation)
        return conversation

    async def list_conversations(
        self,
        session: AsyncSession,
        *,
        role_profile_id: str,
        limit: int = 50,
    ) -> list[ChatConversation]:
        result = await session.execute(
            select(ChatConversation)
            .where(ChatConversation.role_profile_id == role_profile_id)
            .order_by(ChatConversation.updated_at.desc())
            .limit(limit)
        )
        return list(result.scalars())

    async def append_message(
        self,
        session: AsyncSession,
        *,
        conversation_id: str,
        role: str,
        content: str,
        token_count: int | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> ChatMessage:
        if role not in VALID_MESSAGE_ROLES:
            raise ValueError(f"Unsupported chat message role: {role}")
        message = ChatMessage(
            conversation_id=conversation_id,
            role=role,
            content=content,
            token_count=token_count,
            metadata_json=json.dumps(metadata, separators=(",", ":")) if metadata is not None else None,
        )
        session.add(message)
        conversation = await session.get(ChatConversation, conversation_id)
        if conversation is not None:
            conversation.updated_at = utc_now()
        await session.commit()
        await session.refresh(message)
        return message

    async def list_messages(
        self,
        session: AsyncSession,
        *,
        conversation_id: str,
        limit: int = 200,
    ) -> list[ChatMessage]:
        result = await session.execute(
            select(ChatMessage)
            .where(ChatMessage.conversation_id == conversation_id)
            .order_by(ChatMessage.created_at.asc(), ChatMessage.id.asc())
            .limit(limit)
        )
        return list(result.scalars())

    async def delete_conversation(
        self,
        session: AsyncSession,
        *,
        conversation_id: str,
    ) -> bool:
        conversation = await session.get(ChatConversation, conversation_id)
        if conversation is None:
            return False
        await session.delete(conversation)
        await session.commit()
        return True
