from backend.app.core.enums import Role, Status
from backend.app.services.errors import InvalidTransitionError

# not a real user, means the app did it on its own (like auto-assigning)
SYSTEM = "system"


class StatusMachine:
    """the only status moves allowed, and who can make them"""

    ALLOWED: dict[tuple[Status, Status], set[str]] = {
        (Status.PENDING, Status.ASSIGNED): {SYSTEM},
        (Status.ASSIGNED, Status.IN_PROGRESS): {Role.MANAGER},
        (Status.IN_PROGRESS, Status.RESOLVED): {Role.MANAGER},
        (Status.RESOLVED, Status.IN_PROGRESS): {Role.MANAGER},   # reopen
        (Status.RESOLVED, Status.CLOSED): {Role.ADMIN},
    }

    def can_move(self, old: Status, new: Status, actor: str) -> bool:
        return actor in self.ALLOWED.get((old, new), set())

    def check(self, old: Status, new: Status, actor: str) -> None:
        if not self.can_move(old, new, actor):
            raise InvalidTransitionError(f"Can't move a complaint from {old} to {new} as {actor}.")

    def next_statuses(self, current: Status, actor: str) -> list[Status]:
        return [new for (old, new), actors in self.ALLOWED.items()
                if old == current and actor in actors]
