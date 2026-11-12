from backend.app.core.enums import Priority, Role

APP_TITLE = "EchoCampus"

# staff accounts created by the seed, passwords come from .env
STAFF_ACCOUNTS = [
    {"user_id": "AD100", "name": "Super Admin", "email": "admin@college.edu",
     "role": Role.ADMIN, "department": "Administration"},
    {"user_id": "GM101", "name": "Dr. Rajesh Kumar", "email": "rajesh@college.edu",
     "role": Role.MANAGER, "department": "Academics"},
    {"user_id": "GM102", "name": "Ms. Priya Sharma", "email": "priya@college.edu",
     "role": Role.MANAGER, "department": "Infrastructure"},
    {"user_id": "GM103", "name": "Mr. Anil Verma", "email": "anil@college.edu",
     "role": Role.MANAGER, "department": "Student Affairs"},
    {"user_id": "GM104", "name": "Ms. Sunita Rao", "email": "sunita@college.edu",
     "role": Role.MANAGER, "department": "Finance & Admin"},
]

# which manager handles which category
CATEGORY_MANAGER_MAP = {
    "Academic":       "GM101",
    "Examination":    "GM101",
    "Library":        "GM101",
    "Infrastructure": "GM102",
    "IT/Internet":    "GM102",
    "Hostel":         "GM103",
    "Canteen":        "GM103",
    "Sports":         "GM103",
    "Ragging":        "GM103",
    "Fee/Finance":    "GM104",
    "Administrative": "GM104",
    "Scholarship":    "GM104",
    "Transport":      "GM102",
    "Harassment":     "GM103",
    "Discrimination": "GM103",
    "Other":          "GM102",
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

# some categories are always at least this urgent, whatever words are used (student handbook 15.3)
CATEGORY_MIN_PRIORITY = {
    "Ragging": Priority.CRITICAL,
    "Harassment": Priority.CRITICAL,
    "Discrimination": Priority.CRITICAL,
}

# private complaints: never suggested to other students and nobody can join them
SENSITIVE_CATEGORIES = ("Ragging", "Harassment", "Discrimination")

# critical complaints get a meet link (opens a new meet room)
MANAGER_MEET_LINKS = {
    "GM101": "https://meet.google.com/new",
    "GM102": "https://meet.google.com/new",
    "GM103": "https://meet.google.com/new",
    "GM104": "https://meet.google.com/new",
}

# every user id is exactly 5 characters: students ST101, ST102 ... managers GM101-GM104, admin AD100
STUDENT_ID_PREFIX = "ST"
STUDENT_ID_START = 101
STUDENT_ID_DIGITS = 3        # ST + 3 digits, so the last one is ST999

PASSWORD_MIN_LENGTH = 8
