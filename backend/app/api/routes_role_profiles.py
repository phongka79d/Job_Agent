"""Role profile API routes."""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas import (
    RoleProfileCreateRequest,
    RoleProfileListResponse,
    RoleProfileResponse,
)
from app.db.models import RoleProfile
from app.db.session import async_session_maker


async def get_session() -> AsyncIterator[AsyncSession]:
    async with async_session_maker() as session:
        yield session


SessionDep = Annotated[AsyncSession, Depends(get_session)]

router = APIRouter(prefix="/role-profiles", tags=["role-profiles"])


@router.post(
    "",
    response_model=RoleProfileResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_role_profile(
    request: RoleProfileCreateRequest,
    session: SessionDep,
) -> RoleProfile:
    role_profile = RoleProfile(
        target_role=request.target_role,
        level=request.level,
        location=request.location,
        accept_remote=request.accept_remote,
        skills=json.dumps(request.skills),
        resume_text=request.resume_text,
    )
    session.add(role_profile)
    await session.commit()
    await session.refresh(role_profile)
    return role_profile


@router.get("", response_model=RoleProfileListResponse)
async def list_role_profiles(session: SessionDep) -> RoleProfileListResponse:
    result = await session.execute(
        select(RoleProfile).order_by(
            RoleProfile.created_at.desc(),
            RoleProfile.id.desc(),
        )
    )
    return RoleProfileListResponse(role_profiles=list(result.scalars()))
