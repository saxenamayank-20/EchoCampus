import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { CheckCircle2, Clock, Flame, Ticket, Users } from "lucide-react";
import { api } from "../../api/client";
import ComplaintTable from "../../components/ComplaintTable";
import { StatusBadge } from "../../components/Badges";
import { PageHeader, StatCard } from "../../components/Feedback";
import { STATUSES } from "../../lib/format";

function useCount(params) {
  return useQuery({
    queryKey: ["complaints", "count", params],
    queryFn: () => api("/complaints", { params: { ...params, page_size: 1 } }).then((r) => r.total),
  });
}

export default function MyTickets() {
  const total = useCount({});
  const active = useCount({ status: ["Pending", "Assigned", "In Progress"] });
  const done = useCount({ status: ["Resolved", "Closed"] });
  const critical = useCount({ priority: "Critical", status: ["Pending", "Assigned", "In Progress"] });

  return (
    <div>
      <PageHeader
        title="My tickets"
        subtitle="Everything you've raised and where it stands"
        actions={<Link to="/student/new" className="btn-primary">New complaint</Link>}
      />
      <div className="mb-6 grid grid-cols-2 gap-3 lg:grid-cols-4">
        <StatCard label="Total" value={total.data} icon={Ticket} tone="indigo" />
        <StatCard label="Active" value={active.data} icon={Clock} tone="amber" />
        <StatCard label="Resolved / closed" value={done.data} icon={CheckCircle2} tone="green" />
        <StatCard label="Open critical" value={critical.data} icon={Flame} tone="red" />
      </div>
      <ComplaintTable statusOptions={STATUSES} showManager emptyText="You haven't raised any complaints yet." />
      <Supporting />
    </div>
  );
}

// complaints by other students that this student said "I have this issue too" on
function Supporting() {
  const { data = [] } = useQuery({ queryKey: ["complaints", "supporting"], queryFn: () => api("/complaints/supporting") });
  if (!data.length) return null;
  return (
    <div className="card mt-6 overflow-hidden">
      <h2 className="flex items-center gap-2 border-b border-slate-200 px-5 py-3 text-sm font-semibold dark:border-slate-800">
        <Users size={16} /> Complaints I support
      </h2>
      <ul className="divide-y divide-slate-100 dark:divide-slate-800">
        {data.map((c) => (
          <li key={c.ticket_id}>
            <Link to={`/tickets/${c.ticket_id}`} className="flex flex-wrap items-center gap-2 px-5 py-3 text-sm hover:bg-slate-50 dark:hover:bg-slate-800/40">
              <span className="font-mono text-xs text-indigo-600">{c.ticket_id}</span>
              <span className="min-w-0 flex-1 truncate">{c.title}</span>
              <span className="text-xs text-slate-500">{c.supporters_count + 1} affected</span>
              <StatusBadge status={c.status} />
            </Link>
          </li>
        ))}
      </ul>
    </div>
  );
}
