import { useState } from "react";
import { Link, Navigate, useLocation, useNavigate, useSearchParams } from "react-router-dom";
import { api } from "../api/client";
import { homeFor, useAuth } from "../auth/AuthContext";
import { ErrorBox } from "../components/Feedback";
import { useToast } from "../components/Toast";

const DEPARTMENTS = ["Computer Science", "Information Technology", "Electronics", "Mechanical", "Civil",
  "Electrical", "MBA", "BBA", "Commerce", "Arts", "Science", "Other"];

function AuthCard({ title, subtitle, children, footer }) {
  return (
    <div className="flex min-h-screen items-center justify-center px-4 py-10">
      <div className="w-full max-w-md">
        <div className="mb-6 flex flex-col items-center text-center">
          <img src="/favicon.svg" alt="" className="mb-3 h-11 w-11" />
          <h1 className="text-2xl font-semibold">{title}</h1>
          {subtitle && <p className="mt-1 text-sm text-slate-500">{subtitle}</p>}
        </div>
        <div className="card p-6">{children}</div>
        {footer && <p className="mt-4 text-center text-sm text-slate-500">{footer}</p>}
      </div>
    </div>
  );
}

export function LoginPage() {
  const { user, login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [form, setForm] = useState({ user_id: "", password: "" });
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);

  if (user) return <Navigate to={homeFor(user.role)} replace />;

  async function submit(e) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const u = await login(form.user_id.trim(), form.password);
      navigate(location.state?.from ?? homeFor(u.role), { replace: true });
    } catch (err) {
      if (err.code === "not_verified") {
        navigate(`/verify?user=${encodeURIComponent(form.user_id.trim())}`);
        return;
      }
      setError(err);
    } finally {
      setBusy(false);
    }
  }

  return (
    <AuthCard
      title="Sign in to EchoCampus"
      subtitle="Raise and track campus complaints"
      footer={<>New student? <Link to="/register" className="font-medium text-indigo-600">Create an account</Link></>}
    >
      <form onSubmit={submit} className="space-y-4">
        <div>
          <label className="label" htmlFor="uid">User ID</label>
          <input id="uid" className="input" placeholder="ST000101 / GM001 / ADMIN001" autoComplete="username"
            value={form.user_id} onChange={(e) => setForm({ ...form, user_id: e.target.value })} required />
        </div>
        <div>
          <label className="label" htmlFor="pw">Password</label>
          <input id="pw" type="password" className="input" autoComplete="current-password"
            value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} required />
        </div>
        <ErrorBox error={error} />
        <button className="btn-primary w-full" disabled={busy}>{busy ? "Signing in…" : "Sign in"}</button>
      </form>
    </AuthCard>
  );
}

export function RegisterPage() {
  const navigate = useNavigate();
  const toast = useToast();
  const [form, setForm] = useState({ name: "", email: "", department: DEPARTMENTS[0], password: "", confirm: "" });
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);
  const set = (key) => (e) => setForm({ ...form, [key]: e.target.value });

  async function submit(e) {
    e.preventDefault();
    if (form.password !== form.confirm) {
      setError(new Error("Passwords don't match."));
      return;
    }
    setBusy(true);
    setError(null);
    try {
      const { confirm, ...body } = form; // eslint-disable-line no-unused-vars
      const res = await api("/auth/register", { method: "POST", body });
      toast.success(`Account created. Your student ID is ${res.user_id}`);
      navigate(`/verify?user=${res.user_id}&new=1`);
    } catch (err) {
      setError(err);
    } finally {
      setBusy(false);
    }
  }

  return (
    <AuthCard
      title="Student registration"
      subtitle="Your student ID is generated for you"
      footer={<>Already registered? <Link to="/login" className="font-medium text-indigo-600">Sign in</Link></>}
    >
      <form onSubmit={submit} className="space-y-4">
        <div>
          <label className="label" htmlFor="name">Full name</label>
          <input id="name" className="input" value={form.name} onChange={set("name")} required />
        </div>
        <div>
          <label className="label" htmlFor="email">College email</label>
          <input id="email" type="email" className="input" placeholder="name@college.edu" value={form.email} onChange={set("email")} required />
        </div>
        <div>
          <label className="label" htmlFor="dept">Department</label>
          <select id="dept" className="input" value={form.department} onChange={set("department")}>
            {DEPARTMENTS.map((d) => <option key={d}>{d}</option>)}
          </select>
        </div>
        <div className="grid gap-4 sm:grid-cols-2">
          <div>
            <label className="label" htmlFor="pw1">Password</label>
            <input id="pw1" type="password" className="input" autoComplete="new-password" value={form.password} onChange={set("password")} required />
          </div>
          <div>
            <label className="label" htmlFor="pw2">Confirm</label>
            <input id="pw2" type="password" className="input" autoComplete="new-password" value={form.confirm} onChange={set("confirm")} required />
          </div>
        </div>
        <p className="text-xs text-slate-500">At least 8 characters with upper and lower case, a number and a symbol.</p>
        <ErrorBox error={error} />
        <button className="btn-primary w-full" disabled={busy}>{busy ? "Creating…" : "Create account"}</button>
      </form>
    </AuthCard>
  );
}

export function VerifyOtpPage() {
  const [params] = useSearchParams();
  const navigate = useNavigate();
  const toast = useToast();
  const [userId, setUserId] = useState(params.get("user") ?? "");
  const [code, setCode] = useState("");
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);

  async function submit(e) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await api("/auth/verify-otp", { method: "POST", body: { user_id: userId.trim(), code } });
      toast.success("Email verified, you can sign in now.");
      navigate("/login");
    } catch (err) {
      setError(err);
    } finally {
      setBusy(false);
    }
  }

  async function resend() {
    try {
      await api("/auth/resend-otp", { method: "POST", body: { user_id: userId.trim() } });
      toast.info("A new code was sent to your email.");
    } catch (err) {
      setError(err);
    }
  }

  return (
    <AuthCard
      title="Verify your email"
      subtitle={params.get("new") ? `Save your student ID: ${userId}. We sent a 6 digit code to your email.` : "Enter the 6 digit code from your email."}
      footer={<Link to="/login" className="font-medium text-indigo-600">Back to sign in</Link>}
    >
      <form onSubmit={submit} className="space-y-4">
        <div>
          <label className="label" htmlFor="vid">Student ID</label>
          <input id="vid" className="input" value={userId} onChange={(e) => setUserId(e.target.value)} required />
        </div>
        <div>
          <label className="label" htmlFor="code">Code</label>
          <input id="code" className="input text-center font-mono text-lg tracking-[0.5em]" inputMode="numeric" maxLength={6}
            pattern="\d{6}" placeholder="••••••" value={code} onChange={(e) => setCode(e.target.value.replace(/\D/g, ""))} required />
        </div>
        <ErrorBox error={error} />
        <button className="btn-primary w-full" disabled={busy || code.length !== 6}>{busy ? "Checking…" : "Verify"}</button>
        <button type="button" onClick={resend} className="w-full text-sm text-indigo-600 hover:underline" disabled={!userId}>
          Send a new code
        </button>
      </form>
    </AuthCard>
  );
}

export function NotFoundPage() {
  return (
    <div className="flex min-h-[60vh] flex-col items-center justify-center text-center">
      <p className="text-5xl font-semibold text-slate-300">404</p>
      <p className="mt-2 text-slate-500">This page doesn't exist.</p>
      <Link to="/" className="btn-primary mt-4">Go home</Link>
    </div>
  );
}
