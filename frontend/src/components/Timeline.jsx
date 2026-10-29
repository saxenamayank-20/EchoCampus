import { Check } from "lucide-react";
import { STATUSES, formatDateTime } from "../lib/format";

// the 5 status steps as a bar, same idea as the old streamlit progress tracker
export function ProgressTracker({ status }) {
  const current = STATUSES.indexOf(status);
  return (
    <ol className="flex items-start">
      {STATUSES.map((step, i) => {
        const done = i < current;
        const active = i === current;
        return (
          <li key={step} className="relative flex flex-1 flex-col items-center text-center">
            {i > 0 && (
              <span className={`absolute right-1/2 top-4 h-0.5 w-full -translate-y-1/2 ${i <= current ? "bg-indigo-500" : "bg-slate-200 dark:bg-slate-700"}`} />
            )}
            <span
              className={`relative z-10 flex h-8 w-8 items-center justify-center rounded-full text-xs font-semibold
                ${done ? "bg-indigo-500 text-white" : active ? "bg-indigo-600 text-white ring-4 ring-indigo-500/20" : "bg-slate-200 text-slate-500 dark:bg-slate-700 dark:text-slate-400"}`}
            >
              {done ? <Check size={16} /> : i + 1}
            </span>
            <span className={`mt-2 text-[11px] sm:text-xs ${active ? "font-semibold" : "text-slate-500"}`}>{step}</span>
          </li>
        );
      })}
    </ol>
  );
}

export function Timeline({ events }) {
  if (!events?.length) return <p className="text-sm text-slate-500">No activity yet.</p>;
  return (
    <ol className="relative ml-2 border-l border-slate-200 dark:border-slate-700">
      {events.map((e, i) => (
        <li key={i} className="mb-5 ml-5 last:mb-0">
          <span
            className={`absolute -left-[7px] mt-1.5 h-3 w-3 rounded-full border-2 border-white dark:border-slate-900
              ${e.new_status === "Closed" ? "bg-slate-500" : e.new_status === "Resolved" ? "bg-emerald-500" : "bg-indigo-500"}`}
          />
          <p className="text-sm font-medium">{e.action}</p>
          <p className="text-xs text-slate-500">
            {formatDateTime(e.timestamp)} · {e.changed_by}
            {e.old_status && e.new_status && ` · ${e.old_status} → ${e.new_status}`}
          </p>
          {e.note && <p className="mt-1 rounded-md bg-slate-50 px-2 py-1 text-sm dark:bg-slate-800">{e.note}</p>}
        </li>
      ))}
    </ol>
  );
}
