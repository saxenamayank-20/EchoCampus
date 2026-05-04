import re, time
import streamlit as st
from database.models import login_user, register_student
from config.settings import APP_TITLE, INSTITUTION, validate_password, generate_student_id


def _valid_email(email):
    return bool(re.match(r'^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$', email.strip()))


def render_login():
    _, col, _ = st.columns([1, 1.5, 1])
    with col:
        st.markdown(f"""
        <div style="text-align:center;padding:2rem 0 1.25rem;">
          <div style="font-size:3rem;">🎓</div>
          <h1 style="font-size:1.55rem;font-weight:700;margin:.4rem 0 .2rem;">{APP_TITLE}</h1>
          <p style="font-size:.85rem;margin:0;opacity:.6;">{INSTITUTION}</p>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("#### Sign In")
        with st.form("login_form"):
            user_id  = st.text_input("User ID", placeholder="e.g. ST000101 / GM001 / ADMIN001")
            password = st.text_input("Password", type="password", placeholder="Your password")
            btn      = st.form_submit_button("🔐 Sign In", use_container_width=True, type="primary")

        if btn:
            if not user_id.strip() or not password.strip():
                st.error("Please enter both User ID and Password.")
            else:
                with st.spinner("Authenticating..."):
                    user = login_user(user_id.strip(), password)
                if user:
                    st.session_state["user"] = user
                    st.session_state["page"] = "dashboard"
                    st.rerun()
                else:
                    st.error("❌ Invalid User ID or Password.")

        st.divider()
        st.caption("New student?")
        if st.button("📝 Register as Student", use_container_width=True):
            st.session_state["page"] = "register"
            st.rerun()


def render_register():
    DEPARTMENTS = ["Computer Science","Information Technology","Electronics",
                   "Mechanical","Civil","Electrical","MBA","BBA",
                   "Commerce","Arts","Science","Other"]

    _, col, _ = st.columns([1, 2, 1])
    with col:
        st.markdown("""
        <div style="text-align:center;padding:1.5rem 0 1rem;">
          <div style="font-size:2.5rem;">📝</div>
          <h1 style="font-size:1.4rem;font-weight:700;margin:.4rem 0 .2rem;">Student Registration</h1>
          <p style="font-size:.85rem;margin:0;opacity:.6;">Create your account to raise complaints</p>
        </div>
        """, unsafe_allow_html=True)

        with st.form("reg_form"):
            c1, c2 = st.columns(2)
            with c1:
                name    = st.text_input("Full Name *", placeholder="e.g. Priya Patel")
                # Student ID will be auto-generated
                st.info("📝 Student ID will be auto-generated (e.g., ST000101)")
            with c2:
                email = st.text_input("Email Address *", placeholder="name@domain.com",
                                      help="Must be a valid email — e.g. priya@college.edu")
                dept  = st.selectbox("Department *", DEPARTMENTS)
            c3, c4 = st.columns(2)
            with c3:
                pwd  = st.text_input("Password *", type="password",
                                   placeholder="Min 8 chars: A-Z, a-z, 0-9, !@#$%",
                                   help="Must contain uppercase, lowercase, number, and special character")
            with c4: cpwd = st.text_input("Confirm Password *", type="password")
            btn = st.form_submit_button("🚀 Create Account", use_container_width=True, type="primary")

        if btn:
            errors = []
            if not name.strip():          errors.append("Full name is required.")
            if not email.strip():         errors.append("Email is required.")
            elif not _valid_email(email): errors.append("❌ Invalid email — please use format: name@domain.com")
            if not pwd.strip():           errors.append("Password is required.")
            elif pwd != cpwd:             errors.append("Passwords do not match.")
            else:
                # Validate password strength
                is_valid, pwd_error = validate_password(pwd)
                if not is_valid:          errors.append(pwd_error)

            if errors:
                for e in errors: st.error(e)
            else:
                # Auto-generate student ID
                user_id = generate_student_id()

                with st.spinner("Creating account..."):
                    ok, msg = register_student(user_id, name.strip(),
                                               email.strip().lower(), pwd, dept)
                if ok:
                    st.success(f"✅ Account created! Your Student ID is: **{user_id}**")
                    st.info("📝 Please save this Student ID for future logins.")
                    st.balloons(); time.sleep(2.5)
                    st.session_state["page"] = "login"; st.rerun()
                else:
                    st.error(f"❌ {msg}")

        st.divider()
        if st.button("← Back to Sign In", use_container_width=True):
            st.session_state["page"] = "login"; st.rerun()
