from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
from database.models import (login_user, register_student, submit_complaint,
    get_student_complaints, get_manager_complaints, update_complaint_status,
    get_complaint_timeline, get_all_complaints, get_all_users, get_stats,
    request_close, admin_close_complaint, add_manager_update, get_manager_updates)
from config.settings import CATEGORIES, STATUS_FLOW, generate_student_id

app = FastAPI(title="College Complaint Portal API", version="2.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True,
                  allow_methods=["*"], allow_headers=["*"])


class LoginReq(BaseModel):    user_id: str; password: str
class RegisterReq(BaseModel): name: str; email: str; password: str; department: str
class ComplaintReq(BaseModel): student_id: str; title: str; description: str; category: str; remarks: Optional[str]=""
class StatusReq(BaseModel):   ticket_id: str; new_status: str; manager_uid: str; remark: Optional[str]=""
class CloseReq(BaseModel):    ticket_id: str; manager_uid: str
class AdminCloseReq(BaseModel): ticket_id: str; admin_id: str
class UpdateReq(BaseModel):   ticket_id: str; manager_id: str; manager_name: str; update_text: str


@app.post("/auth/login")
async def auth_login(r: LoginReq):
    user = login_user(r.user_id, r.password)
    return {"success": True, "user": user} if user else {"success": False, "error": "Invalid credentials"}

@app.post("/auth/register")
async def auth_register(r: RegisterReq):
    user_id = generate_student_id()
    ok, msg = register_student(user_id, r.name, r.email, r.password, r.department)
    return {"success": ok, "user_id": user_id, "message": msg} if ok else {"success": False, "error": msg}

@app.post("/complaints/submit")
async def submit(r: ComplaintReq):
    try:
        tid, mgr, pri, meet = submit_complaint(r.student_id, r.title, r.description, r.category, r.remarks)
        return {"success": True, "ticket_id": tid, "manager_name": mgr, "priority": pri, "meet_link": meet}
    except Exception as e: raise HTTPException(400, str(e))

@app.get("/complaints/student/{student_id}")
async def get_student(student_id: str):
    return {"success": True, "complaints": get_student_complaints(student_id)}

@app.get("/complaints/manager/{manager_uid}")
async def get_manager(manager_uid: str, resolved: bool = False):
    return {"success": True, "complaints": get_manager_complaints(manager_uid, resolved)}

@app.post("/complaints/update-status")
async def update_status(r: StatusReq):
    ok, msg = update_complaint_status(r.ticket_id, r.new_status, r.manager_uid, r.remark)
    return {"success": ok, "message" if ok else "error": msg}

@app.post("/complaints/request-close")
async def req_close(r: CloseReq):
    request_close(r.ticket_id, r.manager_uid); return {"success": True}

@app.post("/complaints/admin-close")
async def adm_close(r: AdminCloseReq):
    admin_close_complaint(r.ticket_id, r.admin_id); return {"success": True}

@app.post("/complaints/manager-update")
async def post_update(r: UpdateReq):
    add_manager_update(r.ticket_id, r.manager_id, r.manager_name, r.update_text)
    return {"success": True}

@app.get("/complaints/manager-updates")
async def get_updates(): return {"success": True, "updates": get_manager_updates()}

@app.get("/complaints/{ticket_id}/timeline")
async def timeline(ticket_id: str): return {"success": True, "timeline": get_complaint_timeline(ticket_id)}

@app.get("/complaints/all")
async def all_c(): return {"success": True, "complaints": get_all_complaints()}

@app.get("/users")
async def users(role: Optional[str] = None): return {"success": True, "users": get_all_users(role)}

@app.get("/stats")
async def stats(): return {"success": True, "stats": get_stats()}

@app.get("/constants/categories")
async def cats(): return {"success": True, "categories": CATEGORIES}

@app.get("/health")
async def health(): return {"status": "ok", "version": "2.0"}
