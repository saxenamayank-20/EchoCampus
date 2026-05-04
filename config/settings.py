import os
import re
from dotenv import load_dotenv

_ = load_dotenv()

try:
    import streamlit as st
except Exception:
    st = None


# ─── USER PASSWORDS (Hardcoded for simplicity) ───────────────────────────────
# These are used for Admin and Grievance Managers

ADMIN_SEED_PASSWORD = "Admin@2026#Secure"
GM001_PASSWORD = "RajeshKumar@2026#Secure"
GM002_PASSWORD = "PriyaSharma@2026#Secure"
GM003_PASSWORD = "AnilVerma@2026#Secure"
GM004_PASSWORD = "SunitaRao@2026#Secure"

# ─── PREDEFINED USERS (Admin + 4 Grievance Managers) ─────────────────────────
# Format: (user_id, full_name, email, password, role, department, category)
# Seed passwords come from environment variables so they do not need to live in Git.

PREDEFINED_USERS = [
    # ── ADMIN ──────────────────────────────────────────────────────────────────
    ("ADMIN001", "Super Admin",       "admin@college.edu",   ADMIN_SEED_PASSWORD,   "admin",            "Administration",  None),

    # ── GRIEVANCE MANAGERS ──────────────────────────────────────────────────────
    ("GM001",    "Dr. Rajesh Kumar",  "rajesh@college.edu",  GM001_PASSWORD,        "grievance_manager", "Academics",       "Academic"),
    ("GM002",    "Ms. Priya Sharma",  "priya@college.edu",   GM002_PASSWORD,        "grievance_manager", "Infrastructure",  "Infrastructure"),
    ("GM003",    "Mr. Anil Verma",    "anil@college.edu",    GM003_PASSWORD,        "grievance_manager", "Student Affairs", "Hostel/Canteen"),
    ("GM004",    "Ms. Sunita Rao",    "sunita@college.edu",  GM004_PASSWORD,        "grievance_manager", "Finance & Admin", "Administrative/Finance"),
]

# ─── CATEGORY → MANAGER MAPPING ───────────────────────────────────────────────
CATEGORY_MANAGER_MAP = {
    "Academic":              "GM001",
    "Examination":           "GM001",
    "Library":               "GM001",
    "Infrastructure":        "GM002",
    "IT/Internet":           "GM002",
    "Hostel":                "GM003",
    "Canteen":               "GM003",
    "Sports":                "GM003",
    "Ragging":               "GM003",
    "Fee/Finance":           "GM004",
    "Administrative":        "GM004",
    "Scholarship":           "GM004",
    "Other":                 "GM002",
}

CATEGORIES  = list(dict.fromkeys(CATEGORY_MANAGER_MAP.keys()))
STATUS_FLOW = ["Pending", "Assigned", "In Progress", "Resolved", "Closed"]

# ─── PRIORITY AUTO-DETECTION ──────────────────────────────────────────────────
PRIORITY_KEYWORDS = {
    "Critical": ["ragging","harassment","assault","threat","violence","emergency",
                 "critical","danger","safety","abuse","suicide","mental health"],
    "High":     ["exam","result","fees","scholarship","deadline","not working",
                 "broken","failed","error","blocked","urgent","immediately"],
    "Medium":   ["internet","wifi","library","hostel","canteen","maintenance",
                 "repair","issue","problem","concern"],
}
DEFAULT_PRIORITY = "Low"

# ─── GOOGLE MEET (Critical complaints) ───────────────────────────────────────
# Opens a new Meet session. Replace with fixed room links if preferred.
MANAGER_MEET_LINKS = {
    "GM001": "https://meet.google.com/new",
    "GM002": "https://meet.google.com/new",
    "GM003": "https://meet.google.com/new",
    "GM004": "https://meet.google.com/new",
}

APP_TITLE   = "College Complaint Portal"

# ─── STUDENT USER ID FORMAT ──────────────────────────────────────────────────
# Student IDs will be auto-generated as ST000101, ST000102, etc.
STUDENT_ID_PREFIX = "ST"
STUDENT_ID_START = 101  # Starting number for student IDs

# ─── PASSWORD REQUIREMENTS ───────────────────────────────────────────────────
PASSWORD_MIN_LENGTH = 8
PASSWORD_REQUIREMENTS = {
    "uppercase": True,    # At least one uppercase letter
    "lowercase": True,    # At least one lowercase letter
    "digit": True,        # At least one digit
    "special": True,      # At least one special character
}

# ─── PASSWORD VALIDATION ─────────────────────────────────────────────────────
def validate_password(password):
    """
    Validate password against requirements.
    Returns (is_valid, error_message)
    """
    if len(password) < PASSWORD_MIN_LENGTH:
        return False, f"Password must be at least {PASSWORD_MIN_LENGTH} characters long."

    errors = []

    if PASSWORD_REQUIREMENTS["uppercase"] and not re.search(r'[A-Z]', password):
        errors.append("at least one uppercase letter")

    if PASSWORD_REQUIREMENTS["lowercase"] and not re.search(r'[a-z]', password):
        errors.append("at least one lowercase letter")

    if PASSWORD_REQUIREMENTS["digit"] and not re.search(r'\d', password):
        errors.append("at least one number")

    if PASSWORD_REQUIREMENTS["special"] and not re.search(r'[!@#$%^&*()_+\-=\[\]{};\':"\\|,.<>\/?]', password):
        errors.append("at least one special character")

    if errors:
        return False, f"Password must contain {', '.join(errors)}."

    return True, "Password is valid."

# ─── STUDENT ID GENERATION ───────────────────────────────────────────────────
def generate_student_id():
    """
    Generate next available student ID in format ST000101, ST000102, etc.
    """
    from database.connection import get_connection

    conn = get_connection()
    c = conn.cursor()

    try:
        # Find the highest existing student ID using numeric ordering
        c.execute("""
            SELECT user_id FROM users
            WHERE role='student' AND user_id LIKE ?
            ORDER BY CAST(SUBSTRING(user_id, 3) AS UNSIGNED) DESC
            LIMIT 1
        """, (f"{STUDENT_ID_PREFIX}%",))
        row = c.fetchone()

        if row:
            # Extract number from existing ID (e.g., ST000105 -> 105)
            existing_id = row["user_id"]
            try:
                current_num = int(existing_id[len(STUDENT_ID_PREFIX):])
                next_num = current_num + 1
            except ValueError:
                next_num = STUDENT_ID_START
        else:
            next_num = STUDENT_ID_START

        # Format as ST000101, ST000102, etc.
        new_id = f"{STUDENT_ID_PREFIX}{next_num:06d}"

        # Double-check that this ID doesn't already exist (safety check)
        c.execute("SELECT 1 FROM users WHERE user_id=?", (new_id,))
        if c.fetchone():
            # If it exists, increment and try again (shouldn't happen with proper ordering)
            next_num += 1
            new_id = f"{STUDENT_ID_PREFIX}{next_num:06d}"

        return new_id

    except Exception as e:
        # Fallback to start number if database error
        return f"{STUDENT_ID_PREFIX}{STUDENT_ID_START:06d}"
    finally:
        conn.close()
