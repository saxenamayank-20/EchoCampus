import streamlit as st
import pandas as pd
from app.backend_client import (get_all_complaints_by_category, get_resolved_complaints,
                                admin_close_complaint, get_manager_updates,
                                get_stats, get_complaint_timeline)
from app.components.ui import (page_header, metric_card, status_badge,
                                priority_badge, render_timeline)


def render_admin_dashboard(user):
    page_header("🛡️ Admin Dashboard", f"Welcome, {user['name']} &nbsp;|&nbsp; Full System Control")

    # Top metrics
    stats = get_stats()
    c1,c2,c3,c4,c5,c6 = st.columns(6)
    with c1: metric_card("Total",        stats.get("Total",0),       "blue")
    with c2: metric_card("Pending",      stats.get("Pending",0),     "amber")
    with c3: metric_card("In Progress",  stats.get("In Progress",0), "")
    with c4: metric_card("Resolved",     stats.get("Resolved",0),    "green")
    with c5: metric_card("Close Requests", stats.get("PendingClose",0), "red")
    with c6: metric_card("Open Critical", stats.get("OpenCritical",0), "red")
    st.markdown("<br>", unsafe_allow_html=True)

    tab1, tab2, tab3 = st.tabs([
        "📂  All Complaints",
        "✅  Resolved & Close Requests",
        "📨  Manager Updates",
    ])

    # ── TAB 1: ALL COMPLAINTS BY CATEGORY ────────────────────────────────────
    with tab1:
        st.markdown("#### All Active Complaints — By Category")
        by_cat = get_all_complaints_by_category()

        if not by_cat:
            st.info("No active complaints in the system."); return

        cats       = list(by_cat.keys())
        cat_labels = [f"{cat}  ({len(by_cat[cat])})" for cat in cats]

        if len(cats) == 1:
            _render_cat_complaints(by_cat[cats[0]], cats[0])
        else:
            subtabs = st.tabs(cat_labels)
            for i, cat in enumerate(cats):
                with subtabs[i]:
                    _render_cat_complaints(by_cat[cat], cat)

    # ── TAB 2: RESOLVED & CLOSE REQUESTS ─────────────────────────────────────
    with tab2:
        st.markdown("#### Resolved Complaints & Close Requests")
        resolved = get_resolved_complaints()

        close_reqs   = [c for c in resolved if c.get("close_requested")==1]
        fully_closed = [c for c in resolved if c["status"]=="Closed"]
        res_only     = [c for c in resolved if c["status"]=="Resolved" and not c.get("close_requested")]

        # ── Close request alerts ──
        if close_reqs:
            st.warning(f"🔔 **{len(close_reqs)} Close Request(s) Pending Your Action** — Grievance managers have resolved these and request official closure.")

            for comp in close_reqs:
                with st.expander(f"🔔 CLOSE REQUEST — {comp['ticket_id']}  •  {comp['title'][:50]}", expanded=True):
                    c1, c2, c3 = st.columns(3)
                    with c1:
                        st.markdown(f"**Ticket:** `{comp['ticket_id']}`")
                        st.markdown(f"**Student:** {comp.get('student_name','—')} (`{comp['student_id']}`)")
                        st.markdown(f"**Category:** {comp['category']}")
                    with c2:
                        st.markdown(f"**Priority:** {priority_badge(comp['priority'])}", unsafe_allow_html=True)
                        st.markdown(f"**Manager:** {comp.get('manager_name','—')}")
                        st.markdown(f"**Filed:** {str(comp['created_at'])[:10]}")
                    with c3:
                        if comp.get("manager_remarks"):
                            st.markdown(f"**Manager note:** {comp['manager_remarks'][:80]}...")
                        if st.button("✅ Officially Close", key=f"cls_{comp['ticket_id']}", type="primary"):
                            ok, msg = admin_close_complaint(comp["ticket_id"], user["user_id"])
                            if ok: st.success(msg); st.rerun()
                            else: st.error(msg)

            st.divider()

        # ── Resolved awaiting close request ──
        if res_only:
            st.markdown(f"**Resolved — Awaiting Manager Close Request ({len(res_only)})**")
            for comp in res_only:
                with st.expander(f"✅ {comp['ticket_id']}  •  {comp['title'][:55]}"):
                    c1, c2 = st.columns(2)
                    with c1:
                        st.markdown(f"**Category:** {comp['category']}")
                        st.markdown(f"**Priority:** {priority_badge(comp['priority'])}", unsafe_allow_html=True)
                        st.markdown(f"**Manager:** {comp.get('manager_name','—')}")
                    with c2:
                        st.markdown(f"**Resolved:** {str(comp.get('resolved_at') or '—')[:10]}")
                        st.markdown(f"**Note:** {comp.get('manager_remarks','—')}")
                    if st.button("🔒 Force Close", key=f"fc_{comp['ticket_id']}"):
                        ok, msg = admin_close_complaint(comp["ticket_id"], user["user_id"], force=True)
                        if ok: st.success(msg); st.rerun()
                        else: st.error(msg)
            st.divider()

        # ── Already closed ──
        if fully_closed:
            st.markdown(f"**Officially Closed ({len(fully_closed)})**")
            rows = [{"Ticket ID": c["ticket_id"], "Title": c["title"][:45],
                     "Category": c["category"], "Priority": c["priority"],
                     "Manager": c.get("manager_name","—"),
                     "Closed": str(c.get("resolved_at","—"))[:10]} for c in fully_closed]
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

        if not close_reqs and not res_only and not fully_closed:
            st.info("No resolved complaints yet.")

    # ── TAB 3: MANAGER UPDATES ────────────────────────────────────────────────
    with tab3:
        st.markdown("#### Updates Posted by Grievance Managers")
        updates = get_manager_updates()

        if not updates:
            st.info("No updates from managers yet."); return

        for upd in updates:
            pri = upd.get("priority","Low")
            with st.expander(f"📨 {upd['ticket_id']}  •  {upd.get('manager_name','Manager')}  •  {upd.get('category','—')}", expanded=False):
                mc1, mc2 = st.columns([3, 1])
                with mc1:
                    st.markdown(f"**Manager:** {upd.get('manager_name','Manager')} &nbsp;•&nbsp; `{upd['ticket_id']}` &nbsp;•&nbsp; {upd.get('category','—')}")
                    st.markdown(f"{priority_badge(pri)} &nbsp; {status_badge(upd.get('status','—'))}", unsafe_allow_html=True)
                    st.markdown(f"{upd['update_text']}")
                with mc2:
                    st.caption(str(upd['created_at'])[:16])


def _render_cat_complaints(complaints, category):
    if not complaints:
        st.caption(f"No active complaints in {category}."); return

    total    = len(complaints)
    critical = sum(1 for c in complaints if c["priority"]=="Critical")
    high     = sum(1 for c in complaints if c["priority"]=="High")
    inprog   = sum(1 for c in complaints if c["status"]=="In Progress")

    c1,c2,c3,c4 = st.columns(4)
    with c1: metric_card("Total",       total,    "blue")
    with c2: metric_card("Critical",    critical, "red")
    with c3: metric_card("High",        high,     "amber")
    with c4: metric_card("In Progress", inprog,   "")
    st.markdown("<br>", unsafe_allow_html=True)

    # Sort critical first
    complaints = sorted(complaints, key=lambda x: ["Critical","High","Medium","Low"].index(x.get("priority","Low")))

    for comp in complaints:
        pri  = comp.get("priority","Low")
        icon = {"Critical":"🔥","High":"🔴","Medium":"🟡","Low":"🟢"}.get(pri,"⚪")
        with st.expander(f"{icon} {comp['ticket_id']}  •  {comp['title'][:55]}  •  {comp['status']}", expanded=False):
            c1, c2, c3 = st.columns(3)
            with c1:
                st.markdown(f"**Student:** {comp.get('student_name','—')} (`{comp['student_id']}`)")
                st.markdown(f"**Dept:** {comp.get('student_dept','—')}")
            with c2:
                st.markdown(f"**Priority:** {priority_badge(pri)}", unsafe_allow_html=True)
                st.markdown(f"**Status:** {status_badge(comp['status'])}", unsafe_allow_html=True)
                st.markdown(f"**Manager:** {comp.get('manager_name','—')}")
            with c3:
                st.markdown(f"**Filed:** {str(comp['created_at'])[:10]}")
                st.markdown(f"**Updated:** {str(comp['updated_at'])[:10]}")

            st.markdown("**Description:**")
            st.info(comp["description"])
            if comp.get("manager_remarks"):
                st.success(f"Manager note: {comp['manager_remarks']}")
            if comp.get("meet_link"):
                st.markdown(f"""<div class="crit"><h4>🚨 Critical — Meeting Active</h4>
                <a href="{comp['meet_link']}" target="_blank">📹 Join Google Meet</a>
                </div>""", unsafe_allow_html=True)
            st.markdown("##### Timeline")
            render_timeline(get_complaint_timeline(comp["ticket_id"]))
