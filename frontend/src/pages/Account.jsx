import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { KeyRound } from "lucide-react";
import { api } from "../api/client";
import { useAuth } from "../auth/AuthContext";
import { ErrorBox, PageHeader } from "../components/Feedback";
import { useToast } from "../components/Toast";
import { formatDate, roleLabel } from "../lib/format";

const EMPTY = { current: "", next: "", confirm: "" };

function Row({ label, children }) {
  return (
    <div className="flex flex-col gap-0.5 py-3 sm:flex-row sm:gap-4">
      <dt className="w-40 shrink-0 text-sm text-slate-500">{label}</dt>
      <dd className="text-sm font-medium">{children || "—"}</dd>
    </div>
  );
}

// your own details + change password, same page for every role
export default function Account() {
  const { user: saved } = useAuth();
  const toast = useToast();
  // fresh copy from the server, the saved one is from the moment you logged in
  const { data } = useQuery({ queryKey: ["me"], queryFn: () => api("/auth/me") });
  const user = data ?? saved;

  const [form, setForm] = useState(EMPTY);
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);
  const set = (key) => (e) => setForm({ ...form, [key]: e.target.value });

  async function submit(e) {
    e.preventDefault();
    if (form.next !== form.confirm) {
      setError(new Error("The new passwords don't match."));
      return;
    }
    setBusy(true);
    setError(null);
    try {
      const res = await api("/auth/change-password", {
        method: "POST",
        body: { current_password: form.current, new_password: form.next },
      });
      toast.success(res.message);
      setForm(EMPTY);
    } catch (err) {
      setError(err);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="max-w-3xl space-y-6">
      <PageHeader title="My account" subtitle="Your details and password" />

      <div className="card px-5 py-2">
        <dl className="divide-y divide-slate-100 dark:divide-slate-800">
          <Row label="Name">{user.name}</Row>
          <Row label="User ID"><span className="font-mono">{user.user_id}</span></Row>
          <Row label="Email">{user.email}</Row>
          <Row label="Role">{roleLabel(user.role)}</Row>
          {user.role === "grievance_manager"
            ? <Row label="Categories">{user.categories?.join(", ")}</Row>
            : <Row label="Department">{user.department}</Row>}
          <Row label="Email verified">{user.is_verified ? "Yes" : "No"}</Row>
          <Row label="Member since">{user.created_at && formatDate(user.created_at)}</Row>
        </dl>
      </div>

      <form onSubmit={submit} className="card space-y-4 p-5">
        <h2 className="flex items-center gap-2 font-semibold"><KeyRound size={18} /> Change password</h2>
        <div>
          <label className="label" htmlFor="pw-current">Current password</label>
          <input id="pw-current" type="password" className="input" autoComplete="current-password"
            value={form.current} onChange={set("current")} required />
        </div>
        <div className="grid gap-4 sm:grid-cols-2">
          <div>
            <label className="label" htmlFor="pw-new">New password</label>
            <input id="pw-new" type="password" className="input" autoComplete="new-password"
              value={form.next} onChange={set("next")} required />
          </div>
          <div>
            <label className="label" htmlFor="pw-confirm">Confirm new password</label>
            <input id="pw-confirm" type="password" className="input" autoComplete="new-password"
              value={form.confirm} onChange={set("confirm")} required />
          </div>
        </div>
        <p className="text-xs text-slate-500">At least 8 characters with upper and lower case, a number and a symbol.</p>
        <ErrorBox error={error} />
        <button className="btn-primary" disabled={busy}>{busy ? "Saving…" : "Change password"}</button>
      </form>
    </div>
  );
}
