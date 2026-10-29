import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { CheckCircle2, Clock, Flame, Ticket } from "lucide-react";
import { api } from "../../api/client";
import ComplaintTable from "../../components/ComplaintTable";
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
    </div>
  );
}
