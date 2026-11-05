import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { AlertTriangle, CheckCircle2, Cpu, Gauge } from "lucide-react";
import { api } from "../../api/client";
import { EmptyState, ErrorBox, PageHeader, SkeletonRows, StatCard } from "../../components/Feedback";
import { formatDateTime } from "../../lib/format";

const RANGES = [7, 30, 90];

const ms = (v) => (v == null ? "—" : `${v} ms`);
const num = (v) => (v == null ? "—" : v.toLocaleString());

// how much the ai is used, how often it fails and how fast it is (from the llm_calls log)
export default function AiUsage() {
  const [days, setDays] = useState(30);
  const { data, isLoading, error } = useQuery({
    queryKey: ["ai-usage", days],
    queryFn: () => api("/admin/ai-usage", { params: { days } }),
  });
  const t = data?.total;

  return (
    <div className="space-y-6">
      <PageHeader
        title="AI usage"
        subtitle="Every call to Gemini is logged: calls, failures, tokens and speed per feature."
        actions={
          <select className="input w-auto" value={days} onChange={(e) => setDays(Number(e.target.value))}>
            {RANGES.map((d) => <option key={d} value={d}>Last {d} days</option>)}
          </select>
        }
      />
      <ErrorBox error={error} />

      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <StatCard label="AI calls" value={num(t?.calls)} icon={Cpu} tone="indigo" />
        <StatCard label="Success rate" value={t?.success_rate == null ? "—" : `${t.success_rate}%`} icon={CheckCircle2} tone="green" />
        <StatCard label="Failed calls" value={num(t?.failed)} icon={AlertTriangle} tone={t?.failed ? "red" : "slate"} />
        <StatCard label="Average speed" value={ms(t?.avg_ms)} icon={Gauge} tone="amber" />
      </div>

      <div className="card overflow-hidden">
        {isLoading ? <SkeletonRows /> : !data?.by_feature.length ? (
          <EmptyState title="No AI calls yet" text="Calls show up here once students submit complaints or use the assistant." />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead className="bg-slate-50 text-xs uppercase tracking-wide text-slate-500 dark:bg-slate-800/50">
                <tr>
                  <th className="px-4 py-3">Feature</th><th className="px-4 py-3">Calls</th>
                  <th className="px-4 py-3">Failed</th><th className="hidden px-4 py-3 sm:table-cell">Avg</th>
                  <th className="hidden px-4 py-3 sm:table-cell">p95</th>
                  <th className="hidden px-4 py-3 md:table-cell">Tokens in / out</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                {data.by_feature.map((f) => (
                  <tr key={f.feature}>
                    <td className="px-4 py-3 font-medium capitalize">{f.feature}</td>
                    <td className="px-4 py-3">{num(f.calls)}</td>
                    <td className={`px-4 py-3 ${f.failed ? "text-red-600 dark:text-red-400" : ""}`}>{num(f.failed)}</td>
                    <td className="hidden px-4 py-3 sm:table-cell">{ms(f.avg_ms)}</td>
                    <td className="hidden px-4 py-3 sm:table-cell">{ms(f.p95_ms)}</td>
                    <td className="hidden px-4 py-3 md:table-cell">{num(f.input_tokens)} / {num(f.output_tokens)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {data?.recent_errors.length > 0 && (
        <div className="card p-5">
          <h2 className="mb-3 font-semibold">Recent failures</h2>
          <ul className="space-y-2 text-sm">
            {data.recent_errors.map((e, i) => (
              <li key={i} className="flex flex-wrap gap-x-3 text-slate-600 dark:text-slate-300">
                <span className="text-xs text-slate-500">{formatDateTime(e.at)}</span>
                <span className="font-medium capitalize">{e.feature}</span>
                <span className="min-w-0 flex-1 truncate">{e.error || "unknown error"}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
