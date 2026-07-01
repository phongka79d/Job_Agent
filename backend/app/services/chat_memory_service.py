"""Bounded working-memory assembly for chat agent prompts."""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import ChatConversation, ChatMessage, MemorySummary, RoleProfile
from app.services.token_budget_service import BudgetItem, SimpleTokenCounter, TokenBudgetService


@dataclass(frozen=True)
class AssembledMemory:
    context_text: str
    total_tokens: int
    dropped_keys: list[str]


class ChatMemoryService:
    def __init__(
        self,
        *,
        max_tokens: int = 64000,
        token_counter: SimpleTokenCounter | None = None,
    ) -> None:
        self.budget = TokenBudgetService(max_tokens=max_tokens)
        self.token_counter = token_counter or SimpleTokenCounter()

    async def assemble(
        self,
        session: AsyncSession,
        *,
        conversation_id: str,
        current_user_message: str,
    ) -> AssembledMemory:
        conversation = await self._get_conversation(session, conversation_id)
        profile = await self._get_profile(session, conversation.role_profile_id)
        summary = await self._get_latest_summary(session, conversation_id)
        messages = await self._get_recent_messages(session, conversation_id)

        items = [
            BudgetItem(
                key="system",
                text="System: You are an AI job agent. Use tools for factual job data.",
                tokens=12,
                priority=100,
                required=True,
            ),
            BudgetItem(
                key="current_user_message",
                text=f"Current user message: {current_user_message}",
                tokens=self.token_counter.count(current_user_message),
                priority=95,
                required=True,
            ),
        ]
        if summary is not None:
            items.append(
                BudgetItem(
                    key="conversation_summary",
                    text=f"Conversation summary:\n{summary.summary_text}",
                    tokens=summary.token_count,
                    priority=80,
                )
            )
        items.append(
            BudgetItem(
                key="role_profile",
                text=(
                    f"Role profile:\nTarget role: {profile.target_role}\n"
                    f"Level: {profile.level}\nLocation: {profile.location}\n"
                    f"Accept remote: {profile.accept_remote}\nSkills: {profile.skills}"
                ),
                tokens=self.token_counter.count(profile.target_role or "") + 20,
                priority=75,
            )
        )
        for message in messages:
            text = f"{message.role}: {message.content}"
            items.append(
                BudgetItem(
                    key=f"message:{message.id}",
                    text=text,
                    tokens=message.token_count or self.token_counter.count(text),
                    priority=60,
                )
            )

        selection = self.budget.select(items)
        return AssembledMemory(
            context_text="\n\n".join(item.text for item in selection.items),
            total_tokens=selection.total_tokens,
            dropped_keys=selection.dropped_keys,
        )

    async def _get_conversation(self, session: AsyncSession, conversation_id: str) -> ChatConversation:
        result = await session.execute(select(ChatConversation).where(ChatConversation.id == conversation_id).limit(1))
        conversation = result.scalar_one()
        return conversation

    async def _get_profile(self, session: AsyncSession, role_profile_id: str) -> RoleProfile:
        result = await session.execute(select(RoleProfile).where(RoleProfile.id == role_profile_id).limit(1))
        return result.scalar_one()

    async def _get_latest_summary(self, session: AsyncSession, conversation_id: str) -> MemorySummary | None:
        result = await session.execute(
            select(MemorySummary)
            .where(MemorySummary.conversation_id == conversation_id)
            .order_by(MemorySummary.updated_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def _get_recent_messages(self, session: AsyncSession, conversation_id: str) -> list[ChatMessage]:
        result = await session.execute(
            select(ChatMessage)
            .where(ChatMessage.conversation_id == conversation_id)
            .order_by(ChatMessage.created_at.desc(), ChatMessage.id.desc())
            .limit(40)
        )
        return list(reversed(result.scalars().all()))
