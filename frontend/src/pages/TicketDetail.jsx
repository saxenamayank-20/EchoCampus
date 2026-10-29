import { useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { AlertTriangle, ArrowLeft, Video } from "lucide-react";
import { api } from "../api/client";
import { useAuth } from "../auth/AuthContext";
import Attachments from "../components/Attachments";
import { PriorityBadge, StatusBadge } from "../components/Badges";
import { ErrorBox, Skeleton } from "../components/Feedback";
import Modal from "../components/Modal";
import { ProgressTracker, Timeline } from "../components/Timeline";
import { useToast } from "../components/Toast";
import { formatDate, formatDateTime } from "../lib/format";

function Section({ title, children, className = "" }) {
  return (
    <section className={`card p-5 ${className}`}>
      <h2 className="mb-4 font-semibold">{title}</h2>
      {children}
    </section>
  );
}

function Info({ label, children }) {
  return (
    <div>
      <dt className="text-xs text-slate-500">{label}</dt>
      <dd className="mt-0.5 text-sm">{children}</dd>
    </div>
  );
}

// refresh everything that shows this ticket after a change
function useRefresh(ticketId) {
  const queryClient = useQueryClient();
  return () => {
    queryClient.invalidateQueries({ queryKey: ["ticket", ticketId] });
    queryClient.invalidateQueries({ queryKey: ["timeline", ticketId] });
    queryClient.invalidateQueries({ queryKey: ["status-options", ticketId] });
    queryClient.invalidateQueries({ queryKey: ["complaints"] });
  };
}

function ManagerPanel({ complaint }) {
  const toast = useToast();
  const refresh = useRefresh(complaint.ticket_id);
  const t = complaint.ticket_id;
  const options = useQuery({ queryKey: ["status-options", t], queryFn: () => api(`/manager/complaints/${t}/status-options`) });
  const [status, setStatus] = useState(complaint.status);
  const [remark, setRemark] = useState(complaint.manager_remarks ?? "");
  const [update, setUpdate] = useState("");

  const onError = (e) => toast.error(e.message);
  const save = useMutation({
    mutationFn: () => api(`/manager/complaints/${t}/status`, { method: "POST", body: { status, remark } }),
    onSuccess: () => { toast.success("Saved. The student was emailed."); refresh(); },
    onError,
  });
  const send = useMutation({
    mutationFn: () => api(`/manager/complaints/${t}/updates`, { method: "POST", body: { text: update } }),
    onSuccess: () => { toast.success("Update sent to the admin."); setUpdate(""); },
    onError,
  });
  const closeRequest = useMutation({
    mutationFn: () => api(`/manager/complaints/${t}/close-request`, { method: "POST" }),
    onSuccess: () => { toast.success("Close request sent to the admin."); refresh(); },
    onError,
  });

  if (complaint.status === "Closed") return null;
  return (
    <Section title="Manager actions">
      <div className="grid gap-6 md:grid-cols-2">
        <form onSubmit={(e) => { e.preventDefault(); save.mutate(); }} className="space-y-3">
          <div>
            <label className="label" htmlFor="ns">Status</label>
            {/* only the moves the status machine allows */}
            <select id="ns" className="input" value={status} onChange={(e) => setStatus(e.target.value)}>
              {(options.data ?? [complaint.status]).map((s) => <option key={s}>{s}</option>)}
            </select>
          </div>
          <div>
            <label className="label" htmlFor="rm">Remark for the student</label>
            <textarea id="rm" rows={3} className="input" value={remark} onChange={(e) => setRemark(e.target.value)} placeholder="What was done?" />
          </div>
          <button className="btn-primary" disabled={save.isPending}>{save.isPending ? "Saving…" : "Save"}</button>
        </form>

        <div className="space-y-5">
          <form onSubmit={(e) => { e.preventDefault(); send.mutate(); }} className="space-y-3">
            <label className="label" htmlFor="up">Update for the admin</label>
            <textarea id="up" rows={3} className="input" value={update} onChange={(e) => setUpdate(e.target.value)} placeholder="Progress note…" />
            <button className="btn-secondary" disabled={!update.trim() || send.isPending}>Send to admin</button>
          </form>
          {complaint.status === "Resolved" && (
            <div className="rounded-lg border border-slate-200 p-3 dark:border-slate-800">
              {complaint.close_requested ? (
                <p className="text-sm text-amber-600">Close request sent, waiting for the admin.</p>
              ) : (
                <>
                  <p className="mb-2 text-sm text-slate-500">Fixed for good? Ask the admin to close it.</p>
                  <button className="btn-primary" onClick={() => closeRequest.mutate()} disabled={closeRequest.isPending}>
                    Request closure
                  </button>
                </>
              )}
            </div>
          )}
        </div>
      </div>
    </Section>
  );
}

function AdminPanel({ complaint }) {
  const toast = useToast();
  const refresh = useRefresh(complaint.ticket_id);
  const [confirmForce, setConfirmForce] = useState(false);
  const close = useMutation({
    mutationFn: (force) => api(`/admin/complaints/${complaint.ticket_id}/close`, { method: "POST", body: { force } }),
    onSuccess: () => { toast.success("Complaint closed."); setConfirmForce(false); refresh(); },
    onError: (e) => toast.error(e.message),
  });

  if (complaint.status !== "Resolved") return null;
  return (
    <Section title="Admin actions">
      {complaint.close_requested ? (
        <div className="flex flex-wrap items-center justify-between gap-3">
          <p className="text-sm">The manager resolved this and asked to close it.</p>
          <button className="btn-primary" onClick={() => close.mutate(false)} disabled={close.isPending}>Officially close</button>
        </div>
      ) : (
        <div className="flex flex-wrap items-center justify-between gap-3">
          <p className="text-sm text-slate-500">Resolved, but the manager hasn't asked to close it yet.</p>
          <button className="btn-danger" onClick={() => setConfirmForce(true)}>Force close</button>
        </div>
      )}
      {confirmForce && (
        <Modal title="Force close?" onClose={() => setConfirmForce(false)}>
          <p className="mb-4 text-sm text-slate-600 dark:text-slate-300">
            This closes the ticket without the manager's close request. It will show as "Admin Force Closed" in the timeline.
          </p>
          <div className="flex justify-end gap-2">
            <button className="btn-secondary" onClick={() => setConfirmForce(false)}>Cancel</button>
            <button className="btn-danger" onClick={() => close.mutate(true)} disabled={close.isPending}>Force close</button>
          </div>
        </Modal>
      )}
    </Section>
  );
}

export default function TicketDetail() {
  const { ticketId } = useParams();
  const { user } = useAuth();
  const navigate = useNavigate();
  const ticket = useQuery({ queryKey: ["ticket", ticketId], queryFn: () => api(`/complaints/${ticketId}`) });
  const timeline = useQuery({ queryKey: ["timeline", ticketId], queryFn: () => api(`/complaints/${ticketId}/timeline`) });

  if (ticket.isLoading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-8 w-64" />
        <Skeleton className="h-32 w-full" />
        <Skeleton className="h-64 w-full" />
      </div>
    );
  }
  if (ticket.error) return <ErrorBox error={ticket.error} />;

  const c = ticket.data;
  const isOwner = user.role === "student" && c.student_id === user.user_id;
  const isAssigned = user.role === "grievance_manager" && c.assigned_to === user.user_id;

  return (
    <div className="space-y-5">
      <button onClick={() => navigate(-1)} className="inline-flex items-center gap-1 text-sm text-slate-500 hover:text-slate-800 dark:hover:text-slate-200">
        <ArrowLeft size={16} /> Back
      </button>

      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="font-mono text-xs text-slate-500">{c.ticket_id}</p>
          <h1 className="mt-1 text-xl font-semibold sm:text-2xl">{c.title}</h1>
        </div>
        <div className="flex gap-2">
          <PriorityBadge priority={c.priority} />
          <StatusBadge status={c.status} />
        </div>
      </div>

      {c.priority === "Critical" && c.meet_link && c.status !== "Closed" && (
        <div className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-red-200 bg-red-50 p-4 text-red-800 dark:border-red-900 dark:bg-red-950 dark:text-red-200">
          <p className="flex items-center gap-2 text-sm font-medium"><AlertTriangle size={18} /> Critical complaint, an urgent meeting is set up.</p>
          <a href={c.meet_link} target="_blank" rel="noreferrer" className="btn bg-red-600 text-white hover:bg-red-700">
            <Video size={16} /> Join Google Meet
          </a>
        </div>
      )}

      <section className="card p-5">
        <ProgressTracker status={c.status} />
      </section>

      <div className="grid gap-5 lg:grid-cols-3">
        <div className="space-y-5 lg:col-span-2">
          <Section title="Details">
            <dl className="mb-4 grid grid-cols-2 gap-4 sm:grid-cols-3">
              <Info label="Category">{c.category}</Info>
              <Info label="Student">{c.student_name} ({c.student_id})</Info>
              <Info label="Department">{c.student_dept ?? "—"}</Info>
              <Info label="Manager">{c.manager_name ?? "Not assigned yet"}</Info>
              <Info label="Filed">{formatDate(c.created_at)}</Info>
              <Info label="Last update">{formatDateTime(c.updated_at)}</Info>
            </dl>
            <p className="whitespace-pre-wrap rounded-lg bg-slate-50 p-3 text-sm dark:bg-slate-800/60">{c.description}</p>
            {c.student_remarks && <p className="mt-3 text-sm text-slate-500">Student remarks: {c.student_remarks}</p>}
            {c.manager_remarks && (
              <p className="mt-3 rounded-lg border border-emerald-200 bg-emerald-50 p-3 text-sm text-emerald-800 dark:border-emerald-900 dark:bg-emerald-950 dark:text-emerald-200">
                Manager: {c.manager_remarks}
              </p>
            )}
          </Section>

          {isAssigned && <ManagerPanel key={c.status} complaint={c} />}
          {user.role === "admin" && <AdminPanel complaint={c} />}

          <Section title="Proof">
            <Attachments ticketId={c.ticket_id} canUpload={(isOwner || isAssigned) && c.status !== "Closed"} />
          </Section>
        </div>

        <Section title="Timeline" className="h-fit">
          {timeline.isLoading ? <Skeleton className="h-40 w-full" /> : <Timeline events={timeline.data} />}
        </Section>
      </div>
    </div>
  );
}
