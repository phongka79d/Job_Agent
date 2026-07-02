"""Store and validate role-profile CV export templates."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import ProfileCvTemplate


UNSAFE_LATEX_COMMANDS = (
    "\\write18",
    "\\input",
    "\\include",
    "\\includegraphics",
    "\\openout",
    "\\read",
    "\\catcode",
    "\\usepackage{shellesc}",
    "\\immediate\\write",
)


class ProfileCvTemplateService:
    """Manages the active LaTeX template for CV draft exports."""

    async def get_active_template(
        self,
        session: AsyncSession,
        *,
        role_profile_id: str,
    ) -> ProfileCvTemplate | None:
        result = await session.execute(
            select(ProfileCvTemplate)
            .where(
                ProfileCvTemplate.role_profile_id == role_profile_id,
                ProfileCvTemplate.is_active.is_(True),
            )
            .order_by(ProfileCvTemplate.updated_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def save_active_template(
        self,
        session: AsyncSession,
        *,
        role_profile_id: str,
        name: str,
        template_source: str,
    ) -> ProfileCvTemplate:
        cleaned_name = name.strip()
        cleaned_source = template_source.strip()
        if not cleaned_name:
            raise ValueError("Template name is required")
        self._validate_latex_source(cleaned_source)

        existing = (
            await session.execute(
                select(ProfileCvTemplate).where(
                    ProfileCvTemplate.role_profile_id == role_profile_id,
                    ProfileCvTemplate.is_active.is_(True),
                )
            )
        ).scalars().all()
        for template in existing:
            template.is_active = False

        template = ProfileCvTemplate(
            role_profile_id=role_profile_id,
            name=cleaned_name,
            template_format="latex",
            template_source=cleaned_source,
            is_active=True,
        )
        session.add(template)
        await session.commit()
        await session.refresh(template)
        return template

    @staticmethod
    def _validate_latex_source(template_source: str) -> None:
        if "\\documentclass" not in template_source or "\\begin{document}" not in template_source:
            raise ValueError("LaTeX template must include \\documentclass and \\begin{document}")

        normalized = template_source.lower().replace(" ", "")
        for command in UNSAFE_LATEX_COMMANDS:
            if command.lower().replace(" ", "") in normalized:
                raise ValueError(f"Template contains unsafe LaTeX command: {command}")
