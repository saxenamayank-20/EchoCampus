import streamlit as st
from app.backend_client import (submit_complaint, get_student_complaints,
                                get_complaint_timeline, auto_detect_priority)
from app.components.ui import (page_header, metric_card, status_badge,
                                priority_badge, render_timeline, render_progress_tracker)
from backend.app.core.constants import CATEGORIES


def render_student_dashboard(user):
    page_header("🎓 Student Portal",
        f"Welcome, {user['name']} &nbsp;|&nbsp; {user['user_id']} &nbsp;|&nbsp; {user.get('department','—')}")

    tab1, tab2, tab3 = st.tabs(["📝  New Complaint", "🎫  My Tickets", "📡  Track Status"])

    # ── TAB 1: NEW COMPLAINT ──────────────────────────────────────────────────
    with tab1:
        st.markdown("#### Submit a New Complaint")
        st.caption("Priority is **automatically set** based on your complaint content — no manual selection needed.")

        with st.form("comp_form", clear_on_submit=True):
            c1, c2 = st.columns([2, 1])
            with c1: title    = st.text_input("Complaint Title *", placeholder="Clear, brief title of your issue")
            with c2: category = st.selectbox("Category *", CATEGORIES)
            description = st.text_area("Description *",
                placeholder="Describe the issue in detail — what happened, when, and where.",
                height=130)
            remarks = st.text_area("Additional Remarks (optional)",
                placeholder="Any supporting info...", height=60)

            # Live preview
            if title or description:
                detected = auto_detect_priority(title or "", description or "", category)
                st.markdown(f"🔍 **Auto-detected priority:** {priority_badge(detected)}", unsafe_allow_html=True)
                if detected == "Critical":
                    st.warning("⚠️ Critical priority — a Google Meet link will be generated and sent to you and your manager.")

            submitted = st.form_submit_button("🚀 Submit Complaint", use_container_width=True, type="primary")

        if submitted:
            if not title.strip() or not description.strip():
                st.error("Please fill in the required fields.")
            else:
                with st.spinner("Submitting..."):
                    ticket_id, mgr_name, priority, meet_link = submit_complaint(
                        user["user_id"], title.strip(), description.strip(), category, remarks.strip())
                st.success("✅ Complaint submitted successfully!")
                st.balloons()

                # Confirmation card
                st.markdown(f"""
                **Ticket ID:** `{ticket_id}` &nbsp; {priority_badge(priority)}

                | Detail | Value |
                |---|---|
                | **Category** | {category} |
                | **Assigned Manager** | {mgr_name} |
                | **Status** | Assigned |
                """, unsafe_allow_html=True)

                if priority == "Critical" and meet_link:
                    st.markdown(f"""
                    <div class="crit" style="margin-top:.75rem;">
                      <h4>🚨 Critical Complaint — Urgent Meeting Scheduled</h4>
                      <p style="margin:0 0 .5rem;font-size:.875rem;">
                        Your complaint has been flagged as <strong>Critical</strong>.
                        An urgent meeting has been arranged with <strong>{mgr_name}</strong>.
                        Please join using the link below.
                      </p>
                      <a href="{meet_link}" target="_blank"
                         style="display:inline-block;background:#dc2626;color:white!important;
                         padding:7px 18px;border-radius:8px;font-size:.875rem;
                         font-weight:700;text-decoration:none;">
                        📹 Join Google Meet
                      </a>
                    </div>""", unsafe_allow_html=True)

    # ── TAB 2: MY TICKETS ─────────────────────────────────────────────────────
    with tab2:
        complaints = get_student_complaints(user["user_id"])
        total    = len(complaints)
        pending  = sum(1 for c in complaints if c["status"]=="Pending")
        active   = sum(1 for c in complaints if c["status"] in ("Assigned","In Progress"))
        resolved = sum(1 for c in complaints if c["status"] in ("Resolved","Closed"))
        critical = sum(1 for c in complaints if c["priority"]=="Critical" and c["status"] not in ("Resolved","Closed"))

        cols = st.columns(5)
        with cols[0]: metric_card("Total",    total,    "blue")
        with cols[1]: metric_card("Pending",  pending,  "amber")
        with cols[2]: metric_card("Active",   active,   "")
        with cols[3]: metric_card("Resolved", resolved, "green")
        with cols[4]: metric_card("Critical", critical, "red")
        st.markdown("<br>", unsafe_allow_html=True)

        if not complaints:
            st.info("No complaints yet. Use the **New Complaint** tab to raise one.")
            return

        f1, f2 = st.columns(2)
        with f1: fs = st.selectbox("Filter by Status",   ["All","Pending","Assigned","In Progress","Resolved","Closed"])
        with f2: fc = st.selectbox("Filter by Category", ["All"] + CATEGORIES)

        filtered = [c for c in complaints
                    if (fs=="All" or c["status"]==fs) and (fc=="All" or c["category"]==fc)]
        st.caption(f"Showing {len(filtered)} of {total}")

        for comp in filtered:
            pri = comp.get("priority","Low")
            with st.expander(f"🎫 {comp['ticket_id']}  •  {comp['title'][:55]}  •  {comp['status']}", expanded=False):
                c1, c2, c3 = st.columns(3)
                with c1:
                    st.markdown(f"**Ticket ID:** `{comp['ticket_id']}`")
                    st.markdown(f"**Category:** {comp['category']}")
                    st.markdown(f"**Status:** {status_badge(comp['status'])}", unsafe_allow_html=True)
                with c2:
                    st.markdown(f"**Priority:** {priority_badge(pri)}", unsafe_allow_html=True)
                    st.markdown(f"**Manager:** {comp.get('manager_name','—')}")
                    st.markdown(f"**Manager ID:** `{comp.get('assigned_to','—')}`")
                with c3:
                    st.markdown(f"**Date Filed:** {str(comp['created_at'])[:10]}")
                    st.markdown(f"**Last Update:** {str(comp['updated_at'])[:10]}")

                st.markdown("**Description:**")
                st.info(comp["description"])
                if comp.get("manager_remarks"):
                    st.success(f"💬 Manager: {comp['manager_remarks']}")
                if comp.get("meet_link"):
                    st.markdown(f"""
                    <div class="crit">
                      <h4>🚨 Critical — Meeting Link</h4>
                      <a href="{comp['meet_link']}" target="_blank">📹 Join Google Meet</a>
                    </div>""", unsafe_allow_html=True)

    # ── TAB 3: TRACK STATUS ───────────────────────────────────────────────────
    with tab3:
        st.markdown("#### 📡 Real-Time Status Tracker")
        complaints = get_student_complaints(user["user_id"])
        options    = [c["ticket_id"] for c in complaints]

        if not options:
            st.info("No complaints to track yet.")
            return

        c1, c2 = st.columns([3, 1])
        with c1: manual   = st.text_input("Enter Ticket ID", placeholder="TKT-ABC12345")
        with c2: selected = st.selectbox("Or pick from list", [""] + options)

        ticket_id = manual.strip().upper() if manual.strip() else selected
        if not ticket_id: return

        comp = next((c for c in complaints if c["ticket_id"] == ticket_id), None)
        if not comp:
            st.error(f"Ticket `{ticket_id}` not found."); return

        pri = comp.get("priority","Low")

        # Header card — using Streamlit native elements instead of HTML
        st.markdown(f"### {comp['ticket_id']} — {comp['title']}")
        hc1, hc2 = st.columns([3, 1])
        with hc1:
            st.markdown(f"{status_badge(comp['status'])} &nbsp; {priority_badge(pri)}", unsafe_allow_html=True)
        with hc2:
            pass

        mc1, mc2, mc3, mc4 = st.columns(4)
        with mc1: st.markdown(f"**Category:** {comp['category']}")
        with mc2: st.markdown(f"**Manager:** {comp.get('manager_name','—')}")
        with mc3: st.markdown(f"**Filed:** {str(comp['created_at'])[:10]}")
        with mc4: st.markdown(f"**Updated:** {str(comp['updated_at'])[:10]}")

        st.divider()

        # Critical meet link
        if pri == "Critical" and comp.get("meet_link"):
            st.markdown(f"""
            <div class="crit">
              <h4>🚨 Critical Priority — Urgent Meeting Required</h4>
              <p style="margin:0 0 .5rem;font-size:.875rem;">
                Please join the urgent meeting with <strong>{comp.get('manager_name','your manager')}</strong> to resolve this immediately.
              </p>
              <a href="{comp['meet_link']}" target="_blank"
                 style="display:inline-block;background:#dc2626;color:white!important;
                 padding:8px 18px;border-radius:8px;font-size:.875rem;font-weight:700;text-decoration:none;">
                📹 Join Google Meet Now
              </a>
            </div>""", unsafe_allow_html=True)

        # Progress tracker
        st.markdown("#### Current Progress")
        render_progress_tracker(comp["status"])

        # Description + response
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("**Your complaint:**")
            st.info(comp["description"])
        with col2:
            st.markdown("**Manager response:**")
            if comp.get("manager_remarks"):
                st.success(comp["manager_remarks"])
            else:
                st.caption("Awaiting manager response...")

        # Timeline
        st.markdown("#### 🕐 Activity Timeline")
        render_timeline(get_complaint_timeline(ticket_id))
