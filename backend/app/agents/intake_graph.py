"""Intake graph: submitting a complaint, step by step, as a LangGraph StateGraph.

classify -> check_duplicates -> route -> (critical?) escalate -> notify

The ai steps fall back to the keyword path on any error, so a submission is never blocked.
The nodes only orchestrate. The rules and db work stay in ComplaintService.
"""
import operator
from typing import TYPE_CHECKING, Annotated, TypedDict

from langgraph.graph import END, START, StateGraph

from backend.app.ai.duplicates import embed_complaint, find_duplicates
from backend.app.ai.triage import Triage, keyword_triage, triage
from backend.app.core.enums import Priority
from backend.app.models import Complaint, User

if TYPE_CHECKING:
    from backend.app.services.complaint_service import ComplaintService


class IntakeState(TypedDict, total=False):
    # what the student sent
    student_id: int
    title: str
    description: str
    category: str
    remarks: str
    # filled in by the nodes
    triage: Triage
    embedding: list[float] | None
    duplicates: list[str]          # ticket ids of similar open complaints
    ticket_id: str
    critical: bool
    steps: Annotated[list[str], operator.add]   # each node adds its name, so we can see the path taken


def build_intake_graph(service: "ComplaintService | None"):
    """service = None is only for drawing the diagram (nodes never run then)"""

    def classify(state: IntakeState) -> dict:
        args = state["title"], state["description"], state["category"]
        try:
            t = triage(service.llm, *args)
        except Exception as e:      # triage already handles ai errors, this catches anything else
            print(f"[INTAKE] triage failed, keyword rules used: {e}")
            t = keyword_triage(*args)
        return {"triage": t, "steps": ["classify"]}

    def check_duplicates(state: IntakeState) -> dict:
        try:
            vector = embed_complaint(service.llm, state["title"], state["description"])
            similar = find_duplicates(service.db, vector, exclude_student_id=state["student_id"])
            found = [c.ticket_id for c, _ in similar]
        except Exception as e:
            print(f"[INTAKE] duplicate check skipped: {e}")
            vector, found = None, []
        return {"embedding": vector, "duplicates": found, "steps": ["check_duplicates"]}

    def route(state: IntakeState) -> dict:
        student = service.db.get(User, state["student_id"])
        complaint = service.create_routed(student, state["title"], state["description"], state["category"],
                                          state.get("remarks", ""), state["triage"], state["embedding"],
                                          state["duplicates"])
        return {"ticket_id": complaint.ticket_id, "critical": complaint.priority == Priority.CRITICAL,
                "steps": ["route"]}

    def escalate(state: IntakeState) -> dict:
        service.escalate_new(_complaint(state))
        return {"steps": ["escalate"]}

    def notify(state: IntakeState) -> dict:
        service.notify_submitted(_complaint(state))
        return {"steps": ["notify"]}

    def _complaint(state: IntakeState) -> Complaint:
        return service.complaints.get_by_ticket(state["ticket_id"])

    def critical_or_not(state: IntakeState) -> str:
        return "escalate" if state["critical"] else "notify"

    graph = StateGraph(IntakeState)
    graph.add_node("classify", classify)
    graph.add_node("check_duplicates", check_duplicates)
    graph.add_node("route", route)
    graph.add_node("escalate", escalate)
    graph.add_node("notify", notify)
    graph.add_edge(START, "classify")
    graph.add_edge("classify", "check_duplicates")
    graph.add_edge("check_duplicates", "route")
    graph.add_conditional_edges("route", critical_or_not, ["escalate", "notify"])
    graph.add_edge("escalate", "notify")
    graph.add_edge("notify", END)
    return graph.compile()


def run_intake(service: "ComplaintService", student: User, title: str, description: str,
               category: str, remarks: str = "") -> IntakeState:
    graph = build_intake_graph(service)
    return graph.invoke({"student_id": student.id, "title": title, "description": description,
                         "category": category, "remarks": remarks, "steps": []})
