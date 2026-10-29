import { Link, useSearchParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { Clock, Flame, Inbox, TriangleAlert } from "lucide-react";
import { api } from "../../api/client";
import { useAuth } from "../../auth/AuthContext";
import ComplaintTable from "../../components/ComplaintTable";
import { PageHeader, StatCard } from "../../components/Feedback";

const ACTIVE = ["Assigned", "In Progress"];
const DONE = ["Resolved", "Closed"];

function useCount(params) {
  return useQuery({
    queryKey: ["complaints", "count", params],
    queryFn: () => api("/complaints", { params: { ...params, page_size: 1 } }).then((r) => r.total),
  });
}

export default function Queue() {
  const { user } = useAuth();
  const [params, setParams] = useSearchParams();
  const resolved = params.get("tab") === "resolved";
  const statuses = resolved ? DONE : ACTIVE;

  const open = useCount({ status: ACTIVE });
  const critical = useCount({ status: ACTIVE, priority: "Critical" });
  const high = useCount({ status: ACTIVE, priority: "High" });
  const inProgress = useCount({ status: ["In Progress"] });

  const tab = (active, label, value) => (
    <button
      onClick={() => setParams(value ? { tab: value } : {})}
      className={`rounded-lg px-3 py-1.5 text-sm ${active ? "bg-white font-medium shadow-sm dark:bg-slate-800" : "text-slate-500"}`}
    >
      {label}
    </button>
  );

  return (
    <div>
      <PageHeader title="Complaints" subtitle={`Your categories: ${user.categories?.join(", ") || "—"}`} />
      <div className="mb-6 grid grid-cols-2 gap-3 lg:grid-cols-4">
        <StatCard label="Open" value={open.data} icon={Inbox} tone="indigo" />
        <StatCard label="Critical" value={critical.data} icon={Flame} tone="red" />
        <StatCard label="High" value={high.data} icon={TriangleAlert} tone="amber" />
        <StatCard label="In progress" value={inProgress.data} icon={Clock} />
      </div>

      <div className="mb-4 inline-flex rounded-xl bg-slate-100 p-1 dark:bg-slate-900">
        {tab(!resolved, "Active", null)}
        {tab(resolved, "Resolved", "resolved")}
      </div>

      {/* key resets paging/filters when switching tabs */}
      <ComplaintTable
        key={resolved ? "done" : "active"}
        fixed={{ status: statuses }}
        statusOptions={[]}
        showStudent
        emptyText={resolved ? "Nothing resolved yet." : "No open complaints right now."}
      />
      {!resolved && (
        <p className="mt-3 text-xs text-slate-500">
          Open a ticket to update its status, post an update for the admin or <Link to="?tab=resolved" className="text-indigo-600">see resolved ones</Link>.
        </p>
      )}
    </div>
  );
}
