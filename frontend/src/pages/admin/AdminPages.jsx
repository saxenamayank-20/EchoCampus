import { useState } from "react";
import { Link } from "react-router-dom";
import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { api } from "../../api/client";
import { PriorityBadge, StatusBadge } from "../../components/Badges";
import ComplaintTable from "../../components/ComplaintTable";
import { EmptyState, ErrorBox, PageHeader, SkeletonRows } from "../../components/Feedback";
import Pagination from "../../components/Pagination";
import { STATUSES, formatDate, formatDateTime, roleLabel } from "../../lib/format";

export function AllComplaints() {
  return (
    <div>
      <PageHeader title="All complaints" subtitle="Filter by category to see one department's queue" />
      <ComplaintTable statusOptions={STATUSES} showStudent showManager />
    </div>
  );
}

function ComplaintCards({ params, empty }) {
  const { data, isLoading, error } = useQuery({
    queryKey: ["complaints", "cards", params],
    queryFn: () => api("/complaints", { params: { ...params, page_size: 50 } }),
  });
  if (error) return <ErrorBox error={error} />;
  if (isLoading) return <div className="card"><SkeletonRows rows={3} /></div>;
  if (!data.items.length) return <div className="card"><EmptyState title={empty} /></div>;
  return (
    <div className="grid gap-3 md:grid-cols-2">
      {data.items.map((c) => (
        <Link key={c.ticket_id} to={`/tickets/${c.ticket_id}`} className="card block p-4 transition hover:border-indigo-300">
          <div className="mb-2 flex items-start justify-between gap-2">
            <span className="font-mono text-xs text-slate-500">{c.ticket_id}</span>
            <div className="flex gap-1.5"><PriorityBadge priority={c.priority} /><StatusBadge status={c.status} /></div>
          </div>
          <p className="font-medium">{c.title}</p>
          <p className="mt-1 text-xs text-slate-500">{c.category} · {c.manager_name ?? "—"} · resolved {formatDate(c.resolved_at)}</p>
          {c.manager_remarks && <p className="mt-2 line-clamp-2 text-sm text-slate-600 dark:text-slate-300">“{c.manager_remarks}”</p>}
        </Link>
      ))}
    </div>
  );
}

export function CloseRequests() {
  return (
    <div className="space-y-8">
      <PageHeader title="Close requests" subtitle="Managers resolved these and want them officially closed" />
      <section>
        <h2 className="mb-3 text-sm font-semibold text-amber-600">Waiting for you</h2>
        <ComplaintCards params={{ status: "Resolved", close_requested: true }} empty="No close requests right now." />
      </section>
      <section>
        <h2 className="mb-3 text-sm font-semibold text-slate-500">Resolved, no close request yet</h2>
        <ComplaintCards params={{ status: "Resolved", close_requested: false }} empty="Nothing here." />
      </section>
      <section>
        <h2 className="mb-3 text-sm font-semibold text-slate-500">Closed</h2>
        <ComplaintTable fixed={{ status: "Closed" }} queryKey="complaints-closed" showManager />
      </section>
    </div>
  );
}

function usePaged(path, extra = {}) {
  const [page, setPage] = useState(1);
  const params = { ...extra, page, page_size: 20 };
  const query = useQuery({ queryKey: [path, params], queryFn: () => api(path, { params }), placeholderData: keepPreviousData });
  return { ...query, page, setPage };
}

export function ManagerUpdates() {
  const { data, isLoading, error, page, setPage } = usePaged("/admin/manager-updates");
  return (
    <div>
      <PageHeader title="Manager updates" subtitle="Progress notes posted by grievance managers" />
      <ErrorBox error={error} />
      <div className="card overflow-hidden">
        {isLoading ? <SkeletonRows /> : !data?.items.length ? <EmptyState title="No updates yet" /> : (
          <ul className="divide-y divide-slate-100 dark:divide-slate-800">
            {data.items.map((u, i) => (
              <li key={i} className="p-4">
                <div className="mb-1 flex flex-wrap items-center gap-2 text-xs text-slate-500">
                  <span className="font-medium text-slate-700 dark:text-slate-200">{u.manager_name}</span>
                  <span>·</span>
                  <Link to={`/tickets/${u.ticket_id}`} className="font-mono text-indigo-600">{u.ticket_id}</Link>
                  <span>·</span><span>{u.category}</span><span>·</span><span>{formatDateTime(u.created_at)}</span>
                  <PriorityBadge priority={u.priority} /><StatusBadge status={u.status} />
                </div>
                <p className="text-sm">{u.update_text}</p>
              </li>
            ))}
          </ul>
        )}
        {data && <Pagination page={page} pageSize={20} total={data.total} onChange={setPage} />}
      </div>
    </div>
  );
}

export function UsersPage() {
  const [role, setRole] = useState("");
  const { data, isLoading, error, page, setPage } = usePaged("/admin/users", { role });
  return (
    <div>
      <PageHeader
        title="Users"
        actions={
          <select className="input w-48" value={role} onChange={(e) => { setRole(e.target.value); setPage(1); }} aria-label="Role">
            <option value="">All roles</option>
            <option value="student">Students</option>
            <option value="grievance_manager">Managers</option>
            <option value="admin">Admin</option>
          </select>
        }
      />
      <ErrorBox error={error} />
      <div className="card overflow-hidden">
        {isLoading ? <SkeletonRows /> : !data?.items.length ? <EmptyState title="No users" /> : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead className="bg-slate-50 text-xs uppercase tracking-wide text-slate-500 dark:bg-slate-800/50">
                <tr>
                  <th className="px-4 py-3">ID</th><th className="px-4 py-3">Name</th>
                  <th className="hidden px-4 py-3 md:table-cell">Email</th><th className="px-4 py-3">Role</th>
                  <th className="hidden px-4 py-3 lg:table-cell">Department / categories</th>
                  <th className="hidden px-4 py-3 sm:table-cell">Verified</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                {data.items.map((u) => (
                  <tr key={u.user_id}>
                    <td className="px-4 py-3 font-mono text-xs">{u.user_id}</td>
                    <td className="px-4 py-3">{u.name}</td>
                    <td className="hidden px-4 py-3 md:table-cell">{u.email}</td>
                    <td className="px-4 py-3">{roleLabel(u.role)}</td>
                    <td className="hidden px-4 py-3 text-slate-500 lg:table-cell">{u.categories.length ? u.categories.join(", ") : u.department}</td>
                    <td className="hidden px-4 py-3 sm:table-cell">{u.is_verified ? "Yes" : "No"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        {data && <Pagination page={page} pageSize={20} total={data.total} onChange={setPage} />}
      </div>
    </div>
  );
}
