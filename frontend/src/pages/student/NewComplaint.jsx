import { useEffect, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { AlertTriangle } from "lucide-react";
import { api, uploadFile } from "../../api/client";
import AiCheck from "../../components/AiCheck";
import { PriorityBadge } from "../../components/Badges";
import { ErrorBox, PageHeader } from "../../components/Feedback";
import FileDropzone from "../../components/FileDropzone";
import { useToast } from "../../components/Toast";

// waits until the user stops typing before calling the api
function useDebounced(value, ms = 400) {
  const [debounced, setDebounced] = useState(value);
  useEffect(() => {
    const t = setTimeout(() => setDebounced(value), ms);
    return () => clearTimeout(t);
  }, [value, ms]);
  return debounced;
}

export default function NewComplaint() {
  const navigate = useNavigate();
  const toast = useToast();
  const queryClient = useQueryClient();
  const location = useLocation();
  // "raise a complaint" from the assistant passes the question as the title
  const [form, setForm] = useState({ title: location.state?.title ?? "", description: "", category: "", remarks: "" });
  const [files, setFiles] = useState([]);
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);
  const [check, setCheck] = useState(null);       // the ai check result, null = not checked yet
  const [supporting, setSupporting] = useState(null);
  // any change to the text means the old check doesn't count anymore
  const set = (key) => (e) => { setForm({ ...form, [key]: e.target.value }); if (key !== "remarks") setCheck(null); };

  const { data: categories = [] } = useQuery({ queryKey: ["categories"], queryFn: () => api("/meta/categories"), staleTime: Infinity });
  useEffect(() => {
    if (!form.category && categories.length) setForm((f) => ({ ...f, category: categories[0] }));
  }, [categories, form.category]);

  // live priority hint, same keyword rules the backend uses on submit
  const text = useDebounced(`${form.title}|${form.description}|${form.category}`);
  const preview = useQuery({
    queryKey: ["priority-preview", text],
    queryFn: () => api("/complaints/priority-preview", { params: { title: form.title, description: form.description, category: form.category } }),
    enabled: Boolean(form.title || form.description),
  });

  // step 1: ask the ai (category, priority, crisis help, similar complaints) before anything is saved
  async function runCheck() {
    setBusy(true);
    setError(null);
    try {
      setCheck(await api("/complaints/preview", { method: "POST", body: { title: form.title, description: form.description, category: form.category } }));
    } catch (err) {
      // the check is a helper, never a blocker: submit still works
      setCheck({ failed: true });
      toast.info(err.code === "rate_limited" ? err.message : "Couldn't run the AI check, you can still submit.");
    } finally {
      setBusy(false);
    }
  }

  async function support(ticketId) {
    setSupporting(ticketId);
    try {
      await api(`/complaints/${ticketId}/support`, { method: "POST" });
      toast.success("Added. You'll get updates on that complaint.");
      queryClient.invalidateQueries({ queryKey: ["complaints"] });
      navigate(`/tickets/${ticketId}`);
    } catch (err) {
      toast.error(err.message);
      setSupporting(null);
    }
  }

  async function submit(e) {
    e.preventDefault();
    if (!check) return runCheck();
    setBusy(true);
    setError(null);
    try {
      const complaint = await api("/complaints", { method: "POST", body: form });
      // complaint first, then each proof file with its own progress bar
      let failed = 0;
      for (const item of files) {
        try {
          await uploadFile(complaint.ticket_id, item.file, (p) =>
            setFiles((all) => all.map((x) => (x.id === item.id ? { ...x, progress: p } : x))));
        } catch (err) {
          failed += 1;
          setFiles((all) => all.map((x) => (x.id === item.id ? { ...x, error: err.message, progress: 100 } : x)));
        }
      }
      queryClient.invalidateQueries({ queryKey: ["complaints"] });
      toast.success(`Complaint ${complaint.ticket_id} submitted.`);
      if (failed) toast.error(`${failed} file(s) didn't upload. You can add them from the ticket page.`);
      navigate(`/tickets/${complaint.ticket_id}`);
    } catch (err) {
      setError(err);
    } finally {
      setBusy(false);
    }
  }

  const priority = preview.data?.priority;

  return (
    <div className="mx-auto max-w-3xl">
      <PageHeader title="New complaint" subtitle="We check it with AI first: the right category, how urgent it is, and whether others already reported it." />
      <form onSubmit={submit} className="card space-y-5 p-5 sm:p-6">
        <div className="grid gap-4 sm:grid-cols-3">
          <div className="sm:col-span-2">
            <label className="label" htmlFor="title">Title</label>
            <input id="title" className="input" maxLength={200} placeholder="Short summary of the issue" value={form.title} onChange={set("title")} required minLength={3} />
          </div>
          <div>
            <label className="label" htmlFor="cat">Category</label>
            <select id="cat" className="input" value={form.category} onChange={set("category")}>
              {categories.map((c) => <option key={c}>{c}</option>)}
            </select>
          </div>
        </div>
        <div>
          <label className="label" htmlFor="desc">Description</label>
          <textarea id="desc" rows={5} className="input" placeholder="What happened, where and when?" value={form.description} onChange={set("description")} required minLength={5} />
        </div>
        <div>
          <label className="label" htmlFor="rem">Extra remarks (optional)</label>
          <textarea id="rem" rows={2} className="input" value={form.remarks} onChange={set("remarks")} />
        </div>

        {check && !check.failed && (
          <AiCheck result={check} category={form.category} supporting={supporting} onSupport={support}
            onUseCategory={(c) => setForm((f) => ({ ...f, category: c }))} />
        )}

        {!check && priority && (
          <div className="flex flex-wrap items-center gap-2 text-sm">
            <span className="text-slate-500">Detected priority:</span> <PriorityBadge priority={priority} />
          </div>
        )}
        {!check && priority === "Critical" && (
          <div className="flex gap-2 rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-800 dark:border-red-900 dark:bg-red-950 dark:text-red-200">
            <AlertTriangle size={18} className="mt-0.5 shrink-0" />
            This looks critical. A Google Meet link with your manager will be created as soon as you submit.
          </div>
        )}

        <div>
          <p className="label">Proof (optional)</p>
          <FileDropzone items={files} onChange={setFiles} disabled={busy} />
        </div>

        <ErrorBox error={error} />
        <div className="flex justify-end">
          <button className="btn-primary" disabled={busy}>
            {busy ? "Please wait…" : check ? "Submit complaint" : "Check & continue"}
          </button>
        </div>
      </form>
    </div>
  );
}
