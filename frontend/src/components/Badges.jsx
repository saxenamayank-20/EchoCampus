const STATUS = {
  Pending: "bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-300",
  Assigned: "bg-blue-100 text-blue-700 dark:bg-blue-950 dark:text-blue-300",
  "In Progress": "bg-amber-100 text-amber-800 dark:bg-amber-950 dark:text-amber-300",
  Resolved: "bg-emerald-100 text-emerald-700 dark:bg-emerald-950 dark:text-emerald-300",
  Closed: "bg-slate-200 text-slate-600 dark:bg-slate-800 dark:text-slate-400",
};

const PRIORITY = {
  Critical: "bg-red-600 text-white",
  High: "bg-orange-100 text-orange-800 dark:bg-orange-950 dark:text-orange-300",
  Medium: "bg-yellow-100 text-yellow-800 dark:bg-yellow-950 dark:text-yellow-300",
  Low: "bg-green-100 text-green-700 dark:bg-green-950 dark:text-green-300",
};

const base = "inline-flex items-center whitespace-nowrap rounded-full px-2.5 py-0.5 text-xs font-medium";

export function StatusBadge({ status }) {
  return <span className={`${base} ${STATUS[status] ?? STATUS.Pending}`}>{status}</span>;
}

export function PriorityBadge({ priority }) {
  return <span className={`${base} ${PRIORITY[priority] ?? PRIORITY.Low}`}>{priority}</span>;
}
