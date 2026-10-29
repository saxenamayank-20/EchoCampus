import { Inbox } from "lucide-react";

// grey placeholder blocks while data loads
export function Skeleton({ className = "" }) {
  return <div className={`animate-pulse rounded-md bg-slate-200 dark:bg-slate-800 ${className}`} />;
}

export function SkeletonRows({ rows = 5 }) {
  return (
    <div className="space-y-3 p-4">
      {Array.from({ length: rows }, (_, i) => (
        <Skeleton key={i} className="h-10 w-full" />
      ))}
    </div>
  );
}

export function EmptyState({ title, text, action }) {
  return (
    <div className="flex flex-col items-center justify-center px-6 py-14 text-center">
      <div className="mb-3 rounded-full bg-slate-100 p-3 text-slate-400 dark:bg-slate-800">
        <Inbox size={26} />
      </div>
      <p className="font-medium">{title}</p>
      {text && <p className="mt-1 max-w-sm text-sm text-slate-500">{text}</p>}
      {action && <div className="mt-4">{action}</div>}
    </div>
  );
}

export function ErrorBox({ error }) {
  if (!error) return null;
  return (
    <div className="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700 dark:border-red-900 dark:bg-red-950 dark:text-red-300">
      {error.message}
    </div>
  );
}

export function PageHeader({ title, subtitle, actions }) {
  return (
    <div className="mb-6 flex flex-wrap items-end justify-between gap-3">
      <div>
        <h1 className="text-xl font-semibold sm:text-2xl">{title}</h1>
        {subtitle && <p className="mt-1 text-sm text-slate-500">{subtitle}</p>}
      </div>
      {actions}
    </div>
  );
}

export function StatCard({ label, value, tone = "slate", icon: Icon }) {
  const tones = {
    slate: "text-slate-600 bg-slate-100 dark:bg-slate-800 dark:text-slate-300",
    indigo: "text-indigo-600 bg-indigo-50 dark:bg-indigo-950 dark:text-indigo-300",
    amber: "text-amber-600 bg-amber-50 dark:bg-amber-950 dark:text-amber-300",
    green: "text-emerald-600 bg-emerald-50 dark:bg-emerald-950 dark:text-emerald-300",
    red: "text-red-600 bg-red-50 dark:bg-red-950 dark:text-red-300",
  };
  return (
    <div className="card flex items-center gap-3 p-4">
      {Icon && (
        <div className={`rounded-lg p-2.5 ${tones[tone]}`}>
          <Icon size={20} />
        </div>
      )}
      <div>
        <div className="text-2xl font-semibold leading-none">{value ?? "—"}</div>
        <div className="mt-1 text-xs text-slate-500">{label}</div>
      </div>
    </div>
  );
}
