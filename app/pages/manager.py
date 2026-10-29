import streamlit as st
from app.backend_client import (get_manager_complaints, update_complaint_status,
                                get_complaint_timeline, request_close, add_manager_update,
                                manager_status_options)
from app.components.ui import (page_header, metric_card, status_badge,
                                priority_badge, render_timeline, render_progress_tracker)


def render_manager_dashboard(user):
    page_header("📋 Grievance Manager",
        f"{user['name']} &nbsp;|&nbsp; {user['user_id']} &nbsp;|&nbsp; Category: {user.get('category','—')}")

    tab1, tab2 = st.tabs(["📥  Complaints Received", "✅  Resolved Complaints"])

    # ── TAB 1: COMPLAINTS RECEIVED ────────────────────────────────────────────
    with tab1:
        active = get_manager_complaints(user["user_id"], resolved=False)
        c1,c2,c3,c4 = st.columns(4)
        with c1: metric_card("Total Active",  len(active), "blue")
        with c2: metric_card("Critical", sum(1 for c in active if c["priority"]=="Critical"), "red")
        with c3: metric_card("High",     sum(1 for c in active if c["priority"]=="High"), "amber")
        with c4: metric_card("In Progress", sum(1 for c in active if c["status"]=="In Progress"), "")
        st.markdown("<br>", unsafe_allow_html=True)

        if not active:
            st.success("🎉 **All clear!** No active complaints in your queue.")
        else:
            f1, f2 = st.columns(2)
            with f1: fp = st.selectbox("Filter Priority", ["All","Critical","High","Medium","Low"])
            with f2: fs = st.selectbox("Filter Status",   ["All","Assigned","In Progress"])
            filtered = sorted(
                [c for c in active if (fp=="All" or c["priority"]==fp) and (fs=="All" or c["status"]==fs)],
                key=lambda x: ["Critical","High","Medium","Low"].index(x.get("priority","Low")))
            st.caption(f"Showing {len(filtered)} of {len(active)} — only your assigned complaints")

            for comp in filtered:
                pri = comp.get("priority","Low")
                icon = {"Critical":"🔥","High":"🔴","Medium":"🟡","Low":"🟢"}.get(pri,"⚪")
                with st.expander(f"{icon} {comp['ticket_id']}  •  {comp['title'][:52]}  [{comp['status']}]",
                                 expanded=(pri=="Critical")):
                    _complaint_detail(comp, user)

    # ── TAB 2: RESOLVED ───────────────────────────────────────────────────────
    with tab2:
        resolved = get_manager_complaints(user["user_id"], resolved=True)
        c1,c2,c3 = st.columns(3)
        with c1: metric_card("Total Resolved", len(resolved), "green")
        with c2: metric_card("Resolved", sum(1 for c in resolved if c["status"]=="Resolved"), "green")
        with c3: metric_card("Closed by Admin", sum(1 for c in resolved if c["status"]=="Closed"), "")
        st.markdown("<br>", unsafe_allow_html=True)
        st.info("ℹ️ Once a complaint is resolved, use **Request Admin to Close** to officially close it.")

        if not resolved:
            st.caption("No resolved complaints yet.")
            return

        for comp in resolved:
            req = comp.get("close_requested", 0)
            label = f"✅ {comp['ticket_id']}  •  {comp['title'][:52]}  [{comp['status']}]"
            if req: label += "  🔔 Close Requested"
            with st.expander(label, expanded=False):
                c1, c2, c3 = st.columns(3)
                with c1:
                    st.markdown(f"**Student ID:** `{comp['student_id']}`")
                    st.markdown(f"**Category:** {comp['category']}")
                    st.markdown(f"**Priority:** {priority_badge(comp['priority'])}", unsafe_allow_html=True)
                with c2:
                    st.markdown(f"**Status:** {status_badge(comp['status'])}", unsafe_allow_html=True)
                    st.markdown(f"**Filed:** {str(comp['created_at'])[:10]}")
                    st.markdown(f"**Resolved:** {str(comp.get('resolved_at') or '—')[:10]}")
                with c3:
                    if req:
                        st.markdown(f"{status_badge('Pending')}", unsafe_allow_html=True)
                        st.caption("⏳ Awaiting Admin approval")
                    elif comp["status"] != "Closed":
                        if st.button("📤 Request Admin to Close", key=f"req_{comp['ticket_id']}", type="primary"):
                            ok, msg = request_close(comp["ticket_id"], user["user_id"])
                            if ok: st.success(f"✅ {msg}"); st.rerun()
                            else: st.error(msg)

                st.info(comp["description"])
                if comp.get("manager_remarks"):
                    st.success(f"Your note: {comp['manager_remarks']}")
                st.markdown("##### Timeline")
                render_timeline(get_complaint_timeline(comp["ticket_id"]))


def _complaint_detail(comp, user):
    pri = comp.get("priority","Low")

    # Critical banner
    if pri == "Critical":
        meet_btn = (f'<a href="{comp["meet_link"]}" target="_blank" style="display:inline-block;'
                    f'background:#dc2626;color:white!important;padding:6px 14px;border-radius:8px;'
                    f'font-size:.85rem;font-weight:700;text-decoration:none;">📹 Join Meet</a>'
                    if comp.get("meet_link") else "")
        st.markdown(f"""
        <div class="crit">
          <h4>🚨 Critical Priority — Immediate Action Required</h4>
          <p style="margin:0 0 .4rem;font-size:.875rem;">
            This complaint requires urgent attention. A meeting link has been shared with the student.
          </p>
          {meet_btn}
        </div>""", unsafe_allow_html=True)

    # Info row
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown(f"**Ticket:** `{comp['ticket_id']}`")
        st.markdown(f"**Student:** {comp.get('student_name','—')} (`{comp['student_id']}`)")
        st.markdown(f"**Dept:** {comp.get('student_dept','—')}")
    with c2:
        st.markdown(f"**Category:** {comp['category']}")
        st.markdown(f"**Priority:** {priority_badge(pri)}", unsafe_allow_html=True)
        st.markdown(f"**Status:** {status_badge(comp['status'])}", unsafe_allow_html=True)
    with c3:
        st.markdown(f"**Filed:** {str(comp['created_at'])[:10]}")
        st.markdown(f"**Updated:** {str(comp['updated_at'])[:10]}")

    st.markdown("**Description:**")
    st.info(comp["description"])

    render_progress_tracker(comp["status"])
    st.divider()

    col_form, col_upd = st.columns(2)

    with col_form:
        st.markdown("#### Update Status")
        with st.form(f"st_{comp['ticket_id']}"):
            # only the moves the status machine allows, current status first
            ns     = st.selectbox("New Status", manager_status_options(comp["ticket_id"]))
            remark = st.text_area("Remark / Resolution Note",
                                  value=comp.get("manager_remarks",""),
                                  placeholder="Describe action taken...")
            if st.form_submit_button("💾 Save Update", use_container_width=True, type="primary"):
                ok, msg = update_complaint_status(comp["ticket_id"], ns, user["user_id"], remark)
                if ok: st.success(f"✅ {msg}"); st.rerun()
                else: st.error(msg)

    with col_upd:
        st.markdown("#### Post Update to Admin")
        with st.form(f"upd_{comp['ticket_id']}"):
            text = st.text_area("Update message",
                                placeholder="Share a progress update with the Admin...", height=100)
            if st.form_submit_button("📤 Send to Admin", use_container_width=True):
                if text.strip():
                    ok, msg = add_manager_update(comp["ticket_id"], user["user_id"], text.strip())
                    if ok: st.success(msg); st.rerun()
                    else: st.error(msg)
                else: st.warning("Please write a message first.")

    st.markdown("##### 🕐 Timeline")
    render_timeline(get_complaint_timeline(comp["ticket_id"]))
