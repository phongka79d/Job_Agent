"""
Unit Tests for Scoring Service.

Verifies deterministic scoring formulas, skill normalization,
location scoring, level scoring, confidence multipliers, and text builders.
"""

import pytest
from app.services.scoring_service import (
    normalize_skill,
    normalize_skill_set,
    calculate_skill_overlap_score,
    calculate_location_score,
    calculate_level_score,
    get_jd_confidence_multiplier,
    clamp_score,
    calculate_base_score,
    calculate_final_scores,
    build_embedding_text,
    build_role_query_text,
)


def test_normalize_skill():
    """Verify alias normalization and basic cleanup."""
    assert normalize_skill("  SQLite  ") == "sqlite"
    assert normalize_skill("Retrieval-Augmented Generation") == "rag"
    assert normalize_skill("Retrieval Augmented Generation") == "rag"
    assert normalize_skill("Large Language Model") == "llm"
    assert normalize_skill("Large Language Models") == "llm"
    assert normalize_skill("Vector Database") == "vector db"
    assert normalize_skill("JavaScript") == "js"
    assert normalize_skill("TypeScript") == "typescript"
    assert normalize_skill("Python") == "python"  # No alias, just lowercase/strip
    assert normalize_skill("") == ""
    assert normalize_skill(None) == ""


def test_normalize_skill_set():
    """Verify set of skills is normalized correctly."""
    skills = ["  SQLite ", "Python", "Large Language Model", "", None]
    expected = {"sqlite", "python", "llm"}
    assert normalize_skill_set(skills) == expected


def test_calculate_skill_overlap_score():
    """Verify overlap calculations including empty edge cases."""
    user_skills = ["python", "rag", "js", "fastapi"]
    job_skills = ["python", "rag", "docker", "sqlite"]
    
    # Python and RAG are in user_skills. Total job skills is 4. Overlap is 2/4 = 0.5
    assert calculate_skill_overlap_score(user_skills, job_skills) == 0.5
    
    # Empty job skills should yield 0.0
    assert calculate_skill_overlap_score(user_skills, []) == 0.0
    
    # Overlap with aliases resolved: "Retrieval-Augmented Generation" maps to "rag"
    user_skills_aliases = ["Retrieval-Augmented Generation", "javascript"]
    job_skills_aliases = ["rag", "js"]
    assert calculate_skill_overlap_score(user_skills_aliases, job_skills_aliases) == 1.0


def test_calculate_location_score():
    """Verify location scoring three-tier logic."""
    # Exact match = 1.0
    assert calculate_location_score("Ha Noi", "Ha Noi") == 1.0
    assert calculate_location_score("  ha noi  ", "HA NOI") == 1.0
    
    # Remote acceptable or partial match = 0.5
    # Partial match
    assert calculate_location_score("Ha Noi", "Cau Giay, Ha Noi") == 0.5
    assert calculate_location_score("Ha Noi, Vietnam", "Ha Noi") == 0.5
    
    # Remote match
    assert calculate_location_score("Ha Noi", "Remote", accept_remote=True) == 0.5
    assert calculate_location_score("Ha Noi", "onsite", accept_remote=True, work_mode="remote") == 0.5
    
    # Mismatch = 0.0
    assert calculate_location_score("Ha Noi", "Ho Chi Minh") == 0.0
    assert calculate_location_score("Ha Noi", "Remote", accept_remote=False) == 0.0


def test_calculate_level_score():
    """Verify level scoring including adjacent levels."""
    # Exact level match = 1.0
    assert calculate_level_score("intern", "intern") == 1.0
    assert calculate_level_score("Senior", "  senior  ") == 1.0
    
    # Adjacent level match = 0.5
    assert calculate_level_score("intern", "fresher") == 0.5
    assert calculate_level_score("fresher", "intern") == 0.5
    assert calculate_level_score("fresher", "junior") == 0.5
    assert calculate_level_score("junior", "mid") == 0.5
    assert calculate_level_score("mid", "senior") == 0.5
    
    # Mismatch = 0.0
    assert calculate_level_score("intern", "junior") == 0.0
    assert calculate_level_score("junior", "senior") == 0.0
    assert calculate_level_score("unknown", "intern") == 0.0
    assert calculate_level_score(None, "intern") == 0.0


def test_get_jd_confidence_multiplier():
    """Verify JD status multiplier mapping."""
    assert get_jd_confidence_multiplier("full_jd") == 1.00
    assert get_jd_confidence_multiplier("partial_jd") == 0.85
    assert get_jd_confidence_multiplier("contact_for_jd") is None
    assert get_jd_confidence_multiplier("no_jd") is None
    assert get_jd_confidence_multiplier("unclear") is None
    assert get_jd_confidence_multiplier("invalid_status") is None


def test_clamp_score():
    """Verify score clamping to [0, 1]."""
    assert clamp_score(0.85) == 0.85
    assert clamp_score(1.5) == 1.0
    assert clamp_score(-0.5) == 0.0
    assert clamp_score(None) == 0.0
    assert clamp_score("invalid") == 0.0


def test_calculate_base_score():
    """Verify weighted base score formula."""
    # Formula: 0.55 * sim + 0.25 * skills + 0.10 * loc + 0.10 * lvl
    # Case 1: All 1.0 -> 1.0
    assert calculate_base_score(1.0, 1.0, 1.0, 1.0) == 1.0
    
    # Case 2: sim=0.8, skills=0.6, loc=0.5, lvl=1.0
    # base = 0.55*0.8 + 0.25*0.6 + 0.10*0.5 + 0.10*1.0
    #      = 0.44 + 0.15 + 0.05 + 0.10 = 0.74
    assert pytest.approx(calculate_base_score(0.8, 0.6, 0.5, 1.0)) == 0.74


def test_calculate_final_scores():
    """Verify final score and percent calculation."""
    # Case 1: full_jd (multiplier 1.0)
    base = 0.80
    final, percent = calculate_final_scores(base, 1.00)
    assert final == 0.80
    assert percent == 80.0
    
    # Case 2: partial_jd (multiplier 0.85)
    final, percent = calculate_final_scores(base, 0.85)
    assert pytest.approx(final) == 0.68
    assert pytest.approx(percent) == 68.0
    
    # Case 3: non-scorable (multiplier None)
    final, percent = calculate_final_scores(base, None)
    assert final is None
    assert percent is None


@pytest.mark.parametrize("jd_status", ["contact_for_jd", "no_jd", "unclear"])
def test_non_scorable_statuses_return_null_score_behavior(jd_status):
    """Verify non-scorable JD statuses produce null final score fields."""
    multiplier = get_jd_confidence_multiplier(jd_status)
    final_score, final_percent = calculate_final_scores(0.80, multiplier)

    assert multiplier is None
    assert final_score is None
    assert final_percent is None


def test_qdrant_similarity_score_clamping_helper():
    """Verify the shared Qdrant score normalization helper clamps to [0, 1]."""
    assert clamp_score(1.25) == 1.0
    assert clamp_score(0.42) == 0.42
    assert clamp_score(-0.25) == 0.0


def test_build_embedding_text():
    """Verify job embedding text construction for dicts and objects."""
    # Dict input
    job_dict = {
        "title": "Software Engineer",
        "level": "Junior",
        "location": "Ha Noi",
        "work_mode": "Hybrid",
        "responsibilities": "Write code",
        "requirements": "Python, SQL",
        "skills": ["python", "sql"],
        "tech_stack": ["FastAPI", "SQLite"],
    }
    expected_text = (
        "Title: Software Engineer\n"
        "Level: Junior\n"
        "Location: Ha Noi\n"
        "Work mode: Hybrid\n"
        "Responsibilities: Write code\n"
        "Requirements: Python, SQL\n"
        "Skills: python, sql\n"
        "Tech stack: FastAPI, SQLite"
    )
    assert build_embedding_text(job_dict) == expected_text

    # Dummy class input
    class JobObject:
        def __init__(self):
            self.title = "Data Scientist"
            self.level = "Senior"
            self.location = "Remote"
            self.work_mode = "Remote"
            self.responsibilities = "Build models"
            self.requirements = "Math, Python"
            self.skills = '["python", "pandas"]'  # JSON string format
            
    job_obj = JobObject()
    expected_obj_text = (
        "Title: Data Scientist\n"
        "Level: Senior\n"
        "Location: Remote\n"
        "Work mode: Remote\n"
        "Responsibilities: Build models\n"
        "Requirements: Math, Python\n"
        "Skills: python, pandas"
    )
    assert build_embedding_text(job_obj) == expected_obj_text


def test_build_role_query_text():
    """Verify role profile query text construction."""
    # Dict input
    profile_dict = {
        "target_role": "AI Engineer",
        "level": "Intern",
        "location": "Ha Noi",
        "accept_remote": True,
        "skills": ["Python", "RAG"],
        "resume_text": "Experienced Intern profile...",
    }
    expected_text = (
        "Target role: AI Engineer\n"
        "Level: Intern\n"
        "Location: Ha Noi\n"
        "Remote acceptable\n"
        "Skills: Python, RAG\n"
        "Resume/Profile: Experienced Intern profile..."
    )
    assert build_role_query_text(profile_dict) == expected_text

    # Dummy class input
    class ProfileObject:
        def __init__(self):
            self.target_role = "Backend Dev"
            self.level = "Junior"
            self.location = "Ho Chi Minh"
            self.accept_remote = False
            self.skills = "Python, FastAPI"  # comma-separated string format
            self.resume_text = None

    profile_obj = ProfileObject()
    expected_obj_text = (
        "Target role: Backend Dev\n"
        "Level: Junior\n"
        "Location: Ho Chi Minh\n"
        "Skills: Python, FastAPI"
    )
    assert build_role_query_text(profile_obj) == expected_obj_text


def test_build_role_query_text_with_cv_evidence_prefers_active_cv_text():
    from app.services.scoring_service import build_role_query_text_with_cv_evidence

    profile = {
        "target_role": "AI Engineer",
        "level": "Intern",
        "location": "Hanoi",
        "accept_remote": True,
        "skills": ["Python"],
        "resume_text": "Legacy resume text",
    }

    text = build_role_query_text_with_cv_evidence(
        profile,
        active_cv_text="Active CV evidence with FastAPI and RAG projects",
    )

    assert "Active CV evidence with FastAPI and RAG projects" in text
    assert "Legacy resume text" not in text
    assert "Target role: AI Engineer" in text
    assert "Skills: Python" in text
