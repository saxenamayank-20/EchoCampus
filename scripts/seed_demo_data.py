"""Fill the database with realistic demo data for the viva: students, ~60 complaints over the
last 30 days (with groups of near-duplicates), some in progress / resolved / closed, and supporters.

Run from the repo root (tables must exist):
    python scripts/seed_demo_data.py            # with ai embeddings (one batched call)
    python scripts/seed_demo_data.py --no-ai    # without ai

It refuses to run if complaints already exist, so it can't mess up real data.
Demo students log in with password Student@123.
"""
import os
import random
import sys
from datetime import timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import func, select

from backend.app.agents.checkpointer import get_checkpointer
from backend.app.ai.embeddings import complaint_text
from backend.app.ai.llm_client import DisabledClient, LLMError, get_llm
from backend.app.core.config import settings
from backend.app.db.seed import seed_staff
from backend.app.db.session import SessionLocal
from backend.app.models import Complaint, ComplaintSupporter, User
from backend.app.services.complaint_service import ComplaintService
from backend.app.services.user_service import UserService

STUDENTS = [("Riya Sharma", "Computer Science"), ("Kabir Mehta", "Mechanical"), ("Ananya Iyer", "Electronics"),
            ("Arjun Nair", "Civil"), ("Sneha Gupta", "MBA"), ("Rohan Das", "Information Technology"),
            ("Ishita Verma", "BBA"), ("Aditya Singh", "Electrical"), ("Meera Pillai", "Commerce"),
            ("Vikram Joshi", "Science")]

# (title, description, category). lines in the same group say the same thing in different words
COMPLAINTS = [
    # wifi cluster
    ("Wifi not working in hostel block B", "No internet in block B rooms since Monday evening.", "IT/Internet"),
    ("Hostel B wifi down", "The wifi in hostel block B has been down for two days, cannot submit assignments.", "IT/Internet"),
    ("No internet in block B hostel", "Block B hostel internet keeps disconnecting every few minutes.", "IT/Internet"),
    # mess food cluster
    ("Stale food served in mess", "Dinner served yesterday in the main mess was stale and smelled bad.", "Canteen"),
    ("Mess food quality is bad", "Food in the mess has been stale for the last week, many students fell sick.", "Canteen"),
    ("Canteen serving old food", "The canteen is reheating old food from the previous day.", "Canteen"),
    # projector cluster
    ("Projector not working in room 204", "The projector in classroom 204 does not turn on.", "Infrastructure"),
    ("Room 204 projector broken", "Teachers cannot show slides in room 204 because the projector is broken.", "Infrastructure"),
    # results cluster
    ("Semester 5 result not shown", "My semester 5 result is missing on the student portal.", "Examination"),
    ("Result not visible on portal", "Sem 5 results are not showing on the portal for our batch.", "Examination"),
    # scholarship cluster
    ("Scholarship amount not credited", "Merit scholarship not credited yet even after verification.", "Scholarship"),
    ("Merit scholarship delayed", "It has been two months and the merit scholarship has not come.", "Scholarship"),
    # singles
    ("Ragging in hostel block A", "Seniors force first years to do their laundry late at night.", "Ragging"),
    ("Library books wrongly marked", "Library system shows a book I returned last week as overdue.", "Library"),
    ("Water cooler needs cleaning", "The water cooler near the gym is dirty.", "Other"),
    ("Fee receipt not generated", "I paid the semester fee online but no receipt was generated.", "Fee/Finance"),
    ("Broken bench in lab 3", "Two benches in physics lab 3 are broken.", "Infrastructure"),
    ("Gym equipment broken", "The treadmill in the sports complex has been broken for weeks.", "Sports"),
    ("Late fee charged wrongly", "A late fee was added even though I paid before the deadline.", "Fee/Finance"),
    ("Exam timetable clash", "Two of my exams are scheduled at the same time on the 14th.", "Examination"),
    ("Hostel room fan not working", "The ceiling fan in room 112, hostel C, does not work.", "Hostel"),
    ("Bonafide certificate delayed", "Applied for a bonafide certificate three weeks ago, still not issued.", "Administrative"),
    ("Assignment marks missing", "Marks for the data structures assignment are not uploaded.", "Academic"),
    ("Street lights off near hostel", "The road between the library and hostel is dark at night, feels unsafe.", "Infrastructure"),
    ("Washroom tap leaking", "The tap in the ground floor washroom of block D keeps leaking.", "Hostel"),
    ("Sports ground not maintained", "The football ground is full of stones and puddles.", "Sports"),
    ("Lab computers very slow", "Computers in the CS lab take ten minutes to start.", "IT/Internet"),
    ("Attendance marked absent wrongly", "I was marked absent for a lecture I attended on Friday.", "Academic"),
    ("Hostel curfew too strict", "Hostel gate closes at 9 pm even on weekends, library is open till 10.", "Hostel"),
    ("Canteen too crowded at lunch", "There are only two counters and the lunch queue takes 30 minutes.", "Canteen"),
    ("Exam hall too hot", "There were no working fans in the exam hall during the midterms.", "Examination"),
    ("Refund not received", "Caution deposit refund not received after leaving the hostel.", "Fee/Finance"),
    ("Online portal login error", "The student portal shows an error when I try to log in.", "IT/Internet"),
    ("Library closes early", "The library closes at 6 pm, students need it till late during exams.", "Library"),
    ("Drinking water not available", "No drinking water on the third floor of the main building.", "Infrastructure"),
    ("ID card not issued", "My student ID card has not been issued even after two months.", "Administrative"),
    ("Harassment by a senior", "A senior keeps sending threatening messages, I feel unsafe.", "Harassment"),
    ("Practical exam rescheduled without notice", "Our chemistry practical was moved without telling us.", "Examination"),
    ("Hostel mess timings", "Breakfast ends at 8 am, before early lectures we cannot eat.", "Canteen"),
    ("Classroom AC leaking", "The AC in room 301 drips water on the benches.", "Infrastructure"),
    ("Library wifi slow", "Wifi in the library reading room is too slow to download papers.", "IT/Internet"),
    ("Transport bus late", "The college bus on route 4 is late every day by 20 minutes.", "Transport"),
    ("Scholarship form not accepted", "The portal rejects my scholarship form without any error message.", "Scholarship"),
    ("Mentor not available", "My assigned mentor has not replied to any email this semester.", "Academic"),
    ("Medical room closed", "The medical room was closed when a student fainted in the afternoon.", "Other"),
    # more near-duplicates so clusters show in the demo
    ("Mess food stale again", "Stale and smelly food served in the mess at dinner, several students sick.", "Canteen"),
    ("Wifi down in block B", "Block B hostel rooms have no wifi since Monday night.", "IT/Internet"),
    ("Projector 204 still broken", "The classroom 204 projector does not switch on, lectures affected.", "Infrastructure"),
    ("Scholarship not received yet", "Merit scholarship still not credited after verification was done.", "Scholarship"),
    ("Street lights not working", "Street lights between the library and the hostel are off, it is dark and unsafe.", "Infrastructure"),
    ("Bus route 4 always late", "Route 4 college bus reaches 20 minutes late every morning.", "Transport"),
    ("Exam clash on 14th", "My two exams are at the same time on the 14th, please reschedule.", "Examination"),
    # more singles
    ("Lab safety goggles missing", "There are no safety goggles in chemistry lab 2.", "Infrastructure"),
    ("Hostel hot water not working", "No hot water in hostel C bathrooms for a week.", "Hostel"),
    ("Grade sheet name spelling wrong", "My name is spelled wrong on the semester grade sheet.", "Examination"),
    ("Library e-journal access not working", "Cannot open online journals from the hostel network.", "Library"),
    ("Basketball court lights broken", "Floodlights on the basketball court are broken, no evening practice.", "Sports"),
    ("Fee portal double charged", "The fee portal charged my card twice for the same payment.", "Fee/Finance"),
    ("Migration certificate pending", "Requested a migration certificate a month ago, no update.", "Administrative"),
    ("Discrimination by a staff member", "A staff member keeps making remarks about my region, I feel targeted.", "Discrimination"),
]


def main() -> int:
    use_ai = "--no-ai" not in sys.argv
    llm = get_llm() if use_ai else DisabledClient()
    settings.rate_limit_complaints_per_hour = 10_000      # this script submits many at once
    rng = random.Random(7)                                # same demo data every time
    get_checkpointer()      # before the session opens: its first setup waits for open transactions

    with SessionLocal() as db:
        if db.scalar(select(func.count()).select_from(Complaint)):
            print("[DEMO] complaints already exist, not adding demo data.")
            return 1
        seed_staff(db, settings.seed_passwords())
        users = UserService(db)
        students = []
        for i, (name, dept) in enumerate(STUDENTS):
            s = users.register_student(name, f"{name.split()[0].lower()}.demo{i}@college.edu", "Student@123", dept)
            s.is_verified = True
            students.append(s)
        db.commit()

        service = ComplaintService(db)          # no ai per complaint: keyword priority, saves the free quota
        made = []
        for i, (title, desc, cat) in enumerate(COMPLAINTS):
            c = service.submit(students[i % len(students)], title, desc, cat)
            # spread over the last 30 days so the trend chart has a shape
            back = timedelta(days=rng.randint(0, 29), hours=rng.randint(0, 20))
            for h in c.history:
                h.timestamp -= back
            c.created_at -= back
            c.updated_at -= back
            c.sla_due_at -= back
            made.append(c)
        db.commit()

        if use_ai:
            # one batched embedding call for all complaints (the client also caches them)
            try:
                vectors = llm.embed("embedding", [complaint_text(c.title, c.description) for c in made])
                for c, v in zip(made, vectors, strict=True):
                    c.embedding = v
                db.commit()
                print(f"[DEMO] embeddings saved for {len(made)} complaints")
            except LLMError as e:
                print(f"[DEMO] no embeddings ({e}), duplicates won't show for demo data")

        managers = {u.user_id: u for u in db.scalars(select(User).where(User.role == "grievance_manager"))}
        admin = users.get("AD100")

        def manager_of(c):
            return managers.get(c.manager.user_id) if c.manager else None

        # move some along the status flow
        for c in made[12:24]:
            if manager_of(c):
                service.update_status(c.ticket_id, "In Progress", manager_of(c), "Looking into it")
        for c in made[24:32]:
            m = manager_of(c)
            if m:
                service.update_status(c.ticket_id, "In Progress", m, "Assigned to the team")
                service.update_status(c.ticket_id, "Resolved", m, "Fixed and checked")
        for c in made[24:28]:
            m = manager_of(c)
            if m:
                service.request_close(c.ticket_id, m, "Fixed and checked on site")
                service.student_respond(c.ticket_id, c.student, fixed=True, rating=rng.randint(3, 5))
                service.admin_close(c.ticket_id, admin)
        # supporters on the clusters
        for first, others in [(0, [3, 6, 9]), (3, [1, 4]), (6, [2])]:
            for k in others:
                if made[first].student_id != students[k].id:
                    db.add(ComplaintSupporter(complaint=made[first], student=students[k]))
        db.commit()
        print(f"[DEMO] {len(students)} students (password Student@123), {len(made)} complaints added")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
