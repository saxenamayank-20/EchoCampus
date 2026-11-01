import { HeartHandshake, Phone, Sparkles, Users } from "lucide-react";
import { PriorityBadge, StatusBadge } from "./Badges";

// crisis help comes first and is impossible to miss
export function CrisisCard({ crisis }) {
  return (
    <div className="rounded-xl border-2 border-rose-300 bg-rose-50 p-4 text-rose-900 dark:border-rose-800 dark:bg-rose-950 dark:text-rose-100">
      <p className="flex items-center gap-2 font-semibold"><HeartHandshake size={18} /> You don't have to go through this alone</p>
      <p className="mt-2 text-sm">{crisis.message}</p>
      <ul className="mt-3 space-y-1 text-sm">
        <li className="flex gap-2"><Phone size={15} className="mt-0.5 shrink-0" /> <b>Helpline:</b> {crisis.helpline}</li>
        <li className="flex gap-2"><Phone size={15} className="mt-0.5 shrink-0" /> <b>Counsellor:</b> {crisis.counsellor}</li>
      </ul>
    </div>
  );
}

/** what the ai found before submit: category suggestion, priority, similar complaints */
export default function AiCheck({ result, category, onUseCategory, onSupport, supporting }) {
  return (
    <div className="space-y-4">
      {result.crisis && <CrisisCard crisis={result.crisis} />}

      <div className="rounded-xl border border-indigo-200 bg-indigo-50/60 p-4 text-sm dark:border-indigo-900 dark:bg-indigo-950/40">
        <p className="flex items-center gap-2 font-semibold text-indigo-800 dark:text-indigo-200">
          <Sparkles size={16} /> {result.used_ai ? "AI check" : "Quick check (AI unavailable, keyword rules used)"}
        </p>
        <div className="mt-3 flex flex-wrap items-center gap-2">
          <span className="text-slate-500">Priority:</span> <PriorityBadge priority={result.priority} />
          <span className="text-xs text-slate-500">({result.priority_source === "ai" ? "set by AI" : "keyword rules"})</span>
        </div>
        {result.summary && <p className="mt-2 text-slate-700 dark:text-slate-300">“{result.summary}”</p>}
        {result.suggested_category !== category && (
          <div className="mt-3 flex flex-wrap items-center gap-2">
            <span>This sounds like <b>{result.suggested_category}</b>, not {category}.</span>
            <button type="button" className="btn-secondary px-3 py-1 text-xs" onClick={() => onUseCategory(result.suggested_category)}>
              Use {result.suggested_category}
            </button>
            <span className="text-xs text-slate-500">or keep yours</span>
          </div>
        )}
      </div>

      {result.duplicates.length > 0 && (
        <div className="rounded-xl border border-amber-200 bg-amber-50/60 p-4 dark:border-amber-900 dark:bg-amber-950/30">
          <p className="flex items-center gap-2 text-sm font-semibold"><Users size={16} /> Others already reported something similar</p>
          <p className="mt-1 text-xs text-slate-500">Backing an existing complaint gets it fixed faster than a new one.</p>
          <ul className="mt-3 space-y-2">
            {result.duplicates.map((d) => (
              <li key={d.ticket_id} className="flex flex-wrap items-center gap-2 rounded-lg bg-white p-2.5 text-sm dark:bg-slate-900">
                <span className="font-mono text-xs text-slate-500">{d.ticket_id}</span>
                <span className="min-w-0 flex-1 truncate">{d.title}</span>
                <StatusBadge status={d.status} />
                <span className="text-xs text-slate-500">{Math.round(d.similarity * 100)}% match · {d.supporters_count + 1} affected</span>
                <button type="button" className="btn-primary px-3 py-1 text-xs" disabled={supporting === d.ticket_id}
                  onClick={() => onSupport(d.ticket_id)}>This is my issue too</button>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
