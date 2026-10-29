import itertools

import pytest

from backend.app.core.enums import Role, Status
from backend.app.services.errors import InvalidTransitionError
from backend.app.services.status_machine import SYSTEM, StatusMachine

machine = StatusMachine()

ALLOWED = [
    (Status.PENDING, Status.ASSIGNED, SYSTEM),
    (Status.ASSIGNED, Status.IN_PROGRESS, Role.MANAGER),
    (Status.IN_PROGRESS, Status.RESOLVED, Role.MANAGER),
    (Status.RESOLVED, Status.IN_PROGRESS, Role.MANAGER),
    (Status.RESOLVED, Status.CLOSED, Role.ADMIN),
]
ACTORS = [SYSTEM, Role.STUDENT, Role.MANAGER, Role.ADMIN]

# every other (old, new, actor) combination must be blocked
BLOCKED = [combo for combo in itertools.product(Status, Status, ACTORS)
           if combo not in ALLOWED]


@pytest.mark.parametrize("old,new,actor", ALLOWED)
def test_allowed_moves(old, new, actor):
    assert machine.can_move(old, new, actor)
    machine.check(old, new, actor)  # no error


@pytest.mark.parametrize("old,new,actor", BLOCKED)
def test_blocked_moves(old, new, actor):
    assert not machine.can_move(old, new, actor)
    with pytest.raises(InvalidTransitionError):
        machine.check(old, new, actor)


def test_next_statuses_for_manager():
    assert machine.next_statuses(Status.ASSIGNED, Role.MANAGER) == [Status.IN_PROGRESS]
    assert machine.next_statuses(Status.RESOLVED, Role.MANAGER) == [Status.IN_PROGRESS]
    assert machine.next_statuses(Status.CLOSED, Role.MANAGER) == []
