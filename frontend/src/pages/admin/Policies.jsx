import { useRef, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { FileText, RefreshCw, Trash2, Upload } from "lucide-react";
import { api, apiForm } from "../../api/client";
import { EmptyState, ErrorBox, PageHeader, SkeletonRows } from "../../components/Feedback";
import { useToast } from "../../components/Toast";
import { formatDateTime } from "../../lib/format";

// policy pdfs that the student assistant answers from
export default function Policies() {
  const toast = useToast();
  const queryClient = useQueryClient();
  const { data, isLoading, error } = useQuery({ queryKey: ["policies"], queryFn: () => api("/admin/policies") });
  const [title, setTitle] = useState("");
  const [file, setFile] = useState(null);
  const replaceFor = useRef(null);
  const replaceInput = useRef(null);
  const refresh = () => queryClient.invalidateQueries({ queryKey: ["policies"] });

  const send = useMutation({
    mutationFn: ({ path, method, form }) => apiForm(path, form, method),
    onSuccess: (doc) => { toast.success(`${doc.title}: ${doc.pages} pages, ${doc.chunks} chunks indexed.`); setTitle(""); setFile(null); refresh(); },
    onError: (e) => toast.error(e.message),
  });
  const remove = useMutation({
    mutationFn: (id) => api(`/admin/policies/${id}`, { method: "DELETE" }),
    onSuccess: () => { toast.success("Policy deleted."); refresh(); },
    onError: (e) => toast.error(e.message),
  });

  function upload(e) {
    e.preventDefault();
    const form = new FormData();
    form.append("title", title);
    form.append("file", file);
    send.mutate({ path: "/admin/policies", method: "POST", form });
  }

  function replace(e) {
    const f = e.target.files[0];
    e.target.value = "";
    if (!f) return;
    const form = new FormData();
    form.append("file", f);
    send.mutate({ path: `/admin/policies/${replaceFor.current}`, method: "PUT", form });
  }

  return (
    <div className="space-y-6">
      <PageHeader title="Policies" subtitle="PDFs the student assistant answers from. Re-upload a PDF to replace its old text." />

      <form onSubmit={upload} className="card grid gap-3 p-5 sm:grid-cols-[1fr_1fr_auto] sm:items-end">
        <div>
          <label className="label" htmlFor="pt">Title</label>
          <input id="pt" className="input" value={title} onChange={(e) => setTitle(e.target.value)} placeholder="e.g. Hostel Rules 2026" required />
        </div>
        <div>
          <label className="label" htmlFor="pf">PDF file</label>
          <input id="pf" type="file" accept="application/pdf,.pdf" className="input py-1.5" onChange={(e) => setFile(e.target.files[0] ?? null)} required />
        </div>
        <button className="btn-primary" disabled={!file || !title.trim() || send.isPending}>
          <Upload size={16} /> {send.isPending ? "Indexing…" : "Upload"}
        </button>
      </form>

      <ErrorBox error={error} />
      <div className="card overflow-hidden">
        {isLoading ? <SkeletonRows /> : !data?.length ? (
          <EmptyState title="No policies yet" text="Upload the college's policy PDFs so students can ask questions." />
        ) : (
          <ul className="divide-y divide-slate-100 dark:divide-slate-800">
            {data.map((d) => (
              <li key={d.id} className="flex flex-wrap items-center gap-3 px-5 py-3 text-sm">
                <FileText size={18} className="text-brand-600 dark:text-brand-400" />
                <div className="min-w-0 flex-1">
                  <p className="truncate font-medium">{d.title}</p>
                  <p className="text-xs text-slate-500">{d.filename} · {d.pages} pages · {d.chunks} chunks · {formatDateTime(d.updated_at)}</p>
                </div>
                <button className="btn-secondary px-3 py-1.5 text-xs" disabled={send.isPending}
                  onClick={() => { replaceFor.current = d.id; replaceInput.current.click(); }}>
                  <RefreshCw size={14} /> Replace
                </button>
                <button className="btn-secondary px-3 py-1.5 text-xs text-red-600" disabled={remove.isPending}
                  onClick={() => window.confirm(`Delete "${d.title}"?`) && remove.mutate(d.id)}>
                  <Trash2 size={14} /> Delete
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>
      <input ref={replaceInput} type="file" accept="application/pdf,.pdf" hidden onChange={replace} />
    </div>
  );
}
