"""Services package."""

from app.services.llm_client import (
    FakeJobExtractionClient,
    JobExtractionClientProtocol,
    LLMExtractionError,
    LLMProviderError,
    LLMValidationError,
    OpenAIJobExtractionClient,
)
from app.services.extraction_service import (
    run_extraction_graph,
    extract_from_raw_text,
    extract_from_url,
)
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
from app.services.embedding_service import (
    EmbeddingServiceError,
    embed_text,
)

__all__ = [
    "JobExtractionClientProtocol",
    "OpenAIJobExtractionClient",
    "FakeJobExtractionClient",
    "LLMExtractionError",
    "LLMProviderError",
    "LLMValidationError",
    "run_extraction_graph",
    "extract_from_raw_text",
    "extract_from_url",
    "normalize_skill",
    "normalize_skill_set",
    "calculate_skill_overlap_score",
    "calculate_location_score",
    "calculate_level_score",
    "get_jd_confidence_multiplier",
    "clamp_score",
    "calculate_base_score",
    "calculate_final_scores",
    "build_embedding_text",
    "build_role_query_text",
    "EmbeddingServiceError",
    "embed_text",
]



