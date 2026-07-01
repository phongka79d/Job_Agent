"""Persistence service for visible agent tool-call events."""

from __future__ import annotations

import json
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import AgentToolCall, utc_now


class AgentEventService:
    async def create_tool_call(
        self,
        session: AsyncSession,
        *,
        conversation_id: str,
        tool_name: str,
        input_summary: str,
        safe_payload: dict[str, Any] | None = None,
    ) -> AgentToolCall:
        """Persist only caller-sanitized, allowlisted summaries and safe payload."""
        call = AgentToolCall(
            conversation_id=conversation_id,
            tool_name=tool_name,
            status="pending",
            input_summary=input_summary,
            safe_payload_json=(
                json.dumps(safe_payload, separators=(",", ":"))
                if safe_payload is not None
                else None
            ),
        )
        session.add(call)
        return await self._commit_refresh_detach(session, call)

    async def mark_running(
        self,
        session: AsyncSession,
        tool_call_id: str,
    ) -> AgentToolCall:
        call = await self._get_call(session, tool_call_id)
        call.status = "running"
        call.started_at = utc_now()
        return await self._commit_refresh_detach(session, call)

    async def mark_success(
        self,
        session: AsyncSession,
        tool_call_id: str,
        *,
        result_summary: str,
        safe_payload: dict[str, Any] | None = None,
    ) -> AgentToolCall:
        call = await self._get_call(session, tool_call_id)
        call.status = "success"
        call.result_summary = result_summary
        if safe_payload is not None:
            call.safe_payload_json = json.dumps(safe_payload, separators=(",", ":"))
        call.completed_at = utc_now()
        return await self._commit_refresh_detach(session, call)

    async def mark_failed(
        self,
        session: AsyncSession,
        tool_call_id: str,
        *,
        error_message: str,
    ) -> AgentToolCall:
        """Persist only a caller-sanitized frontend-safe error message."""
        call = await self._get_call(session, tool_call_id)
        call.status = "failed"
        call.error_message = error_message
        call.completed_at = utc_now()
        return await self._commit_refresh_detach(session, call)

    async def list_tool_calls(
        self,
        session: AsyncSession,
        *,
        conversation_id: str,
    ) -> list[AgentToolCall]:
        result = await session.execute(
            select(AgentToolCall)
            .where(AgentToolCall.conversation_id == conversation_id)
            .order_by(AgentToolCall.created_at.asc(), AgentToolCall.id.asc())
        )
        return list(result.scalars())

    async def _get_call(
        self,
        session: AsyncSession,
        tool_call_id: str,
    ) -> AgentToolCall:
        result = await session.execute(
            select(AgentToolCall).where(AgentToolCall.id == tool_call_id).limit(1)
        )
        call = result.scalar_one_or_none()
        if call is None:
            raise ValueError("tool call not found")
        return call

    async def _commit_refresh_detach(
        self,
        session: AsyncSession,
        call: AgentToolCall,
    ) -> AgentToolCall:
        await session.commit()
        await session.refresh(call)
        session.expunge(call)
        return call
