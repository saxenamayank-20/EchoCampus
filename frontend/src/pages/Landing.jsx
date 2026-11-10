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

// public home page for visitors who aren't logged in
export default function Landing() {
  const [theme, toggleTheme] = useTheme();

  return (
    <div className="relative min-h-screen overflow-hidden bg-slate-50 dark:bg-[#060a0f]">
      {/* soft lime glow behind the hero */}
      <div aria-hidden className="pointer-events-none absolute left-1/2 top-[-12rem] h-[34rem] w-[54rem] -translate-x-1/2 rounded-full bg-brand-400/25 blur-3xl dark:bg-brand-400/15" />

      <header className="relative mx-auto flex max-w-6xl items-center justify-between px-4 py-5 sm:px-6">
        <Link to="/" className="flex items-center gap-2.5">
          <img src="/favicon.svg" alt="" className="h-9 w-9" />
          <span className="text-lg font-semibold">EchoCampus</span>
        </Link>
        <nav className="flex items-center gap-2 sm:gap-3">
          <button onClick={toggleTheme} className="rounded-lg p-2 text-slate-500 hover:bg-slate-200/60 dark:hover:bg-slate-800" aria-label="Toggle dark mode">
            {theme === "dark" ? <Sun size={18} /> : <Moon size={18} />}
          </button>
          <Link to="/login" className="whitespace-nowrap px-2 text-sm font-medium text-slate-700 hover:text-slate-950 dark:text-slate-300 dark:hover:text-white">Log in</Link>
          {/* on small phones the big "Raise a complaint" button below does the same */}
          <Link to="/register" className="btn-primary hidden whitespace-nowrap shadow-lg shadow-brand-400/30 sm:inline-flex">Get started</Link>
        </nav>
      </header>

      <main className="relative mx-auto max-w-6xl px-4 sm:px-6">
        {/* hero */}
        <section className="pb-14 pt-12 text-center sm:pt-20">
          <span className="inline-flex items-center gap-1.5 rounded-full border border-brand-300/60 bg-brand-100/70 px-3 py-1 text-xs font-medium text-brand-800 dark:border-brand-400/20 dark:bg-brand-400/10 dark:text-brand-300">
            <Sparkles size={13} /> AI-powered grievance portal
          </span>
          <h1 className="mx-auto mt-6 max-w-3xl text-4xl font-bold leading-tight tracking-tight sm:text-6xl">
            Every campus complaint,{" "}
            <span className="bg-gradient-to-r from-brand-600 to-lime-500 bg-clip-text text-transparent dark:from-brand-300 dark:to-brand-500">heard</span>.
          </h1>
          <p className="mx-auto mt-5 max-w-2xl text-base text-slate-600 dark:text-slate-400 sm:text-lg">
            Raise an issue in a minute, see who is handling it, and close it only when it&apos;s really fixed.
            With AI that sorts complaints, spots duplicates and answers from the student handbook.
          </p>
          <div className="mt-8 flex flex-wrap justify-center gap-3">
            <Link to="/register" className="btn-primary px-6 py-3 text-base shadow-lg shadow-brand-400/30">
              Raise a complaint <ArrowRight size={18} />
            </Link>
            <Link to="/login" className="btn-secondary px-6 py-3 text-base">I have an account</Link>
          </div>
        </section>

        {/* how a complaint moves, the same steps the app uses */}
        <section className="rounded-2xl bg-gradient-to-r from-brand-400 via-lime-400 to-brand-500 p-[2px] shadow-xl shadow-brand-400/10">
          <div className="rounded-[14px] bg-white px-5 py-6 dark:bg-slate-900 sm:px-8">
            <p className="text-sm text-slate-500">Every complaint follows the same steps</p>
            <ol className="mt-4 grid grid-cols-5 gap-2">
              {FLOW.map((s, i) => (
                <li key={s} className="flex flex-col items-center text-center">
                  <span className={`flex h-9 w-9 items-center justify-center rounded-full text-sm font-semibold ${
                    i < 4 ? "bg-brand-400 text-slate-950" : "bg-slate-800 text-white dark:bg-slate-700"}`}>{i + 1}</span>
                  <span className="mt-2 text-xs font-medium sm:text-sm">{s}</span>
                </li>
              ))}
            </ol>
            <p className="mt-5 text-center text-xs text-slate-500">
              The manager can&apos;t close it alone: you confirm the fix first, then the admin closes it.
            </p>
          </div>
        </section>

        {/* features */}
        <section className="grid gap-4 py-14 sm:grid-cols-2 lg:grid-cols-4">
          {FEATURES.map(({ icon: Icon, title, text }) => (
            <div key={title} className="card p-5">
              <div className="mb-4 flex h-11 w-11 items-center justify-center rounded-xl bg-brand-100 text-brand-700 dark:bg-brand-400/10 dark:text-brand-400">
                <Icon size={20} />
              </div>
              <h3 className="font-semibold">{title}</h3>
              <p className="mt-2 text-sm text-slate-600 dark:text-slate-400">{text}</p>
            </div>
          ))}
        </section>

        {/* how it works */}
        <section className="pb-16">
          <h2 className="text-center text-2xl font-bold sm:text-3xl">How it works</h2>
          <div className="mt-8 grid gap-6 sm:grid-cols-3">
            {STEPS.map(({ icon: Icon, title, text }, i) => (
              <div key={title} className="text-center">
                <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-slate-900 text-brand-400 dark:bg-brand-400 dark:text-slate-950">
                  <Icon size={22} />
                </div>
                <p className="mt-3 text-xs font-semibold uppercase tracking-wide text-slate-500">Step {i + 1}</p>
                <h3 className="mt-1 font-semibold">{title}</h3>
                <p className="mt-1 text-sm text-slate-600 dark:text-slate-400">{text}</p>
              </div>
            ))}
          </div>
        </section>
      </main>

      <footer className="relative border-t border-slate-200 py-6 text-center text-xs text-slate-500 dark:border-slate-800">
        © {new Date().getFullYear()} EchoCampus
      </footer>
    </div>
  );
}
