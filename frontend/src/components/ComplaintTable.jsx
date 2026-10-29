import { useState } from "react";
import { Link } from "react-router-dom";
import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { Search } from "lucide-react";
import { api } from "../api/client";
import { PRIORITIES, formatDate } from "../lib/format";
import { PriorityBadge, StatusBadge } from "./Badges";
import { EmptyState, ErrorBox, SkeletonRows } from "./Feedback";
import Pagination from "./Pagination";

const PAGE_SIZE = 10;

/**
 * table of complaints with filters + paging. the backend already limits rows to what
 * this user may see, so the same table works for students, managers and admin.
 * fixed = filters the page always sends (like a manager's queue statuses)
 */
export default function ComplaintTable({ fixed = {}, statusOptions = [], showStudent = false, showManager = false, emptyText, queryKey = "complaints" }) {
  const [page, setPage] = useState(1);
  const [filters, setFilters] = useState({ status: "", category: "", priority: "", q: "", date_from: "", date_to: "" });

  const categories = useQuery({ queryKey: ["categories"], queryFn: () => api("/meta/categories"), staleTime: Infinity });

  const params = {
    ...fixed,
    ...Object.fromEntries(Object.entries(filters).filter(([, v]) => v)),
    page,
    page_size: PAGE_SIZE,
  };
  const { data, isLoading, error } = useQuery({
    queryKey: [queryKey, params],
    queryFn: () => api("/complaints", { params }),
    placeholderData: keepPreviousData, // keep the old page on screen while the next one loads
  });

  const set = (key) => (e) => {
    setFilters((f) => ({ ...f, [key]: e.target.value }));
    setPage(1);
  };

  return (
    <div className="card overflow-hidden">
      <div className="grid gap-3 border-b border-slate-200 p-4 dark:border-slate-800 sm:grid-cols-2 lg:grid-cols-6">
        <label className="relative lg:col-span-2">
          <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
          <input className="input pl-9" placeholder="Search ticket or title" value={filters.q} onChange={set("q")} />
        </label>
        {statusOptions.length > 0 && (
          <select className="input" value={filters.status} onChange={set("status")} aria-label="Status">
            <option value="">All statuses</option>
            {statusOptions.map((s) => <option key={s}>{s}</option>)}
          </select>
        )}
        <select className="input" value={filters.category} onChange={set("category")} aria-label="Category">
          <option value="">All categories</option>
          {categories.data?.map((c) => <option key={c}>{c}</option>)}
        </select>
        <select className="input" value={filters.priority} onChange={set("priority")} aria-label="Priority">
          <option value="">All priorities</option>
          {PRIORITIES.map((p) => <option key={p}>{p}</option>)}
        </select>
        <div className="flex gap-2 lg:col-span-1">
          <input type="date" className="input px-2" value={filters.date_from} onChange={set("date_from")} aria-label="From date" />
          <input type="date" className="input px-2" value={filters.date_to} onChange={set("date_to")} aria-label="To date" />
        </div>
      </div>

      {error && <div className="p-4"><ErrorBox error={error} /></div>}
      {isLoading ? (
        <SkeletonRows />
      ) : !data?.items.length ? (
        <EmptyState title="No complaints found" text={emptyText ?? "Try changing the filters."} />
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead className="bg-slate-50 text-xs uppercase tracking-wide text-slate-500 dark:bg-slate-800/50">
              <tr>
                <th className="px-4 py-3">Ticket</th>
                <th className="px-4 py-3">Title</th>
                <th className="hidden px-4 py-3 md:table-cell">Category</th>
                <th className="px-4 py-3">Priority</th>
                <th className="px-4 py-3">Status</th>
                {showStudent && <th className="hidden px-4 py-3 lg:table-cell">Student</th>}
                {showManager && <th className="hidden px-4 py-3 lg:table-cell">Manager</th>}
                <th className="hidden px-4 py-3 sm:table-cell">Filed</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
              {data.items.map((c) => (
                <tr key={c.ticket_id} className="hover:bg-slate-50 dark:hover:bg-slate-800/40">
                  <td className="whitespace-nowrap px-4 py-3 font-mono text-xs">
                    <Link to={`/tickets/${c.ticket_id}`} className="text-indigo-600 hover:underline dark:text-indigo-400">
                      {c.ticket_id}
                    </Link>
                  </td>
                  <td className="max-w-[16rem] truncate px-4 py-3">
                    <Link to={`/tickets/${c.ticket_id}`} className="hover:underline">{c.title}</Link>
                    {c.close_requested && <span className="ml-2 text-xs text-amber-600">· close requested</span>}
                  </td>
                  <td className="hidden px-4 py-3 md:table-cell">{c.category}</td>
                  <td className="px-4 py-3"><PriorityBadge priority={c.priority} /></td>
                  <td className="px-4 py-3"><StatusBadge status={c.status} /></td>
                  {showStudent && <td className="hidden px-4 py-3 lg:table-cell">{c.student_name}</td>}
                  {showManager && <td className="hidden px-4 py-3 lg:table-cell">{c.manager_name ?? "—"}</td>}
                  <td className="hidden px-4 py-3 text-slate-500 sm:table-cell">{formatDate(c.created_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      {data && <Pagination page={page} pageSize={PAGE_SIZE} total={data.total} onChange={setPage} />}
    </div>
  );
}
