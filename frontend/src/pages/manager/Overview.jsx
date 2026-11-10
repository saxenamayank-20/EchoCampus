import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { AlarmClock, CheckCircle2, Clock, Flame, Hourglass, Inbox, Lock, TriangleAlert } from "lucide-react";
import { api } from "../../api/client";
import { useAuth } from "../../auth/AuthContext";
import { PageHeader, StatCard } from "../../components/Feedback";

const ACTIVE = ["Assigned", "In Progress"];

// just the number of matching complaints (page_size 1, we only read "total")
function useCount(params) {
  return useQuery({
    queryKey: ["complaints", "count", params],
    queryFn: () => api("/complaints", { params: { ...params, page_size: 1 } }).then((r) => r.total),
  });
}

function Box({ to, ...card }) {
  return (
    <Link to={to} className="block rounded-xl transition hover:-translate-y-0.5 hover:shadow-md">
      <StatCard {...card} />
    </Link>
  );
}

function CategoryBox({ category }) {
  const active = useCount({ status: ACTIVE, category });
  const done = useCount({ status: ["Resolved", "Closed"], category });
  return (
    <Link to={`/manager/queue?category=${encodeURIComponent(category)}`}
      className="card block p-4 transition hover:-translate-y-0.5 hover:shadow-md">
      <p className="text-sm font-medium">{category}</p>
      <p className="mt-2 text-2xl font-semibold">{active.data ?? "—"}</p>
      <p className="text-xs text-slate-500">active · {done.data ?? "—"} resolved</p>
    </Link>
  );
}

// the manager's landing page: a few numbers, the lists are under Active / Resolved in the sidebar
export default function ManagerOverview() {
  const { user } = useAuth();
  const active = useCount({ status: ACTIVE });
  const inProgress = useCount({ status: ["In Progress"] });
  const critical = useCount({ status: ACTIVE, priority: "Critical" });
  const high = useCount({ status: ACTIVE, priority: "High" });
  const escalated = useCount({ status: ACTIVE, escalated: true });
  const waiting = useCount({ status: ["Resolved"], close_requested: true });
  const resolved = useCount({ status: ["Resolved"] });
  const closed = useCount({ status: ["Closed"] });

  return (
    <div className="space-y-6">
      <PageHeader title="Complaints" subtitle={`Your categories: ${user.categories?.join(", ") || "—"}`} />

      <div>
        <h2 className="mb-3 text-sm font-semibold text-slate-600 dark:text-slate-300">Needs your work</h2>
        <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
          <Box to="/manager/queue" label="Active" value={active.data} icon={Inbox} tone="brand" />
          <Box to="/manager/queue?status=In%20Progress" label="In progress" value={inProgress.data} icon={Clock} tone="amber" />
          <Box to="/manager/queue?priority=Critical" label="Critical" value={critical.data} icon={Flame} tone="red" />
          <Box to="/manager/queue?priority=High" label="High" value={high.data} icon={TriangleAlert} tone="amber" />
        </div>
      </div>

      <div>
        <h2 className="mb-3 text-sm font-semibold text-slate-600 dark:text-slate-300">Follow-up</h2>
        <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
          <Box to="/manager/queue?escalated=true" label="Escalated (past SLA)" value={escalated.data} icon={AlarmClock} tone="red" />
          <Box to="/manager/queue?tab=resolved&status=Resolved&close_requested=true" label="Waiting for the student" value={waiting.data} icon={Hourglass} />
          <Box to="/manager/queue?tab=resolved&status=Resolved" label="Resolved" value={resolved.data} icon={CheckCircle2} tone="green" />
          <Box to="/manager/queue?tab=resolved&status=Closed" label="Closed" value={closed.data} icon={Lock} />
        </div>
      </div>

      {user.categories?.length > 0 && (
        <div>
          <h2 className="mb-3 text-sm font-semibold text-slate-600 dark:text-slate-300">By category</h2>
          <div className="grid grid-cols-2 gap-3 md:grid-cols-3 lg:grid-cols-4">
            {user.categories.map((c) => <CategoryBox key={c} category={c} />)}
          </div>
        </div>
      )}
    </div>
  );
}
