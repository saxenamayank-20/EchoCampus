import { Link } from "react-router-dom";
import {
  ArrowRight, BookOpen, CheckCircle2, ClipboardList, Moon, ShieldCheck, Sparkles, Sun, UserCheck, Users,
} from "lucide-react";
import { useTheme } from "../lib/theme";

const FLOW = ["Submitted", "Assigned", "In Progress", "Resolved", "Closed"];

const FEATURES = [
  { icon: Sparkles, title: "AI sorts it for you",
    text: "Gemini reads your complaint and suggests the category and priority. It can raise the priority, never lower it." },
  { icon: Users, title: "No duplicate complaints",
    text: "Before you submit, you see similar open complaints and can back one with \"I have this issue too\"." },
  { icon: BookOpen, title: "Answers from the handbook",
    text: "Ask about rules, fees or timings. The assistant answers only from the college documents and shows the page." },
  { icon: ShieldCheck, title: "Tracked until it's fixed",
    text: "Deadlines by priority, automatic escalation, and it only closes after you confirm the fix." },
];

const STEPS = [
  { icon: ClipboardList, title: "Raise it", text: "Describe the problem and add a photo or PDF as proof." },
  { icon: UserCheck, title: "Right person, right away", text: "It goes straight to the manager of that category, with a deadline." },
  { icon: CheckCircle2, title: "Confirm the fix", text: "You get notified when it's resolved and say if it's really fixed." },
];

// dark mode here is plain near-black with see-through cards, so nothing turns navy
const PANEL = "rounded-2xl border border-slate-200 bg-white shadow-sm dark:border-white/10 dark:bg-white/[0.03] dark:shadow-none";

function SectionTitle({ kicker, title, text }) {
  return (
    <div className="mx-auto max-w-2xl text-center">
      <p className="text-xs font-semibold uppercase tracking-[0.2em] text-brand-700 dark:text-brand-400">{kicker}</p>
      <h2 className="mt-3 text-3xl font-bold tracking-tight sm:text-4xl">{title}</h2>
      {text && <p className="mt-3 text-slate-600 dark:text-slate-400">{text}</p>}
    </div>
  );
}

// public home page for visitors who aren't logged in
export default function Landing() {
  const [theme, toggleTheme] = useTheme();

  return (
    <div className="relative min-h-screen overflow-hidden bg-slate-50 dark:bg-[#07090c]">
      {/* soft lime glow behind the hero */}
      <div aria-hidden className="pointer-events-none absolute left-1/2 top-[-14rem] h-[36rem] w-[60rem] -translate-x-1/2 rounded-full bg-brand-400/25 blur-3xl dark:bg-brand-400/[0.07]" />

      <header className="relative mx-auto flex max-w-6xl items-center justify-between px-5 py-5 sm:px-8">
        <Link to="/" className="flex items-center gap-2.5">
          <img src="/favicon.svg" alt="" className="h-9 w-9" />
          <span className="text-lg font-semibold">EchoCampus</span>
        </Link>
        <nav className="flex items-center gap-2 sm:gap-3">
          <button onClick={toggleTheme} className="rounded-lg p-2 text-slate-500 hover:bg-slate-200/60 dark:hover:bg-white/10" aria-label="Toggle dark mode">
            {theme === "dark" ? <Sun size={18} /> : <Moon size={18} />}
          </button>
          <Link to="/login" className="whitespace-nowrap px-2 text-sm font-medium text-slate-700 hover:text-slate-950 dark:text-slate-300 dark:hover:text-white">Log in</Link>
          {/* on small phones the big "Raise a complaint" button below does the same */}
          <Link to="/register" className="btn-primary hidden whitespace-nowrap shadow-lg shadow-brand-400/30 dark:shadow-none sm:inline-flex">Get started</Link>
        </nav>
      </header>

      <main className="relative">
        {/* hero */}
        <section className="mx-auto max-w-6xl px-5 pb-20 pt-16 text-center sm:px-8 sm:pb-24 sm:pt-24">
          <span className="inline-flex items-center gap-1.5 rounded-full border border-brand-300/60 bg-brand-100/70 px-3 py-1 text-xs font-medium text-brand-800 dark:border-brand-400/20 dark:bg-brand-400/10 dark:text-brand-300">
            <Sparkles size={13} /> AI-powered grievance portal
          </span>
          <h1 className="mx-auto mt-7 max-w-4xl text-4xl font-bold leading-[1.1] tracking-tight sm:text-6xl lg:text-7xl">
            Every campus complaint,{" "}
            <span className="bg-gradient-to-r from-brand-600 to-lime-500 bg-clip-text text-transparent dark:from-brand-300 dark:to-brand-500">heard</span>.
          </h1>
          <p className="mx-auto mt-6 max-w-2xl text-base leading-relaxed text-slate-600 dark:text-slate-400 sm:text-lg">
            Raise an issue in a minute, see who is handling it, and close it only when it&apos;s really fixed.
            With AI that sorts complaints, spots duplicates and answers from the student handbook.
          </p>
          <div className="mt-10 flex flex-wrap justify-center gap-3">
            <Link to="/register" className="btn-primary px-6 py-3 text-base shadow-lg shadow-brand-400/30 dark:shadow-none">
              Raise a complaint <ArrowRight size={18} />
            </Link>
            <Link to="/login" className="btn-secondary px-6 py-3 text-base dark:border-white/15 dark:bg-white/5 dark:hover:bg-white/10">I have an account</Link>
          </div>

          {/* how a complaint moves, the same steps the app uses */}
          <div className={`${PANEL} mx-auto mt-16 max-w-4xl px-5 py-7 sm:px-10`}>
            <p className="text-sm font-medium text-slate-500">Every complaint follows the same steps</p>
            <ol className="relative mt-6 grid grid-cols-5 gap-2">
              {/* line behind the circles */}
              <span aria-hidden className="absolute left-[10%] right-[10%] top-[18px] h-0.5 bg-gradient-to-r from-brand-400 via-brand-400 to-slate-300 dark:to-white/20" />
              {FLOW.map((s, i) => (
                <li key={s} className="relative flex flex-col items-center text-center">
                  <span className={`flex h-9 w-9 items-center justify-center rounded-full text-sm font-semibold ring-4 ring-white dark:ring-[#0d1013] ${
                    i < 4 ? "bg-brand-400 text-slate-950" : "bg-slate-800 text-white dark:bg-slate-600"}`}>{i + 1}</span>
                  <span className="mt-2 text-xs font-medium sm:text-sm">{s}</span>
                </li>
              ))}
            </ol>
            <p className="mt-6 text-xs text-slate-500">
              The manager can&apos;t close it alone: you confirm the fix first, then the admin closes it.
            </p>
          </div>
        </section>

        {/* features */}
        <section className="border-y border-slate-200/70 bg-white/60 py-20 dark:border-white/5 dark:bg-white/[0.015] sm:py-24">
          <div className="mx-auto max-w-5xl px-5 sm:px-8">
            <SectionTitle kicker="Why EchoCampus" title="Built for real campus problems"
              text="No lost forms, no running between offices. One place from the first report to the fix." />
            <div className="mt-12 grid gap-5 sm:grid-cols-2">
              {FEATURES.map(({ icon: Icon, title, text }) => (
                <div key={title} className={`${PANEL} flex gap-4 p-6 transition hover:-translate-y-0.5 hover:border-brand-400/60 sm:p-7`}>
                  <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl bg-brand-100 text-brand-700 dark:bg-brand-400/10 dark:text-brand-400">
                    <Icon size={22} />
                  </div>
                  <div>
                    <h3 className="text-lg font-semibold">{title}</h3>
                    <p className="mt-1.5 text-sm leading-relaxed text-slate-600 dark:text-slate-400">{text}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* how it works */}
        <section className="mx-auto max-w-5xl px-5 py-20 sm:px-8 sm:py-24">
          <SectionTitle kicker="How it works" title="Three steps, start to fixed" />
          <div className="mt-12 grid gap-5 sm:grid-cols-3">
            {STEPS.map(({ icon: Icon, title, text }, i) => (
              <div key={title} className={`${PANEL} p-7 text-center`}>
                <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-slate-900 text-brand-400 dark:bg-brand-400 dark:text-slate-950">
                  <Icon size={22} />
                </div>
                <p className="mt-4 text-xs font-semibold uppercase tracking-wide text-slate-500">Step {i + 1}</p>
                <h3 className="mt-1 text-lg font-semibold">{title}</h3>
                <p className="mt-2 text-sm leading-relaxed text-slate-600 dark:text-slate-400">{text}</p>
              </div>
            ))}
          </div>
        </section>

        {/* last push before the footer */}
        <section className="mx-auto max-w-5xl px-5 pb-20 sm:px-8 sm:pb-24">
          <div className="relative overflow-hidden rounded-3xl bg-slate-900 px-6 py-12 text-center text-white dark:border dark:border-white/10 dark:bg-white/[0.04] sm:px-12">
            <div aria-hidden className="pointer-events-none absolute left-1/2 -top-32 h-64 w-[36rem] -translate-x-1/2 rounded-full bg-brand-400/15 blur-3xl" />
            <h2 className="relative text-2xl font-bold sm:text-3xl">Got a problem on campus?</h2>
            <p className="relative mx-auto mt-3 max-w-xl text-slate-300">
              Raise it in a minute and follow it until it&apos;s really fixed.
            </p>
            {/* one button here, log in is already in the top bar */}
            <div className="relative mt-8 flex justify-center">
              <Link to="/register" className="btn-primary px-6 py-3 text-base">Get started <ArrowRight size={18} /></Link>
            </div>
          </div>
        </section>
      </main>

      <footer className="relative border-t border-slate-200 dark:border-white/10">
        <div className="mx-auto flex max-w-6xl flex-col items-center justify-between gap-3 px-5 py-8 text-sm text-slate-500 sm:flex-row sm:px-8">
          <span className="flex items-center gap-2">
            <img src="/favicon.svg" alt="" className="h-6 w-6" />
            <span className="font-medium text-slate-700 dark:text-slate-300">EchoCampus</span>
            <span className="hidden sm:inline">· Every campus complaint, heard.</span>
          </span>
          <span>© {new Date().getFullYear()} EchoCampus</span>
        </div>
      </footer>
    </div>
  );
}
