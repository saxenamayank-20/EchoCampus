import { Link } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { AlarmClock, Bell, CheckCircle2, Clock, Flame, Hourglass, LayoutList, RefreshCw } from "lucide-react";
import {
  Bar, BarChart, CartesianGrid, Cell, Legend, Line, LineChart, Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from "recharts";
import { api } from "../../api/client";
import { PriorityBadge, StatusBadge } from "../../components/Badges";
import { EmptyState, ErrorBox, PageHeader, Skeleton, StatCard } from "../../components/Feedback";
import { useToast } from "../../components/Toast";
import { PRIORITIES, STATUSES, formatDateTime } from "../../lib/format";

const STATUS_COLORS = { Pending: "#94a3b8", Assigned: "#3b82f6", "In Progress": "#f59e0b", Resolved: "#10b981", Closed: "#64748b" };
const PRIORITY_COLORS = { Critical: "#dc2626", High: "#f97316", Medium: "#eab308", Low: "#22c55e" };

function ChartCard({ title, children }) {
  return (
    <div className="card p-5">
      <h2 className="mb-4 text-sm font-semibold">{title}</h2>
      <div className="h-64">{children}</div>
    </div>
  );
}

const tooltipStyle = { contentStyle: { borderRadius: 8, fontSize: 12 } };

// complaints past their sla time, plus a button to run the 15 min check right now
function OverdueList() {
  const toast = useToast();
  const queryClient = useQueryClient();
  const params = { escalated: true, status: ["Pending", "Assigned", "In Progress"], page_size: 20 };
  const { data } = useQuery({ queryKey: ["complaints", "overdue", params], queryFn: () => api("/complaints", { params }) });
  const run = useMutation({
    mutationFn: () => api("/admin/sla/run", { method: "POST" }),
    onSuccess: (r) => {
      toast.info(r.escalated.length ? `${r.escalated.length} complaint(s) escalated.` : "Nothing new is overdue.");
      queryClient.invalidateQueries({ queryKey: ["complaints"] });
      queryClient.invalidateQueries({ queryKey: ["admin-stats"] });
      queryClient.invalidateQueries({ queryKey: ["notifications"] });
    },
    onError: (e) => toast.error(e.message),
  });

  return (
    <div className="card mb-6 overflow-hidden">
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-200 px-5 py-3 dark:border-slate-800">
        <h2 className="flex items-center gap-2 text-sm font-semibold"><AlarmClock size={16} className="text-red-500" /> Overdue (past SLA)</h2>
        <button className="btn-secondary px-3 py-1.5 text-xs" onClick={() => run.mutate()} disabled={run.isPending}>
          <RefreshCw size={14} className={run.isPending ? "animate-spin" : ""} /> Run SLA check
        </button>
      </div>
      {!data?.items.length ? (
        <EmptyState title="Nothing overdue" text="Every open complaint is inside its time limit." />
      ) : (
        <ul className="divide-y divide-slate-100 dark:divide-slate-800">
          {data.items.map((c) => (
            <li key={c.ticket_id}>
              <Link to={`/tickets/${c.ticket_id}`} className="flex flex-wrap items-center gap-2 px-5 py-3 text-sm hover:bg-slate-50 dark:hover:bg-slate-800/40">
                <span className="font-mono text-xs text-indigo-600">{c.ticket_id}</span>
                <span className="min-w-0 flex-1 truncate">{c.title}</span>
                <PriorityBadge priority={c.priority} /> <StatusBadge status={c.status} />
                <span className="text-xs text-red-600">due {formatDateTime(c.sla_due_at)}</span>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

export default function Overview() {
  const { data, isLoading, error } = useQuery({ queryKey: ["admin-stats"], queryFn: () => api("/admin/stats") });

  if (error) return <ErrorBox error={error} />;
  const counts = data?.counts ?? {};
  const byStatus = STATUSES.map((s) => ({ name: s, value: data?.by_status[s] ?? 0 }));
  const byPriority = PRIORITIES.map((p) => ({ name: p, value: data?.by_priority[p] ?? 0 })).filter((p) => p.value);
  const byCategory = Object.entries(data?.by_category ?? {})
    .map(([name, value]) => ({ name, value }))
    .sort((a, b) => b.value - a.value);
  const trend = (data?.trend ?? []).map((d) => ({ ...d, label: d.date.slice(5) }));

  return (
    <div>
      <PageHeader title="Overview" subtitle="How complaints are moving across campus" />
      <div className="mb-6 grid grid-cols-2 gap-3 md:grid-cols-4 xl:grid-cols-7">
        <StatCard label="Total" value={counts.Total} icon={LayoutList} tone="indigo" />
        <StatCard label="Pending" value={counts.Pending} icon={Hourglass} />
        <StatCard label="In progress" value={counts["In Progress"]} icon={Clock} tone="amber" />
        <StatCard label="Resolved" value={counts.Resolved} icon={CheckCircle2} tone="green" />
        <StatCard label="Close requests" value={counts.PendingClose} icon={Bell} tone="amber" />
        <StatCard label="Open critical" value={counts.OpenCritical} icon={Flame} tone="red" />
        <StatCard label="Overdue (SLA)" value={counts.Overdue} icon={AlarmClock} tone="red" />
      </div>

      <OverdueList />

      {isLoading ? (
        <div className="grid gap-5 lg:grid-cols-2">
          {[1, 2, 3, 4].map((i) => <Skeleton key={i} className="h-80" />)}
        </div>
      ) : (
        <div className="grid gap-5 lg:grid-cols-2">
          <ChartCard title="Complaints per day (last 30 days)">
            <ResponsiveContainer>
              <LineChart data={trend}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                <XAxis dataKey="label" fontSize={11} interval={4} />
                <YAxis allowDecimals={false} fontSize={11} width={28} />
                <Tooltip {...tooltipStyle} />
                <Line type="monotone" dataKey="count" stroke="#4f46e5" strokeWidth={2} dot={false} name="Complaints" />
              </LineChart>
            </ResponsiveContainer>
          </ChartCard>

          <ChartCard title="By status">
            <ResponsiveContainer>
              <BarChart data={byStatus}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                <XAxis dataKey="name" fontSize={11} />
                <YAxis allowDecimals={false} fontSize={11} width={28} />
                <Tooltip {...tooltipStyle} />
                <Bar dataKey="value" name="Complaints" radius={[4, 4, 0, 0]}>
                  {byStatus.map((d) => <Cell key={d.name} fill={STATUS_COLORS[d.name]} />)}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </ChartCard>

          <ChartCard title="By category">
            <ResponsiveContainer>
              <BarChart data={byCategory} layout="vertical" margin={{ left: 30 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                <XAxis type="number" allowDecimals={false} fontSize={11} />
                <YAxis type="category" dataKey="name" fontSize={11} width={90} />
                <Tooltip {...tooltipStyle} />
                <Bar dataKey="value" name="Complaints" fill="#6366f1" radius={[0, 4, 4, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </ChartCard>

          <ChartCard title="By priority">
            {byPriority.length ? (
              <ResponsiveContainer>
                <PieChart>
                  <Pie data={byPriority} dataKey="value" nameKey="name" innerRadius={55} outerRadius={90} paddingAngle={byPriority.length > 1 ? 2 : 0}>
                    {byPriority.map((d) => <Cell key={d.name} fill={PRIORITY_COLORS[d.name]} />)}
                  </Pie>
                  <Tooltip {...tooltipStyle} />
                  <Legend iconType="circle" wrapperStyle={{ fontSize: 12 }} />
                </PieChart>
              </ResponsiveContainer>
            ) : (
              <p className="pt-24 text-center text-sm text-slate-500">No complaints yet.</p>
            )}
          </ChartCard>
        </div>
      )}
    </div>
  );
}
