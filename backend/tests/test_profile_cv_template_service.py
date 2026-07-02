import pytest

from app.db.models import ProfileCvTemplate, RoleProfile
from app.services.profile_cv_template_service import ProfileCvTemplateService


VALID_TEMPLATE = "\\documentclass{article}\\begin{document}{{AI_TARGETED_EDITS}}\\end{document}"


@pytest.mark.asyncio
async def test_save_template_replaces_active_template_for_profile(db_session) -> None:
    profile = RoleProfile(id="profile-1", target_role="AI Engineer")
    db_session.add(profile)
    await db_session.commit()
    existing = ProfileCvTemplate(
        id="template-1",
        role_profile_id="profile-1",
        name="Old template",
        template_format="latex",
        template_source=VALID_TEMPLATE,
        is_active=True,
    )
    db_session.add(existing)
    await db_session.commit()

    service = ProfileCvTemplateService()
    saved = await service.save_active_template(
        db_session,
        role_profile_id="profile-1",
        name="Harvard style",
        template_source=VALID_TEMPLATE.replace("article", "article\n"),
    )

    await db_session.refresh(existing)
    assert saved.name == "Harvard style"
    assert saved.is_active is True
    assert existing.is_active is False
    assert await service.get_active_template(db_session, role_profile_id="profile-1") == saved


@pytest.mark.asyncio
async def test_save_template_rejects_unsafe_latex(db_session) -> None:
    db_session.add(RoleProfile(id="profile-1", target_role="AI Engineer"))
    await db_session.commit()

    with pytest.raises(ValueError, match="unsafe LaTeX command"):
        await ProfileCvTemplateService().save_active_template(
            db_session,
            role_profile_id="profile-1",
            name="Unsafe",
            template_source="\\documentclass{article}\\begin{document}\\input{secret}\\end{document}",
        )


@pytest.mark.asyncio
async def test_save_template_requires_latex_document(db_session) -> None:
    db_session.add(RoleProfile(id="profile-1", target_role="AI Engineer"))
    await db_session.commit()

    with pytest.raises(ValueError, match="must include"):
        await ProfileCvTemplateService().save_active_template(
            db_session,
            role_profile_id="profile-1",
            name="Invalid",
            template_source="plain text",
        )
