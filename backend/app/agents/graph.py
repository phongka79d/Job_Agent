"""LangGraph extraction workflow graph compilation."""

from langgraph.graph import StateGraph, END
from app.agents.schemas import (
    JobAgentState,
    validate_extraction_status,
    validate_parse_status,
)
from app.agents.nodes import (
    prepare_content,
    extract_job,
    repair_job,
    classify_jd,
    mark_unclear,
)


def route_after_prepare(state: JobAgentState) -> str:
    """Route after prepare content node."""
    if validate_parse_status(state.get("parse_status")) == "success":
        return "extract_job"
    return END


def route_after_extract(state: JobAgentState) -> str:
    """Route after initial extract node."""
    status = validate_extraction_status(state.get("extraction_status"))
    if status == "success":
        return "classify_jd"
    elif status == "failed":
        return "mark_unclear"
    else:
        return "repair_job"


def route_after_repair(state: JobAgentState) -> str:
    """Route after repair attempt node."""
    status = validate_extraction_status(state.get("extraction_status"))
    if status in ("success", "retried"):
        return "classify_jd"
    return "mark_unclear"


workflow = StateGraph(JobAgentState)

workflow.add_node("prepare_content", prepare_content)
workflow.add_node("extract_job", extract_job)
workflow.add_node("repair_job", repair_job)
workflow.add_node("classify_jd", classify_jd)
workflow.add_node("mark_unclear", mark_unclear)

workflow.set_entry_point("prepare_content")

workflow.add_conditional_edges(
    "prepare_content",
    route_after_prepare,
    {
        "extract_job": "extract_job",
        END: END,
    },
)
workflow.add_conditional_edges(
    "extract_job",
    route_after_extract,
    {
        "classify_jd": "classify_jd",
        "mark_unclear": "mark_unclear",
        "repair_job": "repair_job",
    },
)
workflow.add_conditional_edges(
    "repair_job",
    route_after_repair,
    {
        "classify_jd": "classify_jd",
        "mark_unclear": "mark_unclear",
    },
)

workflow.add_edge("classify_jd", END)
workflow.add_edge("mark_unclear", END)

graph = workflow.compile()
