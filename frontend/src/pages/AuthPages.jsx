import { useState } from "react";
import { Link, Navigate, useLocation, useNavigate, useSearchParams } from "react-router-dom";
import { ArrowLeft, CheckCircle2, Copy, ShieldCheck, Sparkles, Users } from "lucide-react";
import { api } from "../api/client";
import { homeFor, useAuth } from "../auth/AuthContext";
import { ErrorBox } from "../components/Feedback";
import { useToast } from "../components/Toast";
import PasswordInput from "../components/PasswordInput";

const DEPARTMENTS = ["Computer Science", "Information Technology", "Electronics", "Mechanical", "Civil",
  "Electrical", "MBA", "BBA", "Commerce", "Arts", "Science", "Other"];

const POINTS = [
  { icon: Sparkles, text: "AI suggests the category and priority" },
  { icon: Users, text: "See if others already reported it" },
  { icon: ShieldCheck, text: "Tracked with deadlines until it's fixed" },
];

// split screen: brand panel on the left (big screens only), the form on the right
export function AuthCard({ title, subtitle, children, footer }) {
  return (
    <div className="flex min-h-screen">
      <aside className="relative hidden w-[44%] flex-col justify-between overflow-hidden bg-[#060a0f] p-10 text-white lg:flex">
        <div aria-hidden className="pointer-events-none absolute -left-32 -top-32 h-[28rem] w-[28rem] rounded-full bg-brand-400/20 blur-3xl" />
        <div aria-hidden className="pointer-events-none absolute -bottom-40 -right-24 h-[26rem] w-[26rem] rounded-full bg-lime-500/10 blur-3xl" />
        <Link to="/" className="relative flex items-center gap-2.5">
          <img src="/favicon.svg" alt="" className="h-9 w-9" />
          <span className="text-lg font-semibold">EchoCampus</span>
        </Link>
        <div className="relative max-w-md">
          <h2 className="text-4xl font-bold leading-tight">
            Raise it. Track it.<br />
            <span className="bg-gradient-to-r from-brand-300 to-brand-500 bg-clip-text text-transparent">Get it fixed.</span>
          </h2>
          <ul className="mt-8 space-y-4">
            {POINTS.map(({ icon: Icon, text }) => (
              <li key={text} className="flex items-center gap-3 text-slate-300">
                <span className="flex h-9 w-9 items-center justify-center rounded-lg bg-brand-400/10 text-brand-400"><Icon size={18} /></span>
                {text}
              </li>
            ))}
          </ul>

          {/* what a status update looks like, so the panel shows the product */}
          <div className="mt-10 rounded-xl border border-white/10 bg-white/5 p-4 backdrop-blur">
            <div className="flex items-center justify-between text-xs">
              <span className="font-mono text-slate-400">Example update</span>
              <span className="rounded-full bg-amber-400/15 px-2 py-0.5 font-medium text-amber-300">In Progress</span>
            </div>
            <p className="mt-2 text-sm font-medium">Wifi not working in hostel block B</p>
            <p className="mt-1 text-xs text-slate-400">Assigned to the IT/Internet manager · due in 2 days · 3 students affected</p>
            <div className="mt-3 flex gap-1.5">
              {[1, 2, 3, 4, 5].map((i) => (
                <span key={i} className={`h-1.5 flex-1 rounded-full ${i <= 3 ? "bg-brand-400" : "bg-white/10"}`} />
              ))}
            </div>
          </div>
        </div>
        <span />
      </aside>

      <div className="relative flex flex-1 items-center justify-center px-4 py-16">
        <Link to="/" className="absolute left-4 top-5 inline-flex items-center gap-1.5 text-sm text-slate-500 hover:text-slate-900 dark:hover:text-white sm:left-6">
          <ArrowLeft size={16} /> Back to home
        </Link>
        <div className="w-full max-w-md">
          <div className="mb-6 flex flex-col items-center text-center">
            <Link to="/" aria-label="EchoCampus home"><img src="/favicon.svg" alt="" className="mb-3 h-11 w-11 lg:hidden" /></Link>
            <h1 className="text-2xl font-semibold">{title}</h1>
            {subtitle && <p className="mt-1 text-sm text-slate-500">{subtitle}</p>}
          </div>
          <div className="card p-6">{children}</div>
          {footer && <p className="mt-4 text-center text-sm text-slate-500">{footer}</p>}
        </div>
      </div>
    </div>
  );
}

export function LoginPage() {
  const { user, login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [params] = useSearchParams();
  // after verifying, the login page opens with the new student id filled in
  const [form, setForm] = useState({ user_id: params.get("user") ?? "", password: "" });
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
        navigate("/verify?unverified=1");
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
      footer={<>New student? <Link to="/register" className="font-medium text-brand-600 dark:text-brand-400">Create an account</Link></>}
    >
      <form onSubmit={submit} className="space-y-4">
        <div>
          <label className="label" htmlFor="uid">User ID</label>
          <input id="uid" className="input" placeholder="ST101 / GM101 / AD100" autoComplete="username"
            value={form.user_id} onChange={(e) => setForm({ ...form, user_id: e.target.value })} required />
        </div>
        <div>
          <div className="flex items-center justify-between">
            <label className="label" htmlFor="pw">Password</label>
            <Link to="/forgot" className="mb-1 text-xs font-medium text-brand-600 hover:underline dark:text-brand-400">Forgot details?</Link>
          </div>
          <PasswordInput id="pw" autoComplete="current-password"
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
      toast.success("Account created. Check your email for the code.");
      navigate(`/verify?email=${encodeURIComponent(res.email)}&new=1`);
    } catch (err) {
      setError(err);
    } finally {
      setBusy(false);
    }
  }

  return (
    <AuthCard
      title="Student registration"
      subtitle="You get your student ID after verifying your email"
      footer={<>Already registered? <Link to="/login" className="font-medium text-brand-600 dark:text-brand-400">Sign in</Link></>}
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
            <PasswordInput id="pw1" autoComplete="new-password" value={form.password} onChange={set("password")} required />
          </div>
          <div>
            <label className="label" htmlFor="pw2">Confirm</label>
            <PasswordInput id="pw2" autoComplete="new-password" value={form.confirm} onChange={set("confirm")} required />
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
  const toast = useToast();
  const [email, setEmail] = useState(params.get("email") ?? "");
  const [code, setCode] = useState("");
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);
  const [studentId, setStudentId] = useState(null);   // set once the code is right

  async function submit(e) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const res = await api("/auth/verify-otp", { method: "POST", body: { email: email.trim(), code } });
      setStudentId(res.user_id);
    } catch (err) {
      setError(err);
    } finally {
      setBusy(false);
    }
  }

  async function resend() {
    setError(null);
    try {
      await api("/auth/resend-otp", { method: "POST", body: { email: email.trim() } });
      toast.info("A new code was sent to your email.");
    } catch (err) {
      setError(err);
    }
  }

  // no auto redirect here: the student reads and saves the id first
  if (studentId) return <StudentIdSaved studentId={studentId} />;

  const subtitle = params.get("new") ? "We sent a 6 digit code to your email. It can take a minute, check spam too."
    : params.get("unverified") ? "Your email isn't verified yet. Enter it below and we'll send you a code."
    : "Enter your email and the 6 digit code we sent you.";

  return (
    <AuthCard
      title="Verify your email"
      subtitle={subtitle}
      footer={<Link to="/login" className="font-medium text-brand-600 dark:text-brand-400">Back to sign in</Link>}
    >
      <form onSubmit={submit} className="space-y-4">
        <div>
          <label className="label" htmlFor="vemail">College email</label>
          <input id="vemail" type="email" className="input" autoComplete="email" value={email}
            onChange={(e) => setEmail(e.target.value)} required />
        </div>
        <div>
          <label className="label" htmlFor="code">Code</label>
          <input id="code" className="input text-center font-mono text-lg tracking-[0.5em]" inputMode="numeric" maxLength={6}
            pattern="\d{6}" placeholder="••••••" value={code} onChange={(e) => setCode(e.target.value.replace(/\D/g, ""))} required />
        </div>
        <ErrorBox error={error} />
        <button className="btn-primary w-full" disabled={busy || code.length !== 6}>{busy ? "Checking…" : "Verify"}</button>
        <button type="button" onClick={resend} className="w-full text-sm text-brand-600 dark:text-brand-400 hover:underline" disabled={!email.trim()}>
          Send a new code
        </button>
      </form>
    </AuthCard>
  );
}

// the student id, big, with a copy button. after verifying, and in forgot details
export function StudentIdSaved({ studentId, title = "Email verified", subtitle = "Your account is ready.",
  note = "Please save it. You need this ID and your password every time you sign in. We also sent it to your email.",
  children }) {
  const navigate = useNavigate();
  const toast = useToast();

  async function copy() {
    try {
      await navigator.clipboard.writeText(studentId);
      toast.success("Student ID copied.");
    } catch {
      toast.info(`Your student ID is ${studentId}`);
    }
  }

  return (
    <AuthCard title={title} subtitle={subtitle}>
      <div className="space-y-5 text-center">
        <CheckCircle2 size={40} className="mx-auto text-brand-600 dark:text-brand-400" />
        <div className="rounded-xl border-2 border-dashed border-brand-400 bg-brand-50 px-4 py-5 dark:bg-brand-400/10">
          <p className="text-sm text-slate-600 dark:text-slate-300">Your student ID is</p>
          <p className="mt-1 font-mono text-4xl font-bold tracking-wider">{studentId}</p>
          <button type="button" onClick={copy} className="mt-3 inline-flex items-center gap-1.5 text-sm font-medium text-brand-700 hover:underline dark:text-brand-300">
            <Copy size={14} /> Copy
          </button>
        </div>
        <p className="text-sm text-slate-600 dark:text-slate-400">{note}</p>
        {children ?? (
          <button className="btn-primary w-full" onClick={() => navigate(`/login?user=${encodeURIComponent(studentId)}`)}>
            Let&apos;s log in now
          </button>
        )}
      </div>
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
