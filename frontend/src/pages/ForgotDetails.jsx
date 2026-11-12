import { useState } from "react";
import { Link, Navigate, useNavigate, useSearchParams } from "react-router-dom";
import { ChevronRight, IdCard, KeyRound, LifeBuoy } from "lucide-react";
import { api } from "../api/client";
import { homeFor, useAuth } from "../auth/AuthContext";
import { ErrorBox } from "../components/Feedback";
import { useToast } from "../components/Toast";
import { AuthCard, StudentIdSaved } from "./AuthPages";

const OPTIONS = [
  { mode: "id", icon: IdCard, title: "I forgot my student ID", text: "We email a recovery code, then show your ID." },
  { mode: "password", icon: KeyRound, title: "I forgot my password", text: "We email a one-time login code for your student ID." },
  { mode: "both", icon: LifeBuoy, title: "I forgot both", text: "Recovery code for your ID first, then a login code." },
];

const BACK = <Link to="/login" className="font-medium text-brand-600 dark:text-brand-400">Back to sign in</Link>;

function CodeInput({ value, onChange }) {
  return (
    <input id="code" className="input text-center font-mono text-lg tracking-[0.5em]" inputMode="numeric" maxLength={6}
      pattern="\d{6}" placeholder="••••••" value={value} onChange={(e) => onChange(e.target.value.replace(/\D/g, ""))} required />
  );
}

// small helper so every step shows busy + errors the same way
function useStep() {
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);
  async function run(fn) {
    setBusy(true);
    setError(null);
    try {
      await fn();
    } catch (err) {
      setError(err);
    } finally {
      setBusy(false);
    }
  }
  return { error, busy, run };
}

// "forgot details?" on the login page: pick what you forgot, then the steps for that
export function ForgotPage() {
  const [params, setParams] = useSearchParams();
  const mode = params.get("mode");
  if (mode === "password") return <ForgotPassword />;
  if (mode === "id" || mode === "both") return <ForgotId both={mode === "both"} />;

  return (
    <AuthCard title="Forgot details?" subtitle="No problem. Tell us what you forgot." footer={BACK}>
      <div className="space-y-3">
        {OPTIONS.map(({ mode: m, icon: Icon, title, text }) => (
          <button key={m} onClick={() => setParams({ mode: m })}
            className="flex w-full items-center gap-3 rounded-xl border border-slate-200 p-4 text-left transition hover:border-brand-400 hover:bg-brand-50/60 dark:border-slate-800 dark:hover:bg-brand-400/5">
            <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-brand-100 text-brand-700 dark:bg-brand-400/10 dark:text-brand-400">
              <Icon size={20} />
            </span>
            <span className="flex-1">
              <span className="block text-sm font-semibold">{title}</span>
              <span className="block text-xs text-slate-500">{text}</span>
            </span>
            <ChevronRight size={18} className="text-slate-400" />
          </button>
        ))}
        <p className="pt-2 text-center text-xs text-slate-500">
          Managers and admin: please contact the admin or the technical team.
        </p>
      </div>
    </AuthCard>
  );
}

// forgot id (and step 1 of forgot both): email -> recovery code -> the id
function ForgotId({ both }) {
  const navigate = useNavigate();
  const toast = useToast();
  const [email, setEmail] = useState("");
  const [sent, setSent] = useState(false);
  const [code, setCode] = useState("");
  const [studentId, setStudentId] = useState(null);
  const { error, busy, run } = useStep();

  const send = () => run(async () => {
    const res = await api("/auth/forgot/id", { method: "POST", body: { email: email.trim() } });
    setSent(true);
    toast.info(res.message);
  });
  const check = () => run(async () => {
    const res = await api("/auth/forgot/id/verify", { method: "POST", body: { email: email.trim(), code } });
    setStudentId(res.user_id);
  });
  // forgot both: the id is known now, so the login code can go out straight away
  const sendLoginCode = () => run(async () => {
    await api("/auth/forgot/password", { method: "POST", body: { user_id: studentId } });
    navigate(`/login-code?user=${encodeURIComponent(studentId)}`);
  });

  if (studentId) {
    return (
      <StudentIdSaved studentId={studentId} title="Found your account" subtitle="Here's your student ID."
        note={both ? "Save it. Next we'll email you a one-time login code so you can sign in and set a new password."
          : "Save it. You need this ID and your password every time you sign in."}>
        {both ? (
          <>
            <ErrorBox error={error} />
            <button className="btn-primary w-full" onClick={sendLoginCode} disabled={busy}>
              {busy ? "Sending…" : "Send my login code"}
            </button>
          </>
        ) : undefined}
      </StudentIdSaved>
    );
  }

  return (
    <AuthCard title={both ? "Forgot both" : "Forgot student ID"}
      subtitle={sent ? "Enter the recovery code from your email. It can take a minute, check spam too."
        : "Enter the email you registered with and we'll send you a recovery code."}
      footer={<Link to="/forgot" className="font-medium text-brand-600 dark:text-brand-400">Choose something else</Link>}>
      <form onSubmit={(e) => { e.preventDefault(); sent ? check() : send(); }} className="space-y-4">
        <div>
          <label className="label" htmlFor="femail">College email</label>
          <input id="femail" type="email" className="input" autoComplete="email" value={email} disabled={sent}
            onChange={(e) => setEmail(e.target.value)} required />
        </div>
        {sent && (
          <div>
            <label className="label" htmlFor="code">Recovery code</label>
            <CodeInput value={code} onChange={setCode} />
          </div>
        )}
        <ErrorBox error={error} />
        <button className="btn-primary w-full" disabled={busy || (sent && code.length !== 6)}>
          {busy ? "Please wait…" : sent ? "Show my student ID" : "Send recovery code"}
        </button>
        {sent && (
          <button type="button" onClick={send} className="w-full text-sm text-brand-600 hover:underline dark:text-brand-400" disabled={busy}>
            Send a new code
          </button>
        )}
      </form>
    </AuthCard>
  );
}

// forgot password: student id -> login code goes out -> sign in with the code
function ForgotPassword() {
  const navigate = useNavigate();
  const [userId, setUserId] = useState("");
  const { error, busy, run } = useStep();

  const send = () => run(async () => {
    await api("/auth/forgot/password", { method: "POST", body: { user_id: userId.trim() } });
    navigate(`/login-code?user=${encodeURIComponent(userId.trim())}`);
  });

  return (
    <AuthCard title="Forgot password" subtitle="Enter your student ID and we'll email you a one-time login code."
      footer={<Link to="/forgot" className="font-medium text-brand-600 dark:text-brand-400">Choose something else</Link>}>
      <form onSubmit={(e) => { e.preventDefault(); send(); }} className="space-y-4">
        <div>
          <label className="label" htmlFor="fuid">Student ID</label>
          <input id="fuid" className="input" placeholder="ST101" autoComplete="username" value={userId}
            onChange={(e) => setUserId(e.target.value)} required />
        </div>
        <ErrorBox error={error} />
        <button className="btn-primary w-full" disabled={busy}>{busy ? "Sending…" : "Send login code"}</button>
      </form>
    </AuthCard>
  );
}

// sign in with the student id + the emailed login code, then set a new password in my account
export function LoginCodePage() {
  const { user, loginWithCode } = useAuth();
  const navigate = useNavigate();
  const toast = useToast();
  const [params] = useSearchParams();
  const [userId, setUserId] = useState(params.get("user") ?? "");
  const [code, setCode] = useState("");
  const { error, busy, run } = useStep();

  if (user) return <Navigate to={homeFor(user.role)} replace />;

  const submit = () => run(async () => {
    await loginWithCode(userId.trim(), code);
    toast.success("You're in. Please set a new password now.");
    navigate("/account", { replace: true });
  });
  const resend = () => run(async () => {
    const res = await api("/auth/forgot/password", { method: "POST", body: { user_id: userId.trim() } });
    toast.info(res.message);
  });

  return (
    <AuthCard title="Sign in with a code"
      subtitle="We emailed a one-time login code to your account's email. It works once and expires in 10 minutes."
      footer={BACK}>
      <form onSubmit={(e) => { e.preventDefault(); submit(); }} className="space-y-4">
        <div>
          <label className="label" htmlFor="cuid">Student ID</label>
          <input id="cuid" className="input" value={userId} onChange={(e) => setUserId(e.target.value)} required />
        </div>
        <div>
          <label className="label" htmlFor="code">Login code</label>
          <CodeInput value={code} onChange={setCode} />
        </div>
        <ErrorBox error={error} />
        <button className="btn-primary w-full" disabled={busy || code.length !== 6}>{busy ? "Signing in…" : "Sign in"}</button>
        <button type="button" onClick={resend} className="w-full text-sm text-brand-600 hover:underline dark:text-brand-400" disabled={busy || !userId.trim()}>
          Send a new code
        </button>
      </form>
    </AuthCard>
  );
}
