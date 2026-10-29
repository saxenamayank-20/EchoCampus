import os
import sys

_ = sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import streamlit as st

from app.backend_client import init_db
from app.components.ui import inject_css
from app.pages.admin import render_admin_dashboard
from app.pages.auth import render_login, render_register
from app.pages.manager import render_manager_dashboard
from app.pages.student import render_student_dashboard
from backend.app.core.constants import APP_TITLE

if "page_config_done" not in st.session_state:
    st.set_page_config(
        page_title=APP_TITLE,
        page_icon="🎓",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    st.session_state["page_config_done"] = True

try:
    _ = init_db()
    DB_READY = True
    DB_ERROR = ""
except Exception as exc:
    DB_READY = False
    DB_ERROR = str(exc)

_ = inject_css()

if "page" not in st.session_state:
    st.session_state["page"] = "login"
if "user" not in st.session_state:
    st.session_state["user"] = None


def render_sidebar():
    user = st.session_state["user"]
    role = user["role"]
    icon = {"student": "🎓", "grievance_manager": "📋", "admin": "🛡️"}.get(role, "👤")

    with st.sidebar:
        st.markdown(
            f"""
            <div style="padding:1rem 0 .5rem;text-align:center;">
              <div style="font-size:2rem;">{icon}</div>
              <div style="font-weight:700;font-size:.95rem;margin-top:.4rem;">{user['name']}</div>
              <div style="font-size:.78rem;opacity:.6;margin-top:2px;">{user['user_id']}</div>
              <div style="font-size:.75rem;opacity:.5;margin-top:2px;text-transform:capitalize;">
                {user['role'].replace('_', ' ')}
              </div>
              {"<div style='font-size:.75rem;opacity:.5;margin-top:2px;'>Category: " + user.get('category', '—') + "</div>" if role == "grievance_manager" else ""}
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.divider()

        if role == "student":
            st.markdown("**Navigation**")
            st.markdown("📝 New Complaint")
            st.markdown("🎫 My Tickets")
            st.markdown("📡 Track Status")
        elif role == "grievance_manager":
            st.markdown("**Navigation**")
            st.markdown("📥 Complaints Received")
            st.markdown("✅ Resolved Complaints")
        else:
            st.markdown("**Navigation**")
            st.markdown("📂 All Complaints")
            st.markdown("✅ Resolved & Close Requests")
            st.markdown("📨 Manager Updates")

        st.divider()
        if st.button("🚪 Sign Out", use_container_width=True):
            st.session_state["user"] = None
            st.session_state["page"] = "login"
            st.rerun()


def main():
    if not DB_READY:
        st.error("Database connection failed during startup.")
        st.code(DB_ERROR)
        st.info(
            "SQLite database file will be created automatically on first run. "
            "No additional configuration needed."
        )
        return

    user = st.session_state.get("user")
    page = st.session_state.get("page", "login")

    if not user:
        if page == "register":
            render_register()
        else:
            render_login()
        return

    render_sidebar()
    role = user["role"]
    if role == "student":
        render_student_dashboard(user)
    elif role == "grievance_manager":
        render_manager_dashboard(user)
    elif role == "admin":
        render_admin_dashboard(user)
    else:
        st.error("Unknown role.")


if __name__ == "__main__":
    main()
