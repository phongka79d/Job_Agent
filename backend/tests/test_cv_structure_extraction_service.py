from app.services.cv_structure_extraction_service import (
    POOR_STRUCTURE_RECOMMENDATION,
    CvStructureExtractionService,
)


def test_structure_extraction_marks_ordered_cv_reliable():
    text = """
    Summary
    AI engineer intern focused on Python and RAG.

    Experience
    - Built FastAPI services
    - Integrated vector search

    Projects
    - Job Agent: LangGraph workflow

    Education
    University of Engineering, 2024

    Skills
    Python, FastAPI, SQL
    """

    result = CvStructureExtractionService().analyze(text)

    assert result.status == "reliable"
    assert result.confidence >= 0.75
    assert [section.heading for section in result.sections][:3] == [
        "Summary",
        "Experience",
        "Projects",
    ]
    assert result.recommendation is None


def test_structure_extraction_marks_sparse_text_unreliable():
    text = "AI engineer intern. Python FastAPI RAG. Hanoi. Open to internships."

    result = CvStructureExtractionService().analyze(text)

    assert result.status == "unreliable"
    assert result.confidence < 0.25
    assert result.recommendation == POOR_STRUCTURE_RECOMMENDATION


def test_structure_extraction_marks_broken_text_with_table_noise():
    text = "Python\n|\n|\n2024\nName\nEmail\nTable cell cell cell\n" * 2

    result = CvStructureExtractionService().analyze(text)

    assert result.status != "reliable"
    assert any("noise" in warning.lower() for warning in result.warnings)
