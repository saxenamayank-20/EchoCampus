export const STATUSES = ["Pending", "Assigned", "In Progress", "Resolved", "Closed"];
export const PRIORITIES = ["Critical", "High", "Medium", "Low"];

export function formatDate(value) {
  if (!value) return "—";
  return new Date(value).toLocaleDateString(undefined, { day: "numeric", month: "short", year: "numeric" });
}

export function formatDateTime(value) {
  if (!value) return "—";
  return new Date(value).toLocaleString(undefined, {
    day: "numeric", month: "short", hour: "2-digit", minute: "2-digit",
  });
}

export function formatSize(bytes) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`;
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}

export function roleLabel(role) {
  return { student: "Student", grievance_manager: "Grievance Manager", admin: "Admin" }[role] ?? role;
}
