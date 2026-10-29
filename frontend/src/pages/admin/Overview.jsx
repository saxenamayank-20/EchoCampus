import { useQuery } from "@tanstack/react-query";
import { Bell, CheckCircle2, Clock, Flame, Hourglass, LayoutList } from "lucide-react";
import {
  Bar, BarChart, CartesianGrid, Cell, Legend, Line, LineChart, Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from "recharts";
import { api } from "../../api/client";
import { ErrorBox, PageHeader, Skeleton, StatCard } from "../../components/Feedback";
import { PRIORITIES, STATUSES } from "../../lib/format";

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
      <div className="mb-6 grid grid-cols-2 gap-3 md:grid-cols-3 xl:grid-cols-6">
        <StatCard label="Total" value={counts.Total} icon={LayoutList} tone="indigo" />
        <StatCard label="Pending" value={counts.Pending} icon={Hourglass} />
        <StatCard label="In progress" value={counts["In Progress"]} icon={Clock} tone="amber" />
        <StatCard label="Resolved" value={counts.Resolved} icon={CheckCircle2} tone="green" />
        <StatCard label="Close requests" value={counts.PendingClose} icon={Bell} tone="amber" />
        <StatCard label="Open critical" value={counts.OpenCritical} icon={Flame} tone="red" />
      </div>

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
