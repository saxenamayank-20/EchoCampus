"""Closure graph: closing a complaint with two human decisions (human-in-the-loop).

await_student --(confirmed / auto)--> student_confirmed -> await_admin -> close
              --(disputed)--> back_to_manager
              --(admin override)--> admin_override -> close
              --(manager reopened)--> end

The graph pauses with interrupt() at await_student and await_admin. The checkpointer
saves it (in neon), and the student's answer or the admin's click resumes it,
even days later. One thread per close request: "closure-<confirmation id>".
The rules (who may answer, notes, reasons) are checked in ComplaintService before resuming.
"""
from typing import TYPE_CHECKING, TypedDict

from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, interrupt

from backend.app.agents.checkpointer import get_checkpointer
from backend.app.models import ClosureConfirmation

if TYPE_CHECKING:
    from backend.app.services.complaint_service import ComplaintService

AWAIT_STUDENT, AWAIT_ADMIN = "await_student", "await_admin"


class ClosureState(TypedDict, total=False):
    ticket_id: str
    confirmation_id: int
    student_answer: dict      # {"kind": confirmed / auto_confirmed / disputed / override / withdrawn, ...}
    admin_decision: dict      # {"kind": close / withdrawn, "action", "note", "decision", "reason", "admin_id"}
    outcome: str              # closed / disputed / withdrawn


def build_closure_graph(service: "ComplaintService | None", checkpointer=None):
    # nothing may happen before interrupt(): on resume langgraph runs the node again from the top
    def await_student(state: ClosureState) -> dict:
        answer = interrupt({"waiting_for": "student", "ticket_id": state["ticket_id"]})
        return {"student_answer": answer}

    def student_confirmed(state: ClosureState) -> dict:
        service.apply_student_answer(state["ticket_id"], state["student_answer"])
        return {}

    def back_to_manager(state: ClosureState) -> dict:
        service.apply_student_answer(state["ticket_id"], state["student_answer"])
        return {"outcome": "disputed"}

    def admin_override(state: ClosureState) -> dict:
        # the admin closed while the student hadn't answered: their decision came in at the first pause
        return {"admin_decision": state["student_answer"]}

    def await_admin(state: ClosureState) -> dict:
        decision = interrupt({"waiting_for": "admin", "ticket_id": state["ticket_id"]})
        return {"admin_decision": decision}

    def close(state: ClosureState) -> dict:
        service.apply_close(state["ticket_id"], state["admin_decision"])
        return {"outcome": "closed"}

    def after_student(state: ClosureState) -> str:
        return {"confirmed": "student_confirmed", "auto_confirmed": "student_confirmed",
                "disputed": "back_to_manager", "override": "admin_override"}.get(state["student_answer"]["kind"], END)

    def after_admin(state: ClosureState) -> str:
        return "close" if state["admin_decision"]["kind"] == "close" else END

    graph = StateGraph(ClosureState)
    graph.add_node(AWAIT_STUDENT, await_student)
    graph.add_node("student_confirmed", student_confirmed)
    graph.add_node("back_to_manager", back_to_manager)
    graph.add_node("admin_override", admin_override)
    graph.add_node(AWAIT_ADMIN, await_admin)
    graph.add_node("close", close)
    graph.add_edge(START, AWAIT_STUDENT)
    graph.add_conditional_edges(AWAIT_STUDENT, after_student,
                                ["student_confirmed", "back_to_manager", "admin_override", END])
    graph.add_edge("student_confirmed", AWAIT_ADMIN)
    graph.add_conditional_edges(AWAIT_ADMIN, after_admin, ["close", END])
    graph.add_edge("admin_override", "close")
    graph.add_edge("back_to_manager", END)
    graph.add_edge("close", END)
    return graph.compile(checkpointer=checkpointer)


class ClosureFlow:
    """starts and resumes the closure graph for one service (one db session)"""

    def __init__(self, service: "ComplaintService"):
        self.graph = build_closure_graph(service, get_checkpointer())

    @staticmethod
    def _config(confirmation: ClosureConfirmation) -> dict:
        return {"configurable": {"thread_id": f"closure-{confirmation.id}"}}

    def start(self, confirmation: ClosureConfirmation) -> None:
        """runs until the first pause (waiting for the student)"""
        self.graph.invoke({"ticket_id": confirmation.complaint.ticket_id, "confirmation_id": confirmation.id},
                          self._config(confirmation))

    def waiting_at(self, confirmation: ClosureConfirmation) -> str | None:
        """which pause this close request is in, None = no paused graph (e.g. sqlite after a restart)"""
        nxt = self.graph.get_state(self._config(confirmation)).next
        return nxt[0] if nxt else None

    def resume(self, confirmation: ClosureConfirmation, at: str, answer: dict) -> bool:
        """continue from pause `at` with the answer. False = not paused there, caller does it directly"""
        if self.waiting_at(confirmation) != at:
            return False
        self.graph.invoke(Command(resume=answer), self._config(confirmation))
        return True
