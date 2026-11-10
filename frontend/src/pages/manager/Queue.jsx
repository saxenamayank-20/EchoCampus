import { Link, useSearchParams } from "react-router-dom";
import { X } from "lucide-react";
import ComplaintTable from "../../components/ComplaintTable";
import { PageHeader } from "../../components/Feedback";

const ACTIVE = ["Assigned", "In Progress"];
const DONE = ["Resolved", "Closed"];

// the overview boxes open this page with a filter in the url, e.g. ?priority=Critical
export default function Queue() {
  const [params] = useSearchParams();
  const resolved = params.get("tab") === "resolved";
  const priority = params.get("priority") || "";
  const category = params.get("category") || "";
  const status = params.get("status");                 // one status, e.g. "In Progress" or "Closed"
  const escalated = params.get("escalated") === "true";
  const waiting = params.get("close_requested") === "true";

  const allowed = resolved ? DONE : ACTIVE;
  const fixed = {
    status: allowed.includes(status) ? [status] : allowed,
    ...(escalated && { escalated: true }),
    ...(waiting && { close_requested: true }),
  };

  // what the box picked, shown above the table so it's clear the list is filtered
  const picked = [
    allowed.includes(status) && status,
    priority, category,
    escalated && "Escalated (past SLA)",
    waiting && "Waiting for the student",
  ].filter(Boolean);
  const base = resolved ? "/manager/queue?tab=resolved" : "/manager/queue";

  return (
    <div>
      <PageHeader
        title={resolved ? "Resolved complaints" : "Active complaints"}
        subtitle={resolved ? "Resolved (waiting for the student or admin) and closed" : "Assigned and In Progress, in your categories"}
      />

      {picked.length > 0 && (
        <p className="mb-3 flex flex-wrap items-center gap-2 text-sm">
          <span className="text-slate-500">Showing:</span>
          {picked.map((p) => (
            <span key={p} className="rounded-full bg-brand-100 px-2.5 py-0.5 font-medium text-brand-800 dark:bg-brand-400/10 dark:text-brand-400">{p}</span>
          ))}
          <Link to={base} className="inline-flex items-center gap-1 text-slate-500 hover:text-slate-800 dark:hover:text-slate-200">
            <X size={14} /> Clear filter
          </Link>
        </p>
      )}

      {/* key = the url, so a new box (or clearing) starts the table fresh with its filters */}
      <ComplaintTable
        key={params.toString()}
        fixed={fixed}
        initial={{ priority, category }}
        statusOptions={[]}
        showStudent
        emptyText={resolved ? "Nothing resolved yet." : "No open complaints right now."}
      />
      {!resolved && (
        <p className="mt-3 text-xs text-slate-500">
          Open a ticket to update its status or post an update for the admin.
        </p>
      )}
    </div>
  );
}
