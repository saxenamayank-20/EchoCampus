from backend.app.core.enums import Priority, Role

APP_TITLE = "EchoCampus"

# staff accounts created by the seed, passwords come from .env
STAFF_ACCOUNTS = [
    {"user_id": "ADMIN001", "name": "Super Admin", "email": "admin@college.edu",
     "role": Role.ADMIN, "department": "Administration"},
    {"user_id": "GM001", "name": "Dr. Rajesh Kumar", "email": "rajesh@college.edu",
     "role": Role.MANAGER, "department": "Academics"},
    {"user_id": "GM002", "name": "Ms. Priya Sharma", "email": "priya@college.edu",
     "role": Role.MANAGER, "department": "Infrastructure"},
    {"user_id": "GM003", "name": "Mr. Anil Verma", "email": "anil@college.edu",
     "role": Role.MANAGER, "department": "Student Affairs"},
    {"user_id": "GM004", "name": "Ms. Sunita Rao", "email": "sunita@college.edu",
     "role": Role.MANAGER, "department": "Finance & Admin"},
]

# which manager handles which category
CATEGORY_MANAGER_MAP = {
    "Academic":       "GM001",
    "Examination":    "GM001",
    "Library":        "GM001",
    "Infrastructure": "GM002",
    "IT/Internet":    "GM002",
    "Hostel":         "GM003",
    "Canteen":        "GM003",
    "Sports":         "GM003",
    "Ragging":        "GM003",
    "Fee/Finance":    "GM004",
    "Administrative": "GM004",
    "Scholarship":    "GM004",
    "Other":          "GM002",
}
CATEGORIES = list(CATEGORY_MANAGER_MAP)

PRIORITY_KEYWORDS = {
    Priority.CRITICAL: ["ragging", "harassment", "assault", "threat", "violence", "emergency",
                        "critical", "danger", "safety", "abuse", "suicide", "mental health"],
    Priority.HIGH:     ["exam", "result", "fees", "scholarship", "deadline", "not working",
                        "broken", "failed", "error", "blocked", "urgent", "immediately"],
    Priority.MEDIUM:   ["internet", "wifi", "library", "hostel", "canteen", "maintenance",
                        "repair", "issue", "problem", "concern"],
}

# critical complaints get a meet link (opens a new meet room)
MANAGER_MEET_LINKS = {
    "GM001": "https://meet.google.com/new",
    "GM002": "https://meet.google.com/new",
    "GM003": "https://meet.google.com/new",
    "GM004": "https://meet.google.com/new",
}

# student ids look like ST000101, ST000102 ...
STUDENT_ID_PREFIX = "ST"
STUDENT_ID_START = 101

PASSWORD_MIN_LENGTH = 8
