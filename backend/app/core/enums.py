from enum import StrEnum


class Role(StrEnum):
    STUDENT = "student"
    MANAGER = "grievance_manager"
    ADMIN = "admin"


class Status(StrEnum):
    PENDING = "Pending"
    ASSIGNED = "Assigned"
    IN_PROGRESS = "In Progress"
    RESOLVED = "Resolved"
    CLOSED = "Closed"


class Priority(StrEnum):
    CRITICAL = "Critical"
    HIGH = "High"
    MEDIUM = "Medium"
    LOW = "Low"
