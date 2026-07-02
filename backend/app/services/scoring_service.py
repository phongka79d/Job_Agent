"""
Deterministic Scoring and Text Construction Service.

This module provides pure, deterministic functions for skill normalization,
location scoring, level scoring, scoring formulas, and text construction
for embedding. It is free of database sessions, network calls, or external services.
"""

import json
import re
from typing import Any, Iterable, Optional, Set, Tuple

from app.core.constants import JD_STATUSES

# Approved Skill Alias Normalization Mapping
SKILL_ALIASES = {
    "sqlite": "sqlite",
    "retrieval augmented generation": "rag",
    "retrieval-augmented generation": "rag",
    "large language model": "llm",
    "large language models": "llm",
    "vector database": "vector db",
    "javascript": "js",
    "typescript": "typescript",
}


def normalize_skill(skill: str) -> str:
    """
    Normalize a raw skill string.
    
    Trims leading/trailing whitespace, converts to lowercase,
    and maps the value using the approved SKILL_ALIASES mapping.
    
    Args:
        skill: The raw skill string.
        
    Returns:
        The normalized canonical skill string.
    """
    if not skill:
        return ""
    value = skill.strip().lower()
    return SKILL_ALIASES.get(value, value)


def normalize_skill_set(skills: Iterable[str]) -> Set[str]:
    """
    Normalize a collection of skill strings into a set of canonical skills.
    
    Args:
        skills: An iterable of raw skill strings.
        
    Returns:
        A set of normalized, unique, non-empty canonical skill strings.
    """
    if not skills:
        return set()
    return {normalize_skill(s) for s in skills if s and str(s).strip()}


def extract_text_match_tokens(
    value: str | None,
    *,
    stopwords: set[str] | None = None,
) -> set[str]:
    """Extract deterministic tokens for lightweight text matching."""
    if not value:
        return set()
    default_stopwords = {"and", "or", "the", "with", "for", "to", "of", "in", "a", "an"}
    ignored = stopwords if stopwords is not None else default_stopwords
    return {
        token
        for token in re.findall(r"[a-zA-Z][a-zA-Z0-9+#.-]{1,}", value.casefold())
        if token not in ignored
    }


def calculate_skill_overlap_score(user_skills: Iterable[str], job_required_skills: Iterable[str]) -> float:
    """
    Calculate the normalized skill overlap score between user and job skills.
    
    Formula: matched_required_skills / total_required_skills.
    If job has no required skills, returns 0.0.
    
    Args:
        user_skills: Iterable of user skills.
        job_required_skills: Iterable of skills required by the job.
        
    Returns:
        Normalized score in [0.0, 1.0].
    """
    norm_user = normalize_skill_set(user_skills)
    norm_job = normalize_skill_set(job_required_skills)
    
    if not norm_job:
        return 0.0
        
    matched = norm_user.intersection(norm_job)
    return len(matched) / len(norm_job)


def calculate_location_score(
    user_location: Optional[str],
    job_location: Optional[str],
    accept_remote: Optional[bool] = False,
    work_mode: Optional[str] = None
) -> float:
    """
    Calculate three-tier location matching score.
    
    - Exact match = 1.0
    - Remote acceptable or partial match = 0.5
    - Mismatch = 0.0
    
    Args:
        user_location: Target location preference from user.
        job_location: Job location.
        accept_remote: Whether remote jobs are acceptable to the user.
        work_mode: Job work mode (onsite, remote, hybrid, etc.).
        
    Returns:
        Location score in [0.0, 0.5, 1.0].
    """
    user_loc_clean = user_location.strip().lower() if user_location else ""
    job_loc_clean = job_location.strip().lower() if job_location else ""
    work_mode_clean = work_mode.strip().lower() if work_mode else ""
    
    # If both locations are blank, but accept_remote is True and work_mode is remote
    if not user_loc_clean and not job_loc_clean:
        if accept_remote and (work_mode_clean == "remote" or "remote" in job_loc_clean):
            return 0.5
        return 0.0

    # Exact Match
    if user_loc_clean and job_loc_clean and user_loc_clean == job_loc_clean:
        return 1.0

    # Partial Match
    is_partial = False
    if user_loc_clean and job_loc_clean:
        if user_loc_clean in job_loc_clean or job_loc_clean in user_loc_clean:
            is_partial = True

    # Remote Acceptable
    is_remote_match = False
    if accept_remote:
        if work_mode_clean == "remote" or "remote" in job_loc_clean:
            is_remote_match = True

    if is_partial or is_remote_match:
        return 0.5

    return 0.0


def calculate_level_score(user_level: Optional[str], job_level: Optional[str]) -> float:
    """
    Calculate three-tier level matching score including approved adjacent level pairs.
    
    - Exact level match = 1.0
    - Adjacent level match = 0.5
    - Mismatch = 0.0
    
    Approved adjacent level pairs:
    - intern <-> fresher
    - fresher <-> junior
    - junior <-> mid
    - mid <-> senior
    
    Args:
        user_level: Target level preference from user.
        job_level: Level of the job post.
        
    Returns:
        Level score in [0.0, 0.5, 1.0].
    """
    if not user_level or not job_level:
        return 0.0
        
    u_lvl = user_level.strip().lower()
    j_lvl = job_level.strip().lower()
    
    if u_lvl == j_lvl:
        return 1.0
        
    adjacent_pairs = {
        ("intern", "fresher"),
        ("fresher", "junior"),
        ("junior", "mid"),
        ("mid", "senior"),
    }
    
    if (u_lvl, j_lvl) in adjacent_pairs or (j_lvl, u_lvl) in adjacent_pairs:
        return 0.5
        
    return 0.0


def get_jd_confidence_multiplier(jd_status: Optional[str]) -> Optional[float]:
    """
    Return the confidence multiplier based on JD completeness status.
    
    Only full_jd and partial_jd return a valid numeric multiplier.
    Other statuses (contact_for_jd, no_jd, unclear) or invalid statuses return None.
    
    Args:
        jd_status: Complete status of the job description.
        
    Returns:
        Multiplier float or None.
    """
    if jd_status not in JD_STATUSES:
        return None
        
    if jd_status == "full_jd":
        return 1.00
    elif jd_status == "partial_jd":
        return 0.85
        
    return None


def clamp_score(score: Optional[float]) -> float:
    """
    Clamp a score to the range [0.0, 1.0].
    
    Args:
        score: The raw score.
        
    Returns:
        The clamped score in [0.0, 1.0].
    """
    if score is None:
        return 0.0
    try:
        val = float(score)
    except (ValueError, TypeError):
        return 0.0
    return max(0.0, min(1.0, val))


def calculate_base_score(
    embedding_similarity: Optional[float],
    skill_overlap_score: Optional[float],
    location_match_score: Optional[float],
    level_match_score: Optional[float]
) -> float:
    """
    Calculate the base score before applying confidence multiplier.
    
    Formula:
        base_score = 0.55 * embedding_similarity
                   + 0.25 * skill_overlap_score
                   + 0.10 * location_match_score
                   + 0.10 * level_match_score
                   
    All inputs are normalized to [0.0, 1.0] internally.
    
    Args:
        embedding_similarity: Semantic similarity score.
        skill_overlap_score: Skill overlap score.
        location_match_score: Location matching score.
        level_match_score: Level matching score.
        
    Returns:
        Clamped base score in [0.0, 1.0].
    """
    sim = clamp_score(embedding_similarity)
    skills = clamp_score(skill_overlap_score)
    loc = clamp_score(location_match_score)
    lvl = clamp_score(level_match_score)
    
    base = (0.55 * sim) + (0.25 * skills) + (0.10 * loc) + (0.10 * lvl)
    return clamp_score(base)


def calculate_final_scores(
    base_score: Optional[float],
    jd_confidence_multiplier: Optional[float]
) -> Tuple[Optional[float], Optional[float]]:
    """
    Calculate final score and final score percentage.
    
    Formulas:
        final_score = base_score * jd_confidence_multiplier
        final_score_percent = final_score * 100
        
    Returns (None, None) if either base_score or jd_confidence_multiplier is None.
    
    Args:
        base_score: Base score.
        jd_confidence_multiplier: Confidence multiplier.
        
    Returns:
        Tuple of (final_score, final_score_percent) or (None, None).
    """
    if base_score is None or jd_confidence_multiplier is None:
        return None, None
        
    final_score = clamp_score(base_score * jd_confidence_multiplier)
    final_score_percent = final_score * 100.0
    return final_score, final_score_percent


def _get_field(obj: Any, field_name: str) -> Any:
    """
    Helper to access attributes or dictionary keys safely.
    
    Args:
        obj: The object or dictionary.
        field_name: The field to retrieve.
        
    Returns:
        The field value or None.
    """
    if isinstance(obj, dict):
        return obj.get(field_name)
    return getattr(obj, field_name, None)


def _parse_list_field(value: Any) -> list[str]:
    """
    Helper to parse skills or tech stack from JSON strings, lists, or sets safely.
    
    Args:
        value: Raw value of list/set field.
        
    Returns:
        List of strings.
    """
    if not value:
        return []
    if isinstance(value, (list, set, tuple)):
        return [str(item).strip() for item in value if item]
    if isinstance(value, str):
        value_str = value.strip()
        if value_str.startswith("[") and value_str.endswith("]"):
            try:
                parsed = json.loads(value_str)
                if isinstance(parsed, list):
                    return [str(item).strip() for item in parsed if item]
            except Exception:
                pass
        # Fallback for comma separated strings
        return [item.strip() for item in value_str.split(",") if item.strip()]
    return []


def build_embedding_text(job: Any) -> str:
    """
    Build clean job embedding text from extracted fields only.
    
    Includes title, level, location, work mode, responsibilities,
    requirements, skills, and tech stack if present.
    
    Args:
        job: Job object (ORM model, Pydantic model, or dict).
        
    Returns:
        Constructed text for embedding.
    """
    title = _get_field(job, "title")
    level = _get_field(job, "level")
    location = _get_field(job, "location")
    work_mode = _get_field(job, "work_mode")
    responsibilities = _get_field(job, "responsibilities")
    requirements = _get_field(job, "requirements")
    
    skills_raw = _get_field(job, "skills")
    skills_list = _parse_list_field(skills_raw)
    
    tech_stack_raw = _get_field(job, "tech_stack")
    tech_stack_list = _parse_list_field(tech_stack_raw)
    
    parts = []
    if title and str(title).strip():
        parts.append(f"Title: {str(title).strip()}")
    if level and str(level).strip():
        parts.append(f"Level: {str(level).strip()}")
    if location and str(location).strip():
        parts.append(f"Location: {str(location).strip()}")
    if work_mode and str(work_mode).strip():
        parts.append(f"Work mode: {str(work_mode).strip()}")
    if responsibilities and str(responsibilities).strip():
        parts.append(f"Responsibilities: {str(responsibilities).strip()}")
    if requirements and str(requirements).strip():
        parts.append(f"Requirements: {str(requirements).strip()}")
    if skills_list:
        parts.append(f"Skills: {', '.join(skills_list)}")
    if tech_stack_list:
        parts.append(f"Tech stack: {', '.join(tech_stack_list)}")
        
    return "\n".join(parts)


def build_role_query_text(role_profile: Any) -> str:
    """
    Build role query text dynamically from role profile fields.
    
    Includes target role, level, location, remote preference, skills,
    and resume/profile text if present.
    
    Args:
        role_profile: RoleProfile object (ORM model, Pydantic model, or dict).
        
    Returns:
        Constructed role query text.
    """
    target_role = _get_field(role_profile, "target_role")
    level = _get_field(role_profile, "level")
    location = _get_field(role_profile, "location")
    accept_remote = _get_field(role_profile, "accept_remote")
    
    skills_raw = _get_field(role_profile, "skills")
    skills_list = _parse_list_field(skills_raw)
    
    resume_text = _get_field(role_profile, "resume_text")
    
    parts = []
    if target_role and str(target_role).strip():
        parts.append(f"Target role: {str(target_role).strip()}")
    if level and str(level).strip():
        parts.append(f"Level: {str(level).strip()}")
    if location and str(location).strip():
        parts.append(f"Location: {str(location).strip()}")
    if accept_remote:
        parts.append("Remote acceptable")
    if skills_list:
        parts.append(f"Skills: {', '.join(skills_list)}")
    if resume_text and str(resume_text).strip():
        parts.append(f"Resume/Profile: {str(resume_text).strip()}")
        
    return "\n".join(parts)


def build_role_query_text_with_cv_evidence(role_profile: Any, active_cv_text: str | None) -> str:
    """Build profile embedding text with active CV evidence as the primary source."""
    if not active_cv_text or not str(active_cv_text).strip():
        return build_role_query_text(role_profile)

    target_role = _get_field(role_profile, "target_role")
    level = _get_field(role_profile, "level")
    location = _get_field(role_profile, "location")
    accept_remote = _get_field(role_profile, "accept_remote")
    skills_list = _parse_list_field(_get_field(role_profile, "skills"))

    parts: list[str] = []
    if target_role and str(target_role).strip():
        parts.append(f"Target role: {str(target_role).strip()}")
    if level and str(level).strip():
        parts.append(f"Level: {str(level).strip()}")
    if location and str(location).strip():
        parts.append(f"Location: {str(location).strip()}")
    if accept_remote:
        parts.append("Remote acceptable")
    if skills_list:
        parts.append(f"Skills: {', '.join(skills_list)}")
    parts.append(f"Active CV evidence:\n{str(active_cv_text).strip()}")
    return "\n".join(parts)
